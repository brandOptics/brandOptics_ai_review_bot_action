#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path
from textwrap import dedent
import openai
from github import Github
import re # Make sure 'import re' is at the top of your Python file
from datetime import datetime # Import datetime
import pytz # Import pytz (ensure you have it installed)
# --- 1) SETUP ──────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
REPO_NAME      = os.getenv("GITHUB_REPOSITORY")
EVENT_PATH     = os.getenv("GITHUB_EVENT_PATH")

if not OPENAI_API_KEY or not GITHUB_TOKEN:
    print("⛔️ Missing OpenAI or GitHub token.")
    exit(1)
openai.api_key = OPENAI_API_KEY
gh = Github(GITHUB_TOKEN)

# --- 2) LOAD PR DATA ────────────────────────────────────────────────────
with open(EVENT_PATH) as f:
    event = json.load(f)
pr_number = event["pull_request"]["number"]
full_sha  = event["pull_request"]["head"]["sha"]
repo      = gh.get_repo(REPO_NAME)
pr        = repo.get_pull(pr_number)

dev_name = event["pull_request"]["user"]["login"]
title        = event["pull_request"]["title"]
body         = event["pull_request"]["body"] or "No description provided."
url          = event["pull_request"]["html_url"]
source_branch = event["pull_request"]["head"]["ref"]
target_branch = event["pull_request"]["base"]["ref"]
created_at   = event["pull_request"]["created_at"]
# Get the UTC timestamp string from GitHub
created_at_utc_str = event["pull_request"]["created_at"]
commits      = event["pull_request"]["commits"]
additions    = event["pull_request"]["additions"]
deletions    = event["pull_request"]["deletions"]

# --- Insert logo at top of comment ────────────────────────────────────
default_branch = repo.default_branch

# Ensure the image URL is correct and points to the raw content of the default branch
# Make sure the file exists at .github/assets/bailogo.png in your repo's default branch
# And that your repository is public or the image is accessible.
img_url = (
    f"https://raw.githubusercontent.com/"
    f"{REPO_NAME}/{default_branch}/.github/assets/bailogo.png"
)

# --- Dynamic Timezone Configuration ---
# Get the target timezone name from an environment variable.
# Provide a sensible default (e.g., 'UTC' or 'Asia/Kolkata' if that's your primary target)
TARGET_TIMEZONE_NAME = os.getenv("TARGET_TIMEZONE", "Asia/Kolkata")
# --- Timezone Conversion for 'created_at' ---
try:
    utc_dt = datetime.strptime(created_at_utc_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_dt = pytz.utc.localize(utc_dt)

    # Use the dynamically set timezone name
    local_tz = pytz.timezone(TARGET_TIMEZONE_NAME)

    local_dt = utc_dt.astimezone(local_tz)
    formatted_created_at = local_dt.strftime("%B %d, %Y, %I:%M %p %Z")

except pytz.UnknownTimeZoneError:
    print(f"⚠️ Warning: Unknown timezone '{TARGET_TIMEZONE_NAME}' specified. Falling back to UTC.")
    local_tz = pytz.utc # Fallback to UTC if the provided timezone is invalid
    local_dt = utc_dt.astimezone(local_tz)
    formatted_created_at = local_dt.strftime("%B %d, %Y, %I:%M %p %Z")
except Exception as e:
    # Catch any other potential errors during parsing or conversion
    print(f"❌ Error during time conversion for '{created_at_utc_str}': {e}. Falling back to original UTC string.")
    formatted_created_at = created_at_utc_str
# --- End Timezone Conversion ---
# --- 3) DETECT CHANGED FILES (exclude .github/) ─────────────────────────
changed_files_list = [f.filename for f in pr.get_files()
                      if f.patch and not f.filename.lower().startswith('.github/')]

if not changed_files_list:
    pr.create_issue_comment(dedent(f"""
<img src="{img_url}" width="100" height="100" />

# brandOptics AI Neural Nexus

## Review: ✅ No Relevant Changes Detected

No actionable code changes were found in this PR.
Everything looks quiet on the commit front — nothing to analyze right now. 😌

💡 **Note**
Make sure your changes include source code updates (excluding config/docs only) to trigger a meaningful review.
"""))
    repo.get_commit(full_sha).create_status(
        context="brandOptics AI Neural Nexus Code Review",
        state="success",
        description="No relevant code changes detected."
    )
    exit(0)

# --- 4) LOAD LINTER REPORTS ─────────────────────────────────────────────
def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception: # Catch any exception during JSON loading
        return None

reports_dir = Path('.github/linter-reports')
eslint_report        = load_json(reports_dir / 'eslint.json')
flake8_report        = load_json(reports_dir / 'flake8.json')
shellcheck_report    = load_json(reports_dir / 'shellcheck.json')
dartanalyzer_report  = load_json(reports_dir / 'dartanalyzer.json')
dotnet_report        = load_json(reports_dir / 'dotnet-format.json')
htmlhint_report      = load_json(reports_dir / 'htmlhint.json')
stylelint_report     = load_json(reports_dir / 'stylelint.json')

# --- 5) HELPERS ─────────────────────────────────────────────────────────
def get_patch_context(patch: str, line_no: int, ctx: int = 3) -> str:
    """Extracts a contextual snippet from a patch around a specific line number."""
    file_line = None
    final_context_lines = []
    
    for line in patch.splitlines():
        if line.startswith('@@ '):
            final_context_lines.append(line)
            match = re.match(r'@@ -\d+,\d+ \+(\d+),\d+ @@', line)
            if match:
                file_line = int(match.group(1)) # 1-indexed for comparison
            else:
                file_line = None
            continue

        if file_line is not None:
            prefix = line[0]
            # Check if the current line is within the desired context
            # Include lines that are additions (+) or context ( ) within the window
            # Also include deletions (-) if they are within the context window
            if prefix in (' ', '+') and abs(file_line - line_no) <= ctx:
                final_context_lines.append(line)
            elif prefix == '-' and (file_line >= line_no - ctx and file_line <= line_no + ctx):
                final_context_lines.append(line)
            
            # Increment file_line only for lines that exist in the new file (context or additions)
            if prefix in (' ', '+'):
                file_line += 1
            
            # Stop if we've passed the context window for lines that exist in the new file
            if file_line > line_no + ctx and prefix not in ('-', '+'):
                break # Break if we are past the context and not looking at a pending deletion/addition

    return '\n'.join(final_context_lines)


# --- LANGUAGE DETECTION ───────────────────────────────────────────────────
def detect_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {
        '.dart':       'Dart/Flutter',
        '.ts':         'TypeScript/Angular',
        '.js':         'JavaScript/React',
        '.jsx':        'JavaScript/React',
        '.tsx':        'TypeScript/React',
        '.py':         'Python',
        '.java':       'Java',
        '.cs':         '.NET C#',
        '.go':         'Go',
        '.html':       'HTML',
        '.htm':        'HTML',
        '.css':        'CSS',
        '.scss':       'SCSS/Sass',
        '.less':       'Less',
        '.sh':         'Shell', # Added for ShellCheck
        # add more as needed…
    }.get(ext, 'general programming')

FENCE_BY_LANG = {
    'Dart/Flutter':     'dart',
    'TypeScript/Angular':'ts',
    'JavaScript/React': 'js',
    'TypeScript/React': 'ts',
    'Python':           'python',
    'Java':             'java',
    '.NET C#':          'csharp',
    'Go':               'go',
    'HTML':             'html',
    'CSS':              'css',
    'SCSS/Sass':        'scss',
    'Less':             'less',
    'Shell':            'sh',
    'general programming': '' # Default to no specific fence if unknown
}

# --- 7) COLLECT ISSUES ──────────────────────────────────────────────────
issues = []
# ESLint
if isinstance(eslint_report, list):
    for rep in eslint_report:
        path = os.path.relpath(rep.get('filePath',''))
        if path in changed_files_list:
            for msg in rep.get('messages', []):
                ln = msg.get('line')
                if ln: issues.append({'file':path,'line':ln,
                                      'code':msg.get('ruleId','ESLint'),
                                      'message':msg.get('message','')})
# Flake8
if isinstance(flake8_report, dict):
    for ap, errs in flake8_report.items():
        path = os.path.relpath(ap)
        if path in changed_files_list:
            for e in errs:
                ln = e.get('line_number') or e.get('line')
                if ln: issues.append({'file':path,'line':ln,
                                      'code':e.get('code','Flake8'),
                                      'message':e.get('text','')})
# ShellCheck
if isinstance(shellcheck_report, list):
    for ent in shellcheck_report:
        path = os.path.relpath(ent.get('file',''))
        ln = ent.get('line')
        if path in changed_files_list and ln: issues.append({'file':path,'line':ln,
                                                         'code':ent.get('code','ShellCheck'),
                                                         'message':ent.get('message','')})
# Dart Analyzer
if isinstance(dartanalyzer_report, dict):
    for diag in dartanalyzer_report.get('diagnostics', []):
        loc = diag.get('location', {})
        path = os.path.relpath(loc.get('file',''))
        ln = loc.get('range',{}).get('start',{}).get('line')
        if path in changed_files_list and ln: issues.append({'file':path,'line':ln,
                                                        'code':diag.get('code','DartAnalyzer'),
                                                        'message':diag.get('problemMessage') or diag.get('message','')})
# .NET Format
if isinstance(dotnet_report, dict):
    diags = dotnet_report.get('Diagnostics') or dotnet_report.get('diagnostics')
    if isinstance(diags, list):
        for d in diags:
            path = os.path.relpath(d.get('Path') or d.get('path',''))
            ln = d.get('Region',{}).get('StartLine')
            if path in changed_files_list and ln: issues.append({'file':path,'line':ln,
                                                           'code':'DotNetFormat',
                                                           'message':d.get('Message','')})

# --- 7b) COLLECT HTMLHint ISSUES ────────────────────────────────────────
if isinstance(htmlhint_report, list):
    for ent in htmlhint_report:
        path = os.path.relpath(ent.get('file', ''))
        ln   = ent.get('line', None)
        msg  = ent.get('message', '')
        rule = ent.get('rule', 'HTMLHint')
        if path in changed_files_list and ln:
            issues.append({
                'file':    path,
                'line':    ln,
                'code':    rule,
                'message': msg
            })

# --- 7c) COLLECT Stylelint ISSUES ──────────────────────────────────────
if isinstance(stylelint_report, list):
    for rep in stylelint_report:
        path = os.path.relpath(rep.get('source', ''))
        ln   = rep.get('line', None)
        msg  = rep.get('text', '')
        rule = rep.get('rule', 'Stylelint')
        if path in changed_files_list and ln:
            issues.append({
                'file':    path,
                'line':    ln,
                'code':    rule,
                'message': msg
            })
# --- 8) GROUP AND FORMAT OUTPUT ─────────────────────────────────────────
file_groups = {}
for issue in issues: file_groups.setdefault(issue['file'], []).append(issue)

# --- 6) AI SUGGESTION ───────────────────────────────────────────────────
def ai_suggest_fix(code: str, patch_ctx: str, file_path: str, line_no: int, issue_message: str) -> str:
    lang = detect_language(file_path)
    fence = FENCE_BY_LANG.get(lang, '') # Get the appropriate fence

    # Provided stronger instructions for AI to always include the language fence
    # and to ensure the "Suggested Fix" section contains the full code block.
    prompt = dedent(f"""
    You are a highly experienced {lang} code reviewer and software architect.
    Your task is to analyze the provided code context and a reported issue, then provide a detailed, actionable suggestion for improvement.

    Reported issue:
    - **File:** `{file_path}`
    - **Line:** `{line_no}`
    - **Issue Code:** `{code}`
    - **Message:** `{issue_message}`

    Here's the relevant code context (a diff snippet around the reported line):
    ```diff
    {patch_ctx}
    ```

    Please provide your analysis and suggestions in exactly three labeled sections.
    **Crucially, ensure the 'Suggested Fix' section includes a code block formatted with triple backticks and the correct language identifier immediately after the opening backticks (e.g., ```{fence}\n...code...\n```).**
    If showing original and corrected code, keep it within a single code block.

    **Analysis:**
    Provide a concise explanation of the root cause of the issue, and elaborate on any other potential issues you identify within the provided code context (e.g., performance, security, maintainability, naming conventions, adherence to {lang} best practices).

    **Suggested Fix:**
    Provide a copy-friendly code snippet for the corrected code. This snippet should include the lines that need to be changed, and if applicable, a few lines of surrounding context for clarity.
    **Remember to use the correct language fence like `{fence}` immediately after the opening triple backticks, e.g., ```{fence}**.
    Example format:
    ```{fence}
    // Original:
    // old code line 1
    // old code line 2
    // Corrected:
    new code line 1
    new code line 2
    ```

    **Rationale:**
    Briefly explain *why* your suggested fix is better, covering aspects like readability, performance, adherence to best practices, or security improvements.
    """)

    system_prompt = (
        f"You are a senior {lang} software architect and code reviewer. "
        "You provide in-depth, actionable feedback, "
        "catching syntax, style, performance, security, naming, and {lang} best practices. "
        "Always focus on clarity, maintainability, and robust solutions."
    )
    resp = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role':'system','content':system_prompt},
                  {'role':'user','content':prompt}],
        temperature=0.1, # Keep temperature low for more deterministic and accurate fixes
        max_tokens=700 # Increased tokens to allow for more detailed responses
    )
    return resp.choices[0].message.content.strip()

rating_prompt = dedent(f"""
You are a senior software reviewer, known for your fair and motivational feedback.

Evaluate the pull request submitted by @{dev_name} using the following data:

- PR Title: "{title}"
- Total Issues Detected: {len(issues)}
- Files Affected: {len(file_groups)}
- Total Commits: {commits}
- Lines Added: {additions}
- Lines Deleted: {deletions}

Base your evaluation on code cleanliness, lint adherence, readability, and developer discipline. Consider if the code followed best practices, had minimal issues, and was neatly structured.

Respond with:
- A creative title (e.g., "Code Ninja", "Syntax Sorcerer", etc.)
- A rating out of 5 stars (⭐️) — use only full stars
- A one-liner review summary using professional yet light-hearted emojis.

Be motivational but fair. If there are many issues, reduce the score accordingly. If it's a clean PR, reward it well. Aim for constructive and encouraging language.
""")
rating_resp = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a professional, playful yet insightful code reviewer."},
        {"role": "user",   "content": rating_prompt}
    ],
    temperature=0.0, # Keep temperature low for consistent ratings
    max_tokens=120
)
rating = rating_resp.choices[0].message.content.strip()

md = []

# Prepend your logo
md.append(f'<img src="{img_url}" width="100" height="100" />')
md.append('')
# Title on its own line
md.append('# brandOptics AI Neural Nexus Review')
md.append('')

# Blank line between title and summary
md.append("## 📊 Review Summary & Recommendations")
md.append("")
md.append(f"Detected **{len(issues)} issue(s)** across **{len(file_groups)} file(s)** in this Pull Request.")
md.append("")

md.append(f"> 🧑‍💻 **Developer Performance Insight for @{dev_name}**")
for line in rating.splitlines():
    md.append(f"> {line}")

md.append("---")
md.append("### 📝 Pull Request Overview")
md.append("")
md.append("| Detail               | Value                                                 |")
md.append("|:---------------------|:------------------------------------------------------|")
md.append(f"| **Title** | {title}                                               |")
md.append(f"| **PR Link** | [#{pr_number}]({url})                                  |")
md.append(f"| **Author** | @{dev_name}                                           |")
md.append(f"| **Branches** | `{source_branch}` &#8594; `{target_branch}`             |") # Using Unicode arrow
md.append(f"| **Opened On** | {formatted_created_at}                                 |")
md.append(f"| **Commits** | {commits}                                             |")
md.append(f"| **Lines Added** | {additions}                                           |")
md.append(f"| **Lines Removed** | {deletions}                                           |")
md.append(f"| **Files Changed** | {len(changed_files_list)} (`{'`, `'.join(changed_files_list)}`) |")
md.append("---")
md.append(dedent("""
Thank you for your contribution! A few adjustments are recommended before this Pull Request can be merged.

🔍 **Key Areas for Refinement:**
1.  **Errors & Warnings:** Please address any compilation errors or linting violations identified.
2.  **Code Consistency:** Ensure naming conventions, formatting, and coding styles align with project standards.
3.  **Clarity & Readability:** Simplify complex logic, remove redundant code, and add concise comments where necessary.
4.  **Performance & Security:** Optimize critical code paths and validate all inputs to prevent vulnerabilities.
5.  **Tests & Documentation:** Update existing tests or add new ones for changes in logic, and refresh any relevant documentation.

💡 **Best Practice Tip:**
Consider breaking down large functions or complex changes into smaller, single-purpose units. This improves readability, simplifies testing, and makes future maintenance more manageable.

Once these suggestions are addressed and you push a new commit, I will automatically re-review and provide an updated assessment. 🚀
"""))
md.append('')
# Blank line to separate from the rest of the content

# Troll Section - placed before detailed issues, but after general advice
troll_prompt = dedent("""
Invent a completely new, funny, over-the-top **office prank or office troll** that could happen at a software company.
Requirements:
- Make it DIFFERENT each time you write it
- It can involve Developers, QA, Management, or any other team
- Keep it SHORT (max 5 lines)
- Use plenty of fun emojis
- Do NOT always repeat the same joke style — be creative!
Generate ONE such funny prank now:
""")
troll_resp = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a playful office troll, known for harmless but hilarious pranks."},
        {"role": "user",   "content": troll_prompt}
    ],
    temperature=0.9, # Higher temperature for more creative pranks
    max_tokens=100
)
troll = troll_resp.choices[0].message.content.strip()

md.append("> 🎭 _Prank War Dispatch:_")    # ← use '>' for blockquotes
for line in troll.splitlines():
    md.append(f"> {line}")                # each line must also start with '>'
md.append('') # Add a blank line after the troll section

md.append('## 📂 Detailed Issue Breakdown & AI Suggestions')
md.append('')

# List of files in the PR to retrieve patches
pr_files = {f.filename: f.patch for f in pr.get_files() if f.patch}

# Iterate through file groups for detailed reporting
for file_path, file_issues in sorted(file_groups.items()):
    md.append(f"### File: `{file_path}`")
    md.append('')
    md.append('| Line No. | Lint Rule / Error Message      | Suggested Fix (Summary)          |')
    md.append('|:--------:|:-------------------------------|:---------------------------------|')

    patch = pr_files.get(file_path, '') # Get the patch for the current file

    details_for_file = [] # Collect details for this file's collapsible sections
    if file_issues:
        for it in sorted(file_issues, key=lambda x: x['line']):
            ln = it['line']
            issue_md = f"`{it['code']}`: {it['message']}"
            ctx = get_patch_context(patch, ln)
            ai_out = ai_suggest_fix(it['code'], ctx, file_path, ln, it['message'])

            # --- CORRECTED EXTRACTION LOGIC ---
            analysis_content = "No specific analysis provided."
            full_fix_content = "No suggested fix snippet provided."
            rationale_content = "No rationale provided."

            # Regex to find sections. Using (?s) for dotall mode to match across lines.
            # Adding non-greedy quantifiers (.*?) to ensure it stops at the next heading.
            analysis_match = re.search(r'(?s)^\*\*Analysis:\*\*\s*\n(.*?)^\*\*Suggested Fix:\*\*', ai_out, re.MULTILINE)
            if analysis_match:
                analysis_content = analysis_match.group(1).strip()

            suggested_fix_match = re.search(r'(?s)^\*\*Suggested Fix:\*\*\s*\n(.*?)^\*\*Rationale:\*\*', ai_out, re.MULTILINE)
            if suggested_fix_match:
                # This should capture the descriptive text AND the code block within it.
                full_fix_content = suggested_fix_match.group(1).strip()
            
            rationale_match = re.search(r'(?s)^\*\*Rationale:\*\*\s*\n(.*)$', ai_out, re.MULTILINE)
            if rationale_match:
                rationale_content = rationale_match.group(1).strip()
            # --- END CORRECTED EXTRACTION LOGIC ---


            # Use the first few lines of the fix as a summary for the table
            # Extract only the code part for the summary, if present
            summary_code_match = re.search(r'```(?:\w*\n)?([\s\S]*?)```', full_fix_content)
            summary_text_for_table = ""
            if summary_code_match:
                summary_text_for_table = summary_code_match.group(1).strip()
            else:
                # If no code block is found, take a snippet of the general text
                summary_text_for_table = full_fix_content.splitlines()[0] if full_fix_content else "See details for suggested fix."


            summary_lines = summary_text_for_table.splitlines()[:3]
            summary = ' '.join(summary_lines).replace('|','\\|')
            if len(summary_text_for_table.splitlines()) > 3 or (len(summary_lines) == 1 and len(summary) > 50):
                summary += '...'
            
            # If the summary is empty after extraction, fall back to a default
            if not summary.strip():
                summary = "See details for suggested fix."

            md.append(f"| {ln} | {issue_md} | `{summary}` |")
            details_for_file.append({
                'line': ln,
                'analysis': analysis_content,
                'full_fix': full_fix_content, # This now contains intro text + code block
                'rationale': rationale_content,
            })
    md.append('') # Blank line after the table for this file

    # Append detailed collapsible sections for each issue in this file
    if details_for_file:
        for detail in details_for_file:
            md.append('<details>')
            md.append(f'<summary><strong>⚙️ Line {detail["line"]} – Detailed AI Insights ---------------------------------</strong> (click to expand)</summary>')
            md.append('')
            md.append(f'**Analysis:**\n{detail["analysis"]}')
            md.append('')
            # Directly append the full_fix content. It is expected to contain the code block within it.
            md.append(f'**Suggested Fix:**\n{detail["full_fix"]}')
            md.append('')
            md.append(f'**Rationale:**\n{detail["rationale"]}')
            md.append('')
            md.append('</details>')
            md.append('') # Blank line after each detail section

    md.append('---') # Separator between files

# Handle the "No issues found" case
if not issues:
    md.clear() # Clear existing content if no issues were found
    md.append(f'<img src="{img_url}" width="100" height="100" />')
    md.append('')
    md.append('# brandOptics AI Neural Nexus Review: All Clear! ✨')
    md.append('')
    md.append(f'Congratulations, @{dev_name}! Your Pull Request has successfully passed all automated code quality checks. Your code is clean, adheres to best practices, and is optimized for performance. 🚀')
    md.append('')
    md.append("---")
    md.append("### 📝 Pull Request Overview")
    md.append("")
    md.append("| Detail               | Value                                                 |")
    md.append("|:---------------------|:------------------------------------------------------|")
    md.append(f"| **Title** | {title}                                               |")
    md.append(f"| **PR Link** | [#{pr_number}]({url})                                  |")
    md.append(f"| **Author** | @{dev_name}                                           |")
    md.append(f"| **Branches** | `{source_branch}` &#8594; `{target_branch}`             |") # Using Unicode arrow
    md.append(f"| **Opened On** | {formatted_created_at}                                 |")
    md.append(f"| **Commits** | {commits}                                             |")
    md.append(f"| **Lines Added** | <span style='color:green;'>+{additions}</span>         |") # Added inline styling
    md.append(f"| **Lines Removed** | <span style='color:red;'>-{deletions}</span>           |") # Added inline styling
    md.append(f"| **Files Changed** | {len(changed_files_list)} (`{'`, `'.join(changed_files_list)}`) |")
md.append("---")
md.append("### 🏅 Developer Performance Rating")
md.append("")
md.append(">") # Start the blockquote
# Split the rating into its components if possible, or just iterate lines
rating_lines = rating.splitlines()

if rating_lines:
    # Get the original first line from the AI's rating output
    original_title_line = rating_lines[0]
 
    cleaned_title = re.sub(r'^\s*#+\s*Title:\s*', '', original_title_line, flags=re.IGNORECASE).strip()

    # Now append the cleaned and bolded title
    md.append(f"> **{cleaned_title}**") # Bold the title

    if len(rating_lines) > 1:
        md.append(f"> {rating_lines[1]}") # The stars line
    if len(rating_lines) > 2:
        # The remaining lines are the summary message
        # Iterate from index 2 for the message part
        for i in range(2, len(rating_lines)):
            md.append(f"> {rating_lines[i]}") # Append remaining lines as part of the blockquote

    md.append("") # End the blockquote (by adding a blank line outside it)

    # Generate a quick AI‐driven developer joke
    joke_resp = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            { "role": "system", "content": "You are a witty developer assistant. Always provide a short, fun programming joke." },
            { "role": "user",   "content": "Tell me a short, fun programming joke about clean code reviews or developers." }
        ],
        temperature=0.8,
        max_tokens=60
    )
    joke = joke_resp.choices[0].message.content.strip()
    md.append('---')
    md.append(f'💬 **Developer Humor Break:** {joke}')
    md.append('')


# --- 9) POST COMMENT & STATUS ───────────────────────────────────────────
final_comment_body = '\n'.join(md)
try:
    pr.create_issue_comment(final_comment_body)
    print(f"Posted AI review for PR #{pr_number}")
except Exception as e:
    print(f"Error posting comment to PR #{pr_number}: {e}")
    # Fallback to outputting the comment body to stdout for debugging in CI
    print("\n--- Generated Comment Body (for debugging) ---")
    print(final_comment_body)
    print("---------------------------------------------")

total_issues = len(issues)

# Set commit status
repo.get_commit(full_sha).create_status(
    context='brandOptics AI Neural Nexus Code Review',
    state='failure' if issues else 'success',
    description=('Issues detected—please refine your code and push updates.' if issues else 'No code issues detected. Ready for merge!')
)