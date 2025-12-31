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

# --- 1) SETUP (Moved to main) ------------------------------------------

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
                        'suggestion': None
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
                        'suggestion': None
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
                    'suggestion': None
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
                        'suggestion': None
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
                    'suggestion': None
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
                        'suggestion': None
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
                        'suggestion': None
                    })

    return issues


def enrich_linter_issues(issues, patches):
    """
    Attempts to add 'original_code' to linter issues by looking up the line in the patch.
    """
    # Parse all patches once to map File -> {Line -> Code}
    file_map = {}
    for fname, patch_text in patches.items():
        pairs = parse_patch_lines(patch_text) # Returns [(line, txt)]
        file_map[fname] = {p[0]: p[1] for p in pairs}

    for i in issues:
        # If it's a linter issue (no original_code) and we have the file
        if not i.get('original_code') and i['file'] in file_map:
            line_code = file_map[i['file']].get(i['line'])
            if line_code:
                i['original_code'] = line_code.strip()
                # Do NOT add generic "Fix violation" comments. User prefers no suggestion over a dummy one.
                # if i.get('suggestion') in ["Fix analysis issue."...]: ...

    return issues

def consolidate_issues(issues):
    """
    Advanced Deduplication:
    1. If a file has a 'Refactoring' issue (from AI), suppress all individual 'Standards' (Linter) issues for that file.
       Rationale: The Refactoring logic should theoretically cover the linter fixes, and we don't want noise.
    2. Deduplicate exact string matches.
    """
    # 1. Check for files with Refactoring
    files_with_refactor = set()
    for i in issues:
        if i.get('type') == 'Refactoring':
            files_with_refactor.add(i['file'])

    final_issues = []
    seen_keys = set()

    for i in issues:
        # Strategy: If file has Refactor, skip "Standards" issues for it.
        # However, keep 'Security' or 'Performance' as they might be distinct/critical.
        if i['file'] in files_with_refactor and i.get('type') == 'Standards':
            continue

        # Normal Deduplication
        key = (i['file'], i['line'], i['message'].strip().lower())
        if key in seen_keys:
            continue
        
        seen_keys.add(key)
        final_issues.append(i)

    return final_issues

# --- 4) AI ANALYZER -----------------------------------------------------
def analyze_code_chunk(filename, patch_content, file_linter_issues=[]):
    """
    Sends the patch context to AI for deep analysis (Security, Perf, Standards).
    Emulates SonarQube "Clean Code" principles.
    """
    # Format linter issues for the prompt
    linter_context = ""
    if file_linter_issues:
        linter_context = "KNOWN LINTER/STATIC ANALYSIS ISSUES (You MUST fix these in your suggestions):\n"
        for i in file_linter_issues:
             linter_context += f"- Line {i['line']}: [{i['type']}] {i['message']} ({i['analysis']})\n"

    prompt = (
        f"You are an Expert Code Reviewer and Static Analyzer aiming to enforce **SonarQube/SonarWay** Clean Code principles.\\n"
        f"Analyze the following code changes for file: `{filename}`\\n\\n"
        "**Goal:** Identify critical issues, code smells, and security hotspots. REFACTOR code to be clean, efficient, and DRY.\\n\\n"
        
        "**CRITICAL INSTRUCTIONS:**\\n"
        "1. **REFACTORING OVER REPORTING:** If you see multiple issues (linter errors, style, duplication) in a single function/block, do NOT report them as 10 separate small issues. Report ONE 'Refactoring' issue for the whole function and provide the **COMPLETE REWRITTEN CODE** that fixes all issues.\\n"
        "2. **DUPLICATION & LOGIC:** Actively look for duplicated logic (DRY), infinite loops, off-by-one errors, and improper implementation patterns. If found, suggest a robust fix.\\n"
        "3. **REAL CODE WITH COMMENTS:** Your 'suggestion' field must contain the FIXED CODE. **Crucially**, include brief comments INSIDE the code explaining *why* you made specific changes (e.g., `// Extracted to helper for reuse`).\\n"
        "4. **FORMATTING:** Ensure the code is properly indented and uses newlines. For large methods, do NOT inline everything; use a readable multi-line format.\\n"
        "5. **MANDATORY LINTER FIXES:** If you do not provide a 'Refactoring' for a block, you **MUST** provide a specific 'Standards' fix for **EVERY** linter issue listed above. In your suggestion, show the fixed code line(s) with a comment `// Fixed: <issue_message>` above it.\\n"
        "6. **Line Numbers:** The input is formatted as `Line: Code`. Return the accurate line number where the issue starts.\\n"
        "7. **Comments:** Ignore commented-out code unless it is clearly large blocks of dead execution logic.\\n"
        "8. **Original Code Context:** When returning `original_code`, you MUST include the line numbers as provided in the input (e.g., `240: int a = 1;`).\\n\\n"

        "**Focus Areas (SonarWay):**\\n"
        "1. [Security] (SQL Injection, XSS, Hardcoded Secrets, PII Leaks, OWASP Top 10).\\n"
        "2. [Reliability] (Cognitive Complexity > 15, N+1 queries, unoptimized I/O, resource leaks).\\n"
        "3. [Maintainability] (Dead code, magic numbers, duplicate blocks, poor naming, massive functions).\\n\\n"

        f"{linter_context}\\n\\n"

        "**STRICT STANDARDS TO ENFORCE:**\\n"
        "A. **Hard Metrics:**\\n"
        "   - Nesting Depth > 4 levels -> Suggest extraction.\\n"
        "   - Function Params > 7 -> Suggest Parameter Object.\\n"
        "   - Cyclomatic Complexity > 10 -> Suggest splitting.\\n\\n"
        "B. **Naming & Style:**\\n"
        "   - Variables/Methods: camelCase (JS/Java/Dart), snake_case (Python).\\n"
        "   - Booleans should have prefixes (is, has, should).\\n\\n"
        "C. **Architecture & Logic:**\\n"
        "   - **Fail Fast:** Flag deep if/else nesting; suggest Guard Clauses.\\n"
        "   - **Error Handling:** Flag empty catch blocks or swallowed errors.\\n"
        "   - **SOLID:** Flag God Classes (SRP violation) or Tight Coupling.\\n"
        "   - **DRY:** Flag duplicated logic blocks.\\n\\n"

        "**Input (Line: Code):**\\n"
        "```text\\n"
        f"{patch_content}\\n"
        "```\\n\\n"
        "**Response Format (JSON only):**\\n"
        "[\\n"
        "    {\\n"
        "        'line': <line_number_approx>,\\n"
        "        'type': 'Security' | 'Performance' | 'Standards' | 'Refactoring',\\n"
        "        'severity': 'High' | 'Medium' | 'Low',\\n"
        "        'message': '<short_title_like_Sonar_Rule_or_Refactor Application>',\\n"
        "        'analysis': '<detailed_explanation_of_why_fix_is_needed>',\\n"
        "        'original_code': '<the_problematic_code_snippet_WITH_LINE_NUMBERS>',\\n"
        "        'suggestion': '<multi_line_VALID_code_block_that_FIXES_the_issue>'\\n"
        "    }\\n"
        "]\\n\\n"
        "**FINAL MANDATE:** If 'KNOWN LINTER ISSUES' were provided in the prompt, you **MUST** return at least one issue (either a 'Refactoring' that solves them all, or individual 'Standards' fixes). Do NOT return [] in this case.\\n"
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
        raw_data = json.loads(content)
        # Handle cases where API returns {"issues": [...]} or just [...]
        data = []
        if isinstance(raw_data, dict):
            data = raw_data.get("issues", []) or raw_data.get("result", [])
        elif isinstance(raw_data, list):
            data = raw_data
        
        # --- FALLBACK: FIXER MODE ---
        # If the "Architect" mode returned nothing, but we DO have linter issues, 
        # we must run a simpler "Fixer" mode to generate the mandatory code fixes.
        if not data and file_linter_issues:
            print(f"[INFO] Fallback: Running Fixer Mode for {filename}...")
            fixer_prompt = (
                f"Fix the following linter errors in `{filename}`. Return JSON only.\\n\\n"
                f"{linter_context}\\n\\n"
                f"**Input Code:**\\n```text\\n{patch_content}\\n```\\n\\n"
                "**Response Format:**\\n"
                "[ { 'line': <int>, 'type': 'Standards', 'severity': 'Medium', 'message': '<msg>', 'analysis': 'Fixing linter error', 'original_code': '<code>', 'suggestion': '<fixed_code>' } ]"
            )
            try:
                fix_resp = openai.chat.completions.create(
                    model='gpt-4o',
                    messages=[
                        {'role':'system', 'content': "You are a code fixer. Output valid JSON."},
                        {'role':'user', 'content': fixer_prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                fix_data = json.loads(fix_resp.choices[0].message.content)
                if isinstance(fix_data, dict):
                    data = fix_data.get("issues", []) or fix_data.get("result", [])
                elif isinstance(fix_data, list):
                    data = fix_data
            except Exception as e:
                print(f"[ERROR] Fixer Mode failed: {e}")
        
        return data

    except Exception as e:
        print(f"Error analyzing {filename}: {e}")
        return []

def main():
    # --- 1) SETUP ----------------------------------------------------------
    global OPENAI_API_KEY, GITHUB_TOKEN, REPO_NAME, EVENT_PATH, TARGET_TIMEZONE_NAME, LOGO_URL, openai, gh, pr_number, full_sha, repo, pr

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

        # Identifiy changed lines (used for validation AND context)
        changed_lines = parse_patch_lines(patch)
        
        # Filter linter issues for this file
        this_file_linter_issues = [i for i in linter_issues if i['file'] == fname]

        # CRITICAL: We MUST run AI if there are linter issues, even if parse_patch_lines returns empty 
        # (e.g., complex diffs, deps updates).
        if not changed_lines and not this_file_linter_issues:
            continue

        # Format patch with line numbers for AI Context (Fixes hallucinated line numbers)
        # If changed_lines is empty but we proceed, use raw patch or placeholders
        if changed_lines:
            patch_with_lines = "\n".join([f"{ln}: {txt}" for ln, txt in changed_lines])
        else:
            # Fallback: Just pass the raw patch if we can't parse lines but need to fix linter
            patch_with_lines = patch

        # Get AI Feedback
        ai_feedback = analyze_code_chunk(fname, patch_with_lines, this_file_linter_issues)
        
        for item in ai_feedback:
            # Enrich with filename
            item['file'] = fname
            all_issues.append(item)

    # Helper: Enrich linter issues with code context if available in patch
    all_issues = enrich_linter_issues(all_issues, patches)

    # CRITICAL: Prioritize "Rich" issues (AI) over "Empty" issues (Linter) for deduplication
    # We sort by boolean: Has Suggestion? (True first).
    # This ensures that if AI returns a fix for the *exact same* linter error, 
    # the AI version (with the code) is processed first (or overrides) in the dedupe logic.
    all_issues.sort(key=lambda x: 1 if x.get('suggestion') else 0, reverse=True)

    # Deduplicate and Consolidate: Remove redundant linter/AI overlap
    all_issues = consolidate_issues(all_issues)

    # Sort issues: High severity first (for display)
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

    def safe_badge_str(s):
        return str(s).replace("-", "--").replace("_", "__").replace(" ", "_")

    author_safe = safe_badge_str(f"@{pr.user.login}")
    files_safe = safe_badge_str(f"{pr.changed_files} Changed")

    badge_author = f"https://img.shields.io/badge/Author-{author_safe}-1f2937?style=flat-square&logo=github"
    badge_files = f"https://img.shields.io/badge/Files-{files_safe}-1f2937?style=flat-square"

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
    md.append(f"    <img src='{b_sec}' />\n    <img src='{b_perf}' />\n    <img src='{b_qual}' />\n  </p>\n</div>\n")
    md.append("\n---\n")

    # 7b) PR OVERVIEW (From "Old" Bot - Clean Summary)
    # 7b) CRITICAL FOCUS (Immediate Attention)
    top_issues = [i for i in all_issues if i['severity'] == "High"]

    if top_issues:
        md.append("### :rotating_light: Critical Focus\n*Immediate attention required.*")
        for i in top_issues:
            fence = get_language_fence(i['file'])
            md.append(f"> **:red_circle: {i['message']}** in `{i['file']}` at Line {i['line']}\n>")
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
                    md.append(f"<summary><b>Line {i['line']}: {i['message']}</b></summary>") 
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
        # STRICT MODE: Fail if ANY issue exists (Security, Low/Med/High, Lint)
        if all_issues:
            state = "failure"
            desc = f"Blocker: Found {len(all_issues)} issues. Strict policy enforced."
        else:
            state = "success"
            desc = "All Clear! Neural Nexus approves."

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
    # Soft Fail: We have already flagged the PR as "failure" in step 8 using create_status.
    # We do NOT want to fail the Action Runner itself (sys.exit(1)) because that looks like a bot crash.
    # Instead, we exit(0) so the Action completes "Successfully" (i.e. it successfully found the bugs).
    if all_issues:
        print(f"\n[INFO] Strict Policy Enforced: Found {len(all_issues)} issues. PR Status set to 'Failure'.")
        print("[INFO] Action run completed successfully (Merge blocked via Status Check).")
        sys.exit(0)
    else:
        print("\n[SUCCESS] QA PASSED. No issues found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
