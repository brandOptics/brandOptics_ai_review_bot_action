#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path
from textwrap import dedent
import openai
from github import Github

# ── 1) SETUP ──────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
REPO_NAME      = os.getenv("GITHUB_REPOSITORY")
EVENT_PATH     = os.getenv("GITHUB_EVENT_PATH")
if not OPENAI_API_KEY or not GITHUB_TOKEN:
    print("⛔️ Missing OpenAI or GitHub token.")
    exit(1)
openai.api_key = OPENAI_API_KEY
gh = Github(GITHUB_TOKEN)

# ── 2) LOAD PR DATA ────────────────────────────────────────────────────
with open(EVENT_PATH) as f:
    event = json.load(f)
pr_number = event["pull_request"]["number"]
full_sha  = event["pull_request"]["head"]["sha"]
repo      = gh.get_repo(REPO_NAME)
pr        = repo.get_pull(pr_number)

# ── 3) DETECT CHANGED FILES (exclude .github/) ─────────────────────────
changed_files = [f.filename for f in pr.get_files()
                 if f.patch and not f.filename.lower().startswith('.github/')]
if not changed_files:
    pr.create_issue_comment("🔮🧠 brandOptics AI Neural Nexus Review — no relevant code changes detected.")
    repo.get_commit(full_sha).create_status(
        context="brandOptics AI Neural Nexus Code Review",
        state="success",
        description="No relevant code changes detected."
    )
    exit(0)

# ── 4) LOAD LINTER REPORTS ─────────────────────────────────────────────
def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except:
        return None
reports_dir = Path('.github/linter-reports')
eslint_report        = load_json(reports_dir / 'eslint.json')
flake8_report        = load_json(reports_dir / 'flake8.json')
shellcheck_report    = load_json(reports_dir / 'shellcheck.json')
dartanalyzer_report  = load_json(reports_dir / 'dartanalyzer.json')
dotnet_report        = load_json(reports_dir / 'dotnet-format.json')

# ── 5) HELPERS ─────────────────────────────────────────────────────────
def get_patch_context(patch: str, line_no: int, ctx: int = 3) -> str:
    file_line = None
    hunk = []
    for line in patch.splitlines():
        if line.startswith('@@ '):
            start = int(line.split()[2].split(',')[0][1:]) - 1
            file_line = start
            hunk = [line]
        elif file_line is not None:
            prefix = line[0]
            if prefix in (' ', '+', '-'):
                if prefix != '-': file_line += 1
                if abs(file_line - line_no) <= ctx: hunk.append(line)
                if file_line > line_no + ctx: break
    return '\n'.join(hunk)

# ── 6) AI SUGGESTION ───────────────────────────────────────────────────
def ai_suggest_fix(code: str, patch_ctx: str, file_path: str, line_no: int) -> str:
    prompt = dedent(f"""
You are a Dart/Flutter expert.
Below is the diff around line {line_no} in `{file_path}` (error: {code}):
```diff
{patch_ctx}
```
Provide exactly three labeled sections:

Fix:
  Copy-friendly corrected snippet (include fences if multi-line).
Refactor:
  Higher-level best-practice improvements.
Why:
  Brief rationale.
""")
    resp = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role':'system','content':'You are a helpful assistant.'},
                  {'role':'user','content':prompt}],
        temperature=0.0,
        max_tokens=400
    )
    return resp.choices[0].message.content.strip()

# ── 7) COLLECT ISSUES ──────────────────────────────────────────────────
issues = []
# ESLint
if isinstance(eslint_report, list):
    for rep in eslint_report:
        path = os.path.relpath(rep.get('filePath',''))
        if path in changed_files:
            for msg in rep.get('messages', []):
                ln = msg.get('line')
                if ln: issues.append({'file':path,'line':ln,
                                      'code':msg.get('ruleId','ESLint'),
                                      'message':msg.get('message','')})
# Flake8
if isinstance(flake8_report, dict):
    for ap, errs in flake8_report.items():
        path = os.path.relpath(ap)
        if path in changed_files:
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
        if path in changed_files and ln: issues.append({'file':path,'line':ln,
                                                         'code':ent.get('code','ShellCheck'),
                                                         'message':ent.get('message','')})
# Dart Analyzer
if isinstance(dartanalyzer_report, dict):
    for diag in dartanalyzer_report.get('diagnostics', []):
        loc = diag.get('location', {})
        path = os.path.relpath(loc.get('file',''))
        ln = loc.get('range',{}).get('start',{}).get('line')
        if path in changed_files and ln: issues.append({'file':path,'line':ln,
                                                        'code':diag.get('code','DartAnalyzer'),
                                                        'message':diag.get('problemMessage') or diag.get('message','')})
# .NET Format
if isinstance(dotnet_report, dict):
    diags = dotnet_report.get('Diagnostics') or dotnet_report.get('diagnostics')
    if isinstance(diags, list):
        for d in diags:
            path = os.path.relpath(d.get('Path') or d.get('path',''))
            ln = d.get('Region',{}).get('StartLine')
            if path in changed_files and ln: issues.append({'file':path,'line':ln,
                                                           'code':'DotNetFormat',
                                                           'message':d.get('Message','')})

# ── 8) GROUP AND FORMAT OUTPUT ─────────────────────────────────────────
file_groups = {}
for issue in issues: file_groups.setdefault(issue['file'], []).append(issue)

# Header with summary
# at the top of your comment body…

 
md = [
    '## 🔮🧠 brandOptics AI Neural Nexus Recommendations & Code Review Suggestions',
    f'**Summary:** {len(issues)} issue(s) across {len(file_groups)} file(s).',
    ''
]

# Troll Section
troll_prompt = dedent("""
Invent a completely new, funny, over-the-top **office prank or office troll** that could happen at a software company.
Requirements:
- Make it DIFFERENT each time you write it
- It can involve Developers, QA, Management, or any other team
- It can involve code, coffee, meetings, office life, or totally absurd things
- Keep it SHORT (max 5 lines)
- Use plenty of fun emojis
- Do NOT always repeat the same joke style — be creative!
Generate ONE such funny prank now:
""")
troll_resp = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a playful office troll."},
        {"role": "user",   "content": troll_prompt}
    ],
    temperature=0.7,
    max_tokens=200
)
troll = troll_resp.choices[0].message.content.strip()

md.append("---")
md.append("> 🎭 _Prank War Dispatch:_")    # ← use '>' for blockquotes
for line in troll.splitlines():
    md.append(f"> {line}")                # each line must also start with '>'
md.append("---")


for file_path, file_issues in sorted(file_groups.items()):
    md.append(f"**File =>** `{file_path}`")
    md.append('')
    md.append('| Line No. | Lint Rule / Error Message      | Suggested Fix (Summary)          |')
    md.append('|:--------:|:-------------------------------|:---------------------------------|')
    gh_file = next(f for f in pr.get_files() if f.filename == file_path)
    patch = gh_file.patch or ''
    details = []
    for it in sorted(file_issues, key=lambda x: x['line']):
        ln = it['line']
        issue_md = f"`{it['code']}` {it['message']}"
        ctx = get_patch_context(patch, ln)
        ai_out = ai_suggest_fix(it['code'], ctx, file_path, ln)
        m = re.search(r'Fix:\s*```dart\n([\s\S]*?)```', ai_out)
        full_fix = m.group(1).strip() if m else ai_out.splitlines()[0].strip()
        lines = full_fix.splitlines()
        # richer summary: first three lines
        summary = ' '.join(lines[:3]).replace('|','\\|')
        md.append(f"| {ln} | {issue_md} | `{summary}` |")
        details.append((ln, full_fix, ai_out))
    md.append('')
    for ln, full_fix, ai_out in details:
        md.append('<details>')
        md.append(f'<summary><strong>🔍✨ Neural AI Guidance & Corrections for (Line {ln})</strong> ---------------- (click to view)</summary>')
        md.append('')
        md.append('```dart')
        md.append(full_fix)
        md.append('```')
        md.append('')
        # Refactor section
        ref = re.search(r'Refactor:\s*([\s\S]*?)(?=\nWhy:|$)', ai_out)
        if ref:
            md.append('**Refactor:**')
            md.append(ref.group(1).strip())
            md.append('')
 
        md.append('')
        md.append('</details>')
        md.append('')
if not issues:
    
    md.append(
        ' 🧠✅ BrandOptics Neural AI Review: '
        'No issues found—your code passes all lint checks, follows best practices, '
        'and is performance-optimized. 🚀 Great job, developer! Ready to merge!'
    )

    # Generate a quick AI‐driven developer joke
    joke_resp = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            { "role": "system", "content": "You are a witty developer assistant." },
            { "role": "user",   "content": "Tell me a short, fun programming joke about clean code reviews." }
        ],
        temperature=0.8,
        max_tokens=40
    )
    joke = joke_resp.choices[0].message.content.strip()

    # Append the joke under the success message
    md.append(f'💬 Joke for you: {joke}')

# ── 9) POST COMMENT & STATUS ───────────────────────────────────────────
body = '\n'.join(md)
pr.create_issue_comment(body)
total_issues = len(issues)
files_affected = len(file_groups)

if issues:
    pr.create_review(
    body= f"""
🧠✨ **brandOptics AI Neural Nexus**  
Detected **{total_issues} issue(s)** across **{files_affected} file(s)** in this PR.

👏 **Appreciation**  
Thank you for your hard work—your contribution is on the right track!

🔍 **Review Summary**  
1. **Errors & Warnings**: Resolve any compile/runtime errors and lint warnings.  
2. **Style & Conventions**: Ensure consistency in naming, formatting, and team guidelines.  
3. **Maintainability**: Simplify complex blocks, remove dead code, and write clear comments.  
4. **Performance & Security**: Optimize hot paths, manage resources correctly, and validate inputs.  
5. **Testing & Documentation**: Add or update tests and inline documentation for clarity.

💡 **Pro Tip**  
Break large modules into smaller, single-responsibility components to improve readability and testability.

Once these tweaks are applied and you push a new commit, I’ll happily re-review and merge! 🚀
""",
    event="REQUEST_CHANGES"
)

    repo.get_commit(full_sha).create_status(
        context="brandOptics AI Neural Nexus Code Review",
        state="failure",
        description="Issues detected—please refine your code and push updates."
    )
else:
    repo.get_commit(full_sha).create_status(
    context='brandOptics AI Neural Nexus Code Review',
    state='failure' if issues else 'success',
    description=('Issues detected — please refine your code.' if issues else 'No code issues detected.')
)
print(f"Posted AI review for PR #{pr_number}")