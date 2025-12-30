#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import re
from pathlib import Path
from textwrap import dedent
import openai
from github import Github
import pytz
from datetime import datetime

# --- 1) SETUP ----------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
REPO_NAME      = os.getenv("GITHUB_REPOSITORY")
EVENT_PATH     = os.getenv("GITHUB_EVENT_PATH")
TARGET_TIMEZONE_NAME = os.getenv("TARGET_TIMEZONE", "Asia/Kolkata")

# LOGO & BRANDING
LOGO_URL = "https://raw.githubusercontent.com/brandOptics/brandOptics_ai_review_bot_action/main/.github/assets/bailogo.png"

if not OPENAI_API_KEY or not GITHUB_TOKEN:
    print("[ERROR] Missing OpenAI or GitHub token.")
    exit(1)

openai.api_key = OPENAI_API_KEY
gh = Github(GITHUB_TOKEN)

# --- 2) LOAD PR DATA ----------------------------------------------------
with open(EVENT_PATH) as f:
    event = json.load(f)

pr_number = event["pull_request"]["number"]
full_sha  = event["pull_request"]["head"]["sha"]
repo      = gh.get_repo(REPO_NAME)
pr        = repo.get_pull(pr_number)

dev_name = event["pull_request"]["user"]["login"]
title        = event["pull_request"]["title"]
url          = event["pull_request"]["html_url"]
source_branch = event["pull_request"]["head"]["ref"]
target_branch = event["pull_request"]["base"]["ref"]
created_at_str = event["pull_request"]["created_at"]
commits      = event["pull_request"]["commits"]
additions    = event["pull_request"]["additions"]
deletions    = event["pull_request"]["deletions"]

# --- Timezone Conversion ---
try:
    utc_dt = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_dt = pytz.utc.localize(utc_dt)
    local_tz = pytz.timezone(TARGET_TIMEZONE_NAME)
    formatted_created_at = utc_dt.astimezone(local_tz).strftime("%B %d, %Y, %I:%M %p %Z")
except Exception:
    formatted_created_at = created_at_str

# --- HELPER: LANGUAGE FENCE ---------------------------------------------
def get_language_fence(filename):
    """Returns the markdown fence identifier for a given filename."""
    ext = Path(filename).suffix.lower()
    mapping = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript', 
        '.tsx': 'tsx', '.jsx': 'jsx', '.html': 'html', '.css': 'css',
        '.java': 'java', '.go': 'go', '.rs': 'rust', '.cpp': 'cpp',
        '.c': 'c', '.cs': 'csharp', '.rb': 'ruby', '.php': 'php',
        '.swift': 'swift', '.kt': 'kotlin', '.dart': 'dart',
        '.json': 'json', '.yml': 'yaml', '.yaml': 'yaml',
        '.sh': 'bash', '.dockerfile': 'dockerfile', '.sql': 'sql',
        '.vue': 'html'
    }
    return mapping.get(ext, '')


# --- 3) PATCH PARSING & CONTEXT -----------------------------------------
def get_file_patches(pr_obj):
    """
    Retrieves patches for all changed files (excluding .github/ folder).
    Returns a dict: { filename: patch_string }
    """
    patches = {}
    for file in pr_obj.get_files():
        if file.filename.lower().startswith(".github/"):
            continue
        if file.patch:
            patches[file.filename] = file.patch
    return patches

def parse_patch_lines(patch):
    """
    Parses a unified diff patch to identify changed line numbers.
    Returns a list of (line_number, line_content) for added/modified lines.
    """
    results = []
    # Regex to capture hunk header: @@ -old_start,old_len +new_start,new_len @@
    hunk_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')
    current_line = 0

    lines = patch.splitlines()
    for line in lines:
        if line.startswith('@@'):
            match = hunk_re.match(line)
            if match:
                current_line = int(match.group(1))
            continue
        
        if line.startswith('+') and not line.startswith('+++'):
            results.append((current_line, line[1:]))
            current_line += 1
        elif line.startswith(' ') or (line.startswith('-') and not line.startswith('---')):
            if not line.startswith('-'):
                current_line += 1
    return results

# --- 3b) HELPER: LOAD LINTER REPORTS ------------------------------------
def load_json(path: Path):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        return None
    return None

def collect_linter_issues(changed_files):
    """
    Reads generated JSON reports from the previous Action steps.
    Returns a list of issues formatted like AI issues.
    """
    issues = []
    reports_dir = Path('.github/linter-reports')
    
    # 1. ESLint (Node/TS/React)
    eslint = load_json(reports_dir / 'eslint.json')
    if isinstance(eslint, list):
        for item in eslint:
            path = os.path.relpath(item.get('filePath', ''))
            if path in changed_files:
                for msg in item.get('messages', []):
                    issues.append({
                        'file': path,
                        'line': msg.get('line', 0),
                        'type': 'Standards', # Linters mostly check standards/syntax
                        'severity': 'High' if msg.get('severity', 0) == 2 else 'Medium',
                        'message': f"[ESLint] {msg.get('ruleId', 'Error')}",
                        'analysis': msg.get('message', ''),
                        'suggestion': "Fix lint violation."
                    })

    # 2. Flake8 (Python)
    flake8 = load_json(reports_dir / 'flake8.json')
    if isinstance(flake8, dict):
        for fname, errs in flake8.items():
            path = os.path.relpath(fname)
            if path in changed_files:
                for e in errs:
                    issues.append({
                        'file': path,
                        'line': e.get('line_number', 0),
                        'type': 'Standards',
                        'severity': 'High' if e.get('code', '').startswith('E') else 'Medium', # E=Error, W=Warning
                        'message': f"[Flake8] {e.get('code', 'Error')}",
                        'analysis': e.get('text', ''),
                        'suggestion': "Fix PEP8 violation."
                    })
    
    # 3. Dart Analyzer (Flutter)
    dart = load_json(reports_dir / 'dartanalyzer.json')
    if isinstance(dart, dict):
        for diag in dart.get('diagnostics', []):
            path = diag.get('location', {}).get('file', '')
            if os.path.relpath(path) in changed_files:
                issues.append({
                    'file': os.path.relpath(path),
                    'line': diag.get('location', {}).get('range', {}).get('start', {}).get('line', 0),
                    'type': 'Standards',
                    'severity': 'High' if diag.get('severity') == 'ERROR' else 'Medium',
                    'message': f"[Dart] {diag.get('code', 'Issue')}",
                    'analysis': diag.get('problemMessage', ''),
                    'suggestion': "Fix analysis issue."
                })

    # 4. SQLFluff (SQL)
    sql_report = load_json(reports_dir / 'sqlfluff.json')
    if isinstance(sql_report, list):
        for file_item in sql_report:
            path = os.path.relpath(file_item.get('filepath', ''))
            if path in changed_files:
                for v in file_item.get('violations', []):
                     issues.append({
                        'file': path,
                        'line': v.get('line_no', 0),
                        'type': 'Standards', # SQLFluff mostly checks style/syntax
                        'severity': 'Medium', # SQLFluff usually outputs warnings
                        'message': f"[SQL] {v.get('code', 'Rule')}",
                        'analysis': v.get('description', ''),
                        'suggestion': "Fix SQL style violation."
                    })

    # 5. HTMLHint (HTML)
    html_report = load_json(reports_dir / 'htmlhint.json')
    if isinstance(html_report, list):
        for item in html_report:
            path = os.path.relpath(item.get('file', ''))
            if path in changed_files:
                 issues.append({
                    'file': path,
                    'line': item.get('line', 0),
                    'type': 'Standards',
                    'severity': 'High' if item.get('type') == 'error' else 'Medium',
                    'message': f"[HTML] {item.get('rule', {}).get('id', 'Issue')}",
                    'analysis': item.get('message', ''),
                    'suggestion': "Fix HTML validation error."
                })

    # 6. Stylelint (CSS/SCSS)
    style_report = load_json(reports_dir / 'stylelint.json')
    if isinstance(style_report, list):
        for item in style_report:
            path = os.path.relpath(item.get('source', ''))
            if path in changed_files:
                for w in item.get('warnings', []):
                    issues.append({
                        'file': path,
                        'line': w.get('line', 0),
                        'type': 'Standards',
                        'severity': 'High' if w.get('severity') == 'error' else 'Medium',
                        'message': f"[CSS] {w.get('rule', 'Rule')}",
                        'analysis': w.get('text', ''),
                        'suggestion': "Fix CSS style violation."
                    })

    # 7. .NET (dotnet-format)
    # Expected format: [ { "FilePath": "...", "FileChanges": [ { "LineNumber": ... } ] } ]
    dotnet_report = load_json(reports_dir / 'dotnet-format.json')
    if isinstance(dotnet_report, list):
        for item in dotnet_report:
            path = os.path.relpath(item.get('FilePath', ''))
            if path in changed_files:
                for change in item.get('FileChanges', []):
                    issues.append({
                        'file': path,
                        'line': change.get('LineNumber', 0),
                        'type': 'Standards',
                        'severity': 'Medium', # Format issues are usually warnings
                        'message': f"[.NET] {change.get('DiagnosticId', 'Format')}",
                        'analysis': change.get('FormatDescription', 'Code style violation'),
                        'suggestion': "Apply dotnet format."
                    })

    return issues

def deduplicate_issues(issues):
    """
    Removes duplicates based on File + Line + Message.
    Prioritizes issues that have 'suggestion' (AI) over plain linter errors.
    """
    unique_map = {}
    
    for i in issues:
        # Create a key. We normalize message to avoid case-sensitivity issues
        key = (i['file'], i['line'], i['message'].strip().lower())
        
        existing = unique_map.get(key)
        if existing:
            # Conflict! Decide who stays.
            # 1. Prefer the one with a 'suggestion' (AI rich content)
            if i.get('suggestion') and not existing.get('suggestion'):
                unique_map[key] = i
            # 2. If both/neither have suggestion, prefer higher severity
            # (Note: Logic assumes 'High' < 'Medium' in severity dict, but here we just check raw string)
            elif i.get('severity') == 'High' and existing.get('severity') != 'High':
                unique_map[key] = i
        else:
            unique_map[key] = i
            
    return list(unique_map.values())

# --- 4) AI ANALYZER -----------------------------------------------------
def analyze_code_chunk(filename, patch_content):
    """
    Sends the patch context to AI for deep analysis (Security, Perf, Standards).
    Emulates SonarQube "Clean Code" principles.
    """
    prompt = (
        f"You are an Expert Code Reviewer and Static Analyzer aiming to enforce **SonarQube/SonarWay** Clean Code principles.\\n"
        f"Analyze the following code changes for file: `{filename}`\\n\\n"
        "**Goal:** Identify critical issues, code smells, and security hotspots.\\n\\n"
        "**CRITICAL RULES:**\\n"
        "1. Do NOT report issues for named constants or utility functions (e.g., dateUtils.format_21). Assume they are valid.\\n"
        "2. Do NOT report 'commented out code' unless it is clearly dead logic. Ignore comments that look like explanations.\\n"
        "3. Use the EXACT line number from the provided diff. Do NOT guess.\\n\\n"
        "**Focus Areas (SonarWay):**\\n"
        "1. [Security] (SQL Injection, XSS, Hardcoded Secrets, PII Leaks, OWASP Top 10).\\n"
        "2. [Reliability] (Cognitive Complexity > 15, N+1 queries, unoptimized I/O, resource leaks).\\n"
        "3. [Maintainability] (Dead code, magic numbers, duplicate blocks, poor naming, massive functions).\\n\\n"
        "**Input:**\\n"
        "```diff\\n"
        f"{patch_content}\\n"
        "```\\n\\n"
        "**Response Format (JSON only):**\\n"
        "[\\n"
        "    {\\n"
        "        'line': <line_number_approx>,\\n"
        "        'type': 'Security' | 'Performance' | 'Standards',\\n"
        "        'severity': 'High' | 'Medium' | 'Low',\\n"
        "        'message': '<short_title_like_Sonar_Rule>',\\n"
        "        'analysis': '<detailed_explanation>',\\n"
        "        'original_code': '<the_problematic_code_snippet_from_diff>',\\n"
        "        'suggestion': '<multi_line_fixed_code_block>'\\n"
        "    },\\n"
        "    ...\\n"
        "]\\n\\n"
        "If no significant issues, return [].\\n"
        "Ensure 'suggestion' uses proper newlines (\\n) for readability. Do not flatten code.\\n"
        "Example:\\n"
        '"suggestion": "line1();\\nline2();" NOT "line1(); line2();"'
    )

    try:
        resp = openai.chat.completions.create(
            model='gpt-4o', # Using a smarter model for "Stunning" results
            messages=[
                {'role':'system', 'content': "You are a pragmatic software architect. Output only valid JSON."},
                {'role':'user', 'content': prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = resp.choices[0].message.content
        # Ensure we get a list
        data = json.loads(content)
        # Handle cases where API returns {"issues": [...]} or just [...]
        if isinstance(data, dict):
            return data.get("issues", []) or data.get("result", [])
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error analyzing {filename}: {e}")
        return []

# --- 5) EXECUTE ANALYSIS ------------------------------------------------
patches = get_file_patches(pr)
all_issues = []

# 5a) Collect Linter Issues
linter_issues = collect_linter_issues(patches.keys())
all_issues.extend(linter_issues)

print(f"[INFO] Analyzing {len(patches)} files...")

for fname, patch in patches.items():
    # Detect if file is relevant (skip locks, assets, etc.)
    if any(fname.endswith(ext) for ext in ['.png', '.jpg', '.lock', '.json']):
        continue

    # Identify changed lines to validate AI suggestions
    changed_lines = parse_patch_lines(patch)
    if not changed_lines:
        continue

    # Get AI Feedback
    ai_feedback = analyze_code_chunk(fname, patch)
    
    for item in ai_feedback:
        # Enrich with filename
        item['file'] = fname
        all_issues.append(item)

# Deduplicate to remove redundant linter/AI overlap
all_issues = deduplicate_issues(all_issues)

# Sort issues: High severity first
severity_order = {"High": 0, "Medium": 1, "Low": 2}
all_issues.sort(key=lambda x: severity_order.get(x.get('severity', 'Low'), 2))

# --- 6) GENERATE RATINGS & COMPONENT STATS ------------------------------
security_count = sum(1 for i in all_issues if i['type'] == 'Security')
perf_count = sum(1 for i in all_issues if i['type'] == 'Performance')
standards_count = sum(1 for i in all_issues if i['type'] == 'Standards')
# Count actual linter errors (High severity standards)
linter_error_count = sum(1 for i in linter_issues if i['severity'] == 'High')

# Calculate "Scores" for badges
def get_badge(label, count, color_good="success", color_bad="critical"):
    # Use flat-square for cleaner look, less prone to rendering issues
    # Replace spaces with underscores or %20 if needed, but shields.io handles dashes better
    safe_label = label.replace(" ", "_")
    if count == 0:
        return f"https://img.shields.io/badge/{safe_label}-A--Perfect-{color_good}?style=flat-square&logo=github"
    elif count < 3:
        return f"https://img.shields.io/badge/{safe_label}-B--Warnings-yellow?style=flat-square&logo=github"
    else:
        return f"https://img.shields.io/badge/{safe_label}-C--Critical-{color_bad}?style=flat-square&logo=github"

badge_sec = get_badge("Security", security_count, "blue", "red")
badge_perf = get_badge("Performance", perf_count, "green", "orange")
badge_qual = get_badge("Code_Quality", standards_count, "success", "yellow") # Underscore ensures correct rendering

# Developer Rating Generation
rating_prompt = (
    f"Rate this PR based on stats:\\n"
    f"- Security Issues: {security_count}\\n"
    f"- Performance Issues: {perf_count}\\n"
    f"- Standards Issues: {standards_count}\\n"
    f"- Files: {len(patches)}\\n\\n"
    "Output specifically:\\n"
    "1. Star Rating (1-5 stars icons)\\n"
    "2. A Creative 'Hero Title' (e.g., Code Ninja, Bug Slayer)\\n"
    "Separated by a pipe symbol |."
)
try:
    rating_resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user", "content": rating_prompt}],
        max_tokens=50
    )
    rating_out = rating_resp.choices[0].message.content.strip()
    if "|" in rating_out:
        stars, hero_title = rating_out.split("|", 1)
    else:
        stars, hero_title = rating_out, "Code Contributor"
except:
    stars, hero_title = "***", "Code Contributor"

def get_troll_message(username):
    try:
        troll_resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user", "content": f"Tell one short, hilarious, random office prank or developer joke in 2 lines, possibly referencing a developer named {username}."}],
            temperature=0.9
        )
        return troll_resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating troll message: {e}")
        return "Why did the developer go broke? Because he used up all his cache!"

# --- 7) GENERATE MARKDOWN COMMENT ---------------------------------------
print("[INFO] Generating Hybrid Neural Nexus Comment...")

md = []

# 7a) HEADER & HUD (Executive V2: Hero Rating + Badge Row)
# Construct Badge URLs for the row
# Badge format: https://img.shields.io/badge/Label-Value-Color?style=flat-square
badge_author = f"https://img.shields.io/badge/Author-@{pr.user.login}-1f2937?style=flat-square&logo=github"
badge_files = f"https://img.shields.io/badge/Files-{pr.changed_files}_Changed-1f2937?style=flat-square"

# Helper for row badges (simpler than the table one)
def get_row_badge(label, count, color="red"):
    if count == 0: return "" # Hide if 0? Or show Green? Let's show clean stats.
    return f"https://img.shields.io/badge/{label}-{count}-{color}?style=flat-square"

# Generate badges
b_sec = get_badge('Security', security_count, 'blue', 'orange').replace('style=for-the-badge', 'style=flat-square') 
b_perf = get_badge('Performance', perf_count).replace('style=for-the-badge', 'style=flat-square')
b_qual = get_badge('Quality', linter_error_count + standards_count).replace('style=for-the-badge', 'style=flat-square')

md.append(f"\n<div align='center'>")
md.append(f"  <img src='https://raw.githubusercontent.com/brandOptics/brandOptics_ai_review_bot_action/main/.github/assets/bailogo.png' height='80' />")
md.append("  <h2>BrandOptics Neural Nexus</h2>")
md.append(f"  <h3>{stars} {hero_title}</h3>")
md.append("  <p><i>'Automated Code Intelligence v3.0'</i></p>")
md.append(f"  <p>\n    <img src='{badge_author}' />\n    <img src='{badge_files}' />")
md.append(f"    {b_sec}\n    {b_perf}\n    {b_qual}\n  </p>\n</div>\n")
md.append("\n---\n")

# 7b) PR OVERVIEW (From "Old" Bot - Clean Summary)
# 7b) CRITICAL FOCUS (Immediate Attention)
top_issues = [i for i in all_issues if i['severity'] == "High"]

if top_issues:
    md.append("### :rotating_light: Critical Focus\n*Immediate attention required.*")
    for i in top_issues:
        fence = get_language_fence(i['file'])
        md.append(f"> **:red_circle: {i['message']}** in `{i['file']}`\n>")
        md.append(f"> **Analysis:** {i['analysis']}")
        md.append(f"> ```{fence}")
        md.append(f"> {i['suggestion']}")
        md.append("> ```\n")
    md.append("\n---\n")

# 7c) Assessment (Only if clean)
elif not all_issues:
    md.append("\n### :sparkles: Assessment")
    md.append("No significant issues found. Great job maintaining code quality!")


# 7d) DETAILED ISSUE BREAKDOWN (Executive V2: Collapsible Files + Detailed Insights)
if all_issues:
    md.append("\n## :open_file_folder: File-by-File Analysis")
    
    # Group issues by file
    issues_by_file = {}
    for i in all_issues:
        f = i['file']
        if f not in issues_by_file: issues_by_file[f] = []
        issues_by_file[f].append(i)

    for filename, file_issues in issues_by_file.items():
        # Determine icon based on worst severity in file
        file_icon = ":page_facing_up:"
        if any(i['severity'] == 'High' for i in file_issues): file_icon = ":red_circle:"
        elif any(i['severity'] == 'Medium' for i in file_issues): file_icon = ":warning:"
        
        # File Collapsible Header
        md.append(f"\n<details>")
        md.append(f"<summary><b>{file_icon} {filename}</b> ({len(file_issues)} issues)</summary>\n")
        
        # 1. Summary Table
        md.append("| Line | Type | Issue |")
        md.append("| :---: | :---: | :--- |")
        
        for i in file_issues:
            # Map type to emoji
            type_icon = ":large_blue_circle:"
            if i['type'] == 'Security': type_icon = ":red_circle:"
            elif i['type'] == 'Performance': type_icon = ":warning:"
            elif i['type'] == 'Standards': type_icon = ":art:"
            
            # Message formatting
            md.append(f"| {i['line']} | {type_icon} | **{i['message']}** |")
        
        md.append("") # End table

        # 2. Detailed Fix & Rationale (Only for rich AI suggestions)
        # We check if 'suggestion' is substantive (i.e. likely AI-generated, not just a lint placeholder)
        rich_issues = [i for i in file_issues if i.get('suggestion') and len(i['suggestion']) > 20]
        
        if rich_issues:
            md.append("<blockquote>")
            md.append("<b>:brain: AI Insights & Fixes</b><br>")
            
            for i in rich_issues:
                fence = get_language_fence(filename)
                original_blk = ""
                if i.get('original_code'):
                    original_blk = f"**Original Code:**\n```{fence}\n{i['original_code']}\n```\n\n"
                
                md.append("\n<details>")
                md.append(f"<summary><b>v Line {i['line']}: {i['message']}</b></summary>") 
                md.append("<br>\n")
                md.append(f"**Why it matters:**\n{i['analysis']}\n")
                
                if original_blk:
                    md.append(original_blk)
                    
                md.append("**Suggested Fix:**")
                md.append(f"```{fence}")
                md.append(i['suggestion'])
                md.append("```\n</details>\n")
            md.append("</blockquote>")

        md.append("</details>")

            

md.append(f"\n<div align='center'>\n  <sub>Generated by <b>BrandOptics A.I.</b> - <a href='{pr.html_url}'>View PR</a></sub>\n</div>\n")

# --- 8) POST COMMENT ----------------------------------------------------
final_body = "\n".join(md)

# Only post if there are issues OR it's a "clean run" notification
# Logic: If 0 issues, we still post the "Success" dashboard.
try:
    # Post to GitHub
    pr.create_issue_comment(final_body)
    print(f"[SUCCESS] Posted Neural Nexus Review for PR #{pr_number}")
    
    # Set Status Check
    # Fail if Security Issues > 0 OR Linter Errors > 0
    # "Standards" warnings from AI do NOT cause failure (to prevent loops)
    state = "failure" if (security_count > 0 or linter_error_count > 0) else "success"
    desc = f"Found {len(all_issues)} issues." if all_issues else "All Clear! Neural Nexus approves."
    repo.get_commit(full_sha).create_status(
        context='brandOptics AI Neural Nexus',
        state=state,
        description=desc
    )

except Exception as e:
    print(f"[ERROR] Failed to post comment: {e}")
    # Print for debug
    print(final_body)
# --- 9) EXIT CODE (BLOCK MERGE) ------------------------------------------
# Ensure the Action itself fails if the check failed.
if (security_count > 0) or any(i.get("severity") == "High" for i in all_issues):
    print("\n[BLOCKING] Critical Issues Found. Fix them to proceed.")
    sys.exit(1)
else:
    print("\n[SUCCESS] QA PASSED.")
    sys.exit(0)
