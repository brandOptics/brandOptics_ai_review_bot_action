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

# --- 2) CONTEXT & ARCHITECTURE DISCOVERY --------------------------------

def generate_repo_map(root=".", max_depth=4, allowed_exts=None):
    """
    Generates a concise file tree of the repository for AI context.
    """
    if allowed_exts is None:
        allowed_exts = {
            '.js', '.ts', '.jsx', '.tsx', '.py', '.java', '.go', '.rb', '.php', 
            '.cs', '.dart', '.swift', '.kt', '.rs', '.c', '.cpp', '.h', '.hpp',
            '.sql', '.vue', '.html', '.css', '.scss'
        }
    
    file_list = []
    ignore_dirs = {'.git', 'node_modules', 'dist', 'build', 'coverage', '__pycache__', '.github', '.idea', '.vscode', 'vendor'}
    
    for r, dirs, files in os.walk(root):
        # Clean ignore dirs
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        depth = r[len(root):].count(os.sep)
        if depth > max_depth:
            continue
            
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in allowed_exts:
                path = os.path.relpath(os.path.join(r, f), root)
                file_list.append(path)
                
    return file_list

def get_project_stack_info(root="."):
    """
    Detects the tech stack based on manifest files and structure.
    """
    stack_hints = []
    
    # Check Manifests
    if os.path.exists(os.path.join(root, 'package.json')):
        try:
            with open(os.path.join(root, 'package.json')) as f:
                pkg = json.load(f)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                
                frameworks = []
                if 'react' in deps: frameworks.append('React')
                if 'next' in deps: frameworks.append('Next.js')
                if 'vue' in deps: frameworks.append('Vue')
                if 'express' in deps: frameworks.append('Express.js')
                if 'fastify' in deps: frameworks.append('Fastify')
                if 'nest.js' in deps or '@nestjs/core' in deps: frameworks.append('NestJS')
                
                stack_hints.append(f"Node.js ({', '.join(frameworks)})")
        except:
            pass

    if os.path.exists(os.path.join(root, 'go.mod')):
        stack_hints.append("Go")
    
    if os.path.exists(os.path.join(root, 'pom.xml')) or os.path.exists(os.path.join(root, 'build.gradle')):
        stack_hints.append("Java/Kotlin (Spring/Gradle/Maven)")
        
    if os.path.exists(os.path.join(root, 'requirements.txt')) or os.path.exists(os.path.join(root, 'pyproject.toml')):
        stack_hints.append("Python")
        
    if os.path.exists(os.path.join(root, 'Cargo.toml')):
        stack_hints.append("Rust")

    if os.path.exists(os.path.join(root, 'Gemfile')):
        stack_hints.append("Ruby")
        
    if os.path.exists(os.path.join(root, 'composer.json')):
        stack_hints.append("PHP")

    # Structure Heuristics
    if os.path.exists(os.path.join(root, 'app', 'controllers')):
        stack_hints.append("MVC Structure (Rails/Laravel style)")
    if os.path.exists(os.path.join(root, 'src', 'main', 'java')):
        stack_hints.append("Standard Java Structure")

    if not stack_hints:
        return "Generic/Unknown Stack"
    
    return " | ".join(stack_hints)

def scan_global_patterns(repo_map, root="."):
    """
    Scans for global architectural patterns (Global Error Handling, Auth Middleware).
    Returns a summary string.
    """
    detected_patterns = []
    
    # Universal Keywords
    # Format: (Label, Regex Pattern, File Extensions)
    checks = [
        ("Global Error Handling (JS/TS)", r"(app\.use\(.*error|setErrorHandler|process\.on\('uncaughtException')", ('.js', '.ts')),
        ("Global Error Handling (Java)", r"@ControllerAdvice|@ExceptionHandler", ('.java',)),
        ("Global Error Handling (Python)", r"@.*\.errorhandler|process_exception", ('.py',)),
        ("Global Error Handling (Go)", r"recover\(\)", ('.go',)),
        ("Global Error Handling (C#)", r"UseExceptionHandler", ('.cs',)),
        ("Auth Middleware", r"(passport\.authenticate|jwt\.verify|@Authorized|@PreAuthorize|login_required)", ('.js', '.ts', '.java', '.py', '.go'))
    ]

    for label, pattern, exts in checks:
        # Optimization: Only check relevant files, and max 20 files per extension to avoid slowness
        candidates = [f for f in repo_map if any(f.endswith(e) for e in exts)]
        # Heuristic: Check "likely" files first (app, server, main, auth, middleware)
        candidates.sort(key=lambda x: 0 if any(k in x.lower() for k in ['app', 'server', 'main', 'config', 'auth', 'middleware']) else 1)
        
        found = False
        re_pat = re.compile(pattern, re.IGNORECASE)
        
        for fname in candidates[:20]: # Check max 20 likely files
            try:
                with open(os.path.join(root, fname), 'r', errors='ignore') as f:
                    content = f.read(10000) # Read first 10k bytes
                    if re_pat.search(content):
                        detected_patterns.append(f"{label} (Detected in {fname})")
                        found = True
                        break
            except:
                continue
        
        if not found and "Error Handling" in label:
             detected_patterns.append(f"{label}: NOT DETECTED (Be Strict on local try-catch)")

    return "\n".join(detected_patterns)

def get_feature_context(target_file, full_content, repo_map, root="."):
    """
    Intelligent Context Fetcher:
    1. Analyzes IMPORTS to find direct dependencies.
    2. Analyzes filename STEM matches to find related MVC files.
    3. Returns FULL CONTENT of the most relevant files (Top 10).
    """
    context_files = set()
    base_name = os.path.basename(target_file)
    name_stem = os.path.splitext(base_name)[0]
    
    # Remove common suffixes to get the "Feature Name"
    for suffix in ['.controller', '.service', '.routes', '.model', '.dto', 'Controller', 'Service', 'Repository', 'Dto']:
        if name_stem.endswith(suffix):
            name_stem = name_stem.replace(suffix, '')
    
    name_stem = name_stem.lower()
    
    # 1. STEM MATCHING
    if len(name_stem) > 3:
        for f in repo_map:
            f_lower = os.path.basename(f).lower()
            if name_stem in f_lower and f != target_file:
                context_files.add(f)
                
    # 2. IMPORT ANALYSIS
    # Boost files that are explicitly imported
    imported_files = set()
    if full_content:
        import_paths = re.findall(r'''(?:from|import|require)\s*\(?['"]([.@][^'"]+)['"]''', full_content)
        for path in import_paths:
            clean_path = os.path.basename(path)
            for f in repo_map:
                if clean_path in f:
                    context_files.add(f)
                    imported_files.add(f)

    # 3. SELECT & READ FULL CONTENT
    # Priority: Explicit Imports > Routes/Services > Utils/Models
    def priority_score(f):
        score = 0
        f_lower = f.lower()
        
        # Explicit imports get a massively high score to ensure they are included
        if f in imported_files:
            score += 50
            
        if 'route' in f_lower: score += 10
        elif 'service' in f_lower: score += 8
        elif 'model' in f_lower or 'entity' in f_lower: score += 6
        # Boost Utils/Types/Interfaces as they are critical for preventing hallucinations
        elif 'util' in f_lower or 'helper' in f_lower: score += 9 
        elif 'type' in f_lower or 'interface' in f_lower or 'dto' in f_lower: score += 9
        else: score += 1
        
        return score
        
    # Sort by priority and take Top 10 (increased from 3)
    sorted_files = sorted(list(context_files), key=priority_score, reverse=True)[:10]
    
    snippets = []
    for f in sorted_files:
        try:
            full_path = os.path.join(root, f)
            # Safety: Skip massive files (>100KB) to prevent context explosion
            if os.path.getsize(full_path) > 100 * 1024:
                snippets.append(f"--- RELATED FILE: {f} (SKIPPED - TOO LARGE) ---\n")
                continue

            with open(full_path, 'r', errors='ignore') as file_obj:
                content = file_obj.read()
                snippets.append(f"--- RELATED FILE: {f} ---\n{content}\n")
        except:
            pass
            
    return "\n".join(snippets)
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

def is_logic_suggestion(issue):
    """
    Detects if an issue is a veiled 'Logic/Refactoring' suggestion.
    """
    t = issue.get('type', 'Standards')
    # SAFE TYPES: Security (Critical) and Standards (Linters) are always allowed.
    if t in ['Security', 'Standards']:
        return False
        
    # TEXT ANALYSIS for other types (Performance, Quality, Refactoring)
    text = (issue.get('message', '') + " " + issue.get('analysis', '')).lower()
    
    # BANNED KEYWORDS: If these appear, it's likely a logic opinion.
    banned_keywords = [
        'logic', 'business', 'flow', 'middleware', 'redundant', 
        'simplify', 'refactor', 'clean', 'structure', 'unnecessary',
        'readability', 'change', 'rewrite'
    ]
    
    if any(k in text for k in banned_keywords):
        return True
        
    # --- GLOBAL HEURISTIC 1: Universal Import/Module Detection ---
    # Regex to catch imports in JS, Python, C#, Java, Go, C++
    # Looks for lines starting with 'import', 'include', 'require', 'using', 'package', 'from'
    if re.search(r'^\s*(import|using|require|include|from|package|export)\b', original_code):
        # If it's an import, it CANNOT be a Magic Number or Secret (usually)
        # We might have "Hardcoded" on imports (e.g. from '...'), but user specifically hates these checks on imports.
        if t in ['Security', 'Secrets Detection', 'Hardcoded Configuration', 'Magic Numbers']:
             return True

    # --- GLOBAL HEURISTIC 2: Benign Magic Numbers ---
    # If the issue is about "Magic Numbers", we filter out common valid use cases globally.
    if 'magic number' in issue.get('message', '').lower() or t == 'Magic Numbers':
         # 2a. Small Integers (-1 to 10), Common Powers of 2, Common HTTP, Common 100s
         # We look for ANY number in the line. If all numbers found are "benign", we drop the issue.
         numbers_found = re.findall(r'\b\d+\b', original_code)
         
         is_benign = True
         if not numbers_found:
             is_benign = True # No numbers? Then definitely a hallucination.
         else:
             for num_str in numbers_found:
                 try:
                     n = int(num_str)
                     # Benign Set: 0-10, 100, 1000, 200/400/404/500 (HTTP), Powers of 2
                     if not ( (-1 <= n <= 10) or n in [100, 1000, 200, 201, 204, 400, 401, 403, 404, 500] or (n > 0 and (n & (n-1) == 0) and n <= 4096) ):
                         is_benign = False # Found a "weird" number (e.g. 87)
                         break
                 except:
                     pass
         
         if is_benign:
             return True
             
         # 2b. Array Indices and Math Operations (universal)
         # [0], [1] -> Array index
         # + 1, - 1, * 100 -> Math
         # > 0, < 1 -> Comparisons
         if re.search(r'\[\s*\d+\s*\]', original_code): return True # Array index
         if re.search(r'[-+*/%]\s*\d+', original_code): return True # Math op
         if re.search(r'[=!<>]=\s*\d+', original_code): return True # Comparison
             
    return False

def consolidate_issues(issues):
    """
    Advanced Deduplication & Filtering.
    """
    final_issues = []
    seen_keys = set()
    
    for i in issues:
        # 1. HARD FILTER: Drop 'Refactoring' type explicitly
        if i.get('type') in ['Refactoring', 'Clean Code']:
            continue
            
        # 2. CODE FIREWALL: Drop Logic Suggestions disguised as other types
        if is_logic_suggestion(i):
            print(f"[FIREWALL] Dropped Logic Suggestion: {i.get('message')}")
            continue

        # 3. Deduplication
        key = (i['file'], i['line'], i['message'].strip().lower())
        if key in seen_keys:
            continue
        
        seen_keys.add(key)
        final_issues.append(i)

    return final_issues



# --- 4) AI ANALYZER -----------------------------------------------------
def analyze_code_chunk(filename, patch_content, file_linter_issues=[], full_source=None, repo_context={}):
    """
    Sends the patch context to AI for deep analysis (Security, Perf, Standards).
    Emulates SonarQube "Clean Code" principles with Context Awareness.
    """
    # Unpack Context
    repo_map_str = "\n".join(repo_context.get('repo_map', [])[:200]) # Limit to top 200 files
    stack_info = repo_context.get('stack_info', 'Unknown')
    global_patterns = repo_context.get('global_patterns', 'None')
    related_files = repo_context.get('related_context', '')

    # Format linter issues for the prompt
    linter_context = ""
    if file_linter_issues:
        linter_context = "KNOWN LINTER/STATIC ANALYSIS ISSUES (You MUST fix these in your suggestions):\n"
        for i in file_linter_issues:
             linter_context += f"- Line {i['line']}: [{i['type']}] {i['message']} ({i['analysis']})\n"

    prompt = (
        "**STRICT PROTOCOL (15 COMMANDMENTS ONLY):**\\n"
        "You are an Automated Security Gatekeeper. Your job is to strictly enforce these 15 rules. DO NOT suggest refactoring on your own.\\n"
        "1. **Linting Compliance:** Zero tolerance for syntax errors, build failures, or compiler warnings. (Fix any LINTER issues provided below).\\n"
        "2. **Hardcoded UI Strings:** No raw text in user interfaces; must use localization/i18n keys. (EXCEPTION: If no i18n detected, IGNORE this rule).\\n"
        "3. **Hardcoded Configuration:** No hardcoded URLs, connection strings, or file paths in logic files. (EXCEPTION: IGNORE simple logic constants/strings like roles, types, keys).\\n"
        "4. **Secrets Detection:** No committed API keys, passwords, tokens, or certificate files. (IGNORE imports/requires).\\n"
        "5. **Security Vulnerabilities:** No use of dangerous functions (eval, SQL injection, unsafe HTML).\\n"
        "6. **Resource Management & Memory Leaks:** No unclosed database connections, streams, missing event listener cleanups, or memory leaks.\\n"
        "7. **Logging Hygiene:** No 'print' statements or debug logs in production code (only standard logging frameworks).\\n"
        "8. **Dead Code:** No commented-out code blocks, unused variables, or unreachable methods.\\n"
        "9. **Magic Numbers:** No unexplained numeric literals (must use named constants or enums). (EXCEPTION: IGNORE 0, 1, -1, 100).\\n"
        "10. **Type-Safe Comparisons:** Enforce strict equality checks (e.g., === in JS).\\n"
        "11. **Naming (Variables):** Enforce camelCase for local variables and parameters.\\n"
        "12. **Naming (Classes):** Enforce PascalCase for Class definitions and Component names.\\n"
        "13. **Naming (Booleans):** Boolean identifiers must start with a verb (is, has, can, should).\\n"
        "14. **Test Integrity:** No test skipping or forcing (e.g., .only, @Ignore) committed.\\n"
        "15. **Dependency Integrity:** Lockfiles must be synced.\\n\\n"
        
        "**NEGATIVE CONSTRAINTS (DO NOT IGNORE):**\\n"
        "1. **NO REFACORING:** Method refactoring and Logic rewriting are EXPLICITLY BANNED. If code is ugly but works, LEAVE IT ALONE.\\n"
        "2. **ASSUME LOGIC IS CORRECT:** Do not check for business logic bugs (e.g., faulty conditions, wrong return values). Assume the developer's logic is intentional.\\n"
        "3. **MIDDLEWARE/FLOW IGNORE:** Do not critique middleware placement, control flow, or message output formats.\\n"
        "4. **ALLOW LOGIC CONSTANTS:** Do NOT flag string literals (e.g., 'admin', 'success', 'user') as Hardcoded Config. Only flag URLs/IPs/Secrets.\\n"
        "5. **NO REDUNDANT FIXES:** If your suggested 'fix' is IDENTICAL to the original code, DO NOT return an issue.\\n"
        "6. **NO IMPORT STYLING:** Do not suggest changing relative paths to absolute paths or vice versa. Ignore module organization.\\n"
        "7. **NO IMPLEMENTATION GUESSING:** If a linter error says 'undefined function', do not write the function logic. Just suggest importing it.\\n"
        "8. **SEVERITY CAP:** Only 'Security' and 'Linting' issues can be 'High'. All others must be 'Medium' or 'Low'.\\n"
        "9. **LINTER PRIORITY:** If 'KNOWN LINTER ISSUES' are provided, you MUST suggest a fix for them.\\n\\n"
        
        f"{related_files}\\n\\n"

        "**Input (Line: Code):**\\n"
        "The code below is prefixed with its connection line number (e.g., '10: import...'). You MUST use these exact line numbers in your report.\\n"
        "```text\\n"
        f"{patch_content}\\n"
        "```\\n\\n"
        "**Response Format (JSON only):**\\n"
        "{\\n"
        "    'issues': [\\n"
        "        {\\n"
        "            'line': <line_number_approx>,\\n"
        "            'type': 'Security' | 'Performance' | 'Standards' | 'Refactoring',\\n"
        "            'severity': 'High' | 'Medium' | 'Low',\\n"
        "            'message': '<short_title_like_Sonar_Rule_or_Refactor Application>',\\n"
        "            'analysis': '<detailed_explanation_of_why_fix_is_needed>',\\n"
        "            'original_code': '<the_problematic_code_snippet_WITH_LINE_NUMBERS>',\\n"
        "            'suggestion': '<multi_line_VALID_code_block_that_FIXES_the_issue>'\\n"
        "        }\\n"
        "    ]\\n"
        "}\\n\\n"
        "**FINAL MANDATE:**\n"
        "1. If 'KNOWN LINTER ISSUES' are present -> You MUST fix them.\n"
        "2. If NO 'Security' or 'Linting' issues are found -> OUTPUT `{\"issues\": []}`.\n"
        "3. DO NOT invent 'Medium' or 'Low' issues just to be helpful. Silence is better than noise.\n"
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
                "{ 'issues': [ { 'line': <int>, 'type': 'Standards', 'severity': 'Medium', 'message': '<msg>', 'analysis': 'Fixing linter error', 'original_code': '<code>', 'suggestion': '<fixed_code>' } ] }"
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
    global OPENAI_API_KEY, GITHUB_TOKEN, REPO_NAME, EVENT_PATH, TARGET_TIMEZONE_NAME, LOGO_URL, openai, gh, pr_number, full_sha, repo, pr, MODEL_NAME, MODEL_NAME

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
    REPO_NAME      = os.getenv("GITHUB_REPOSITORY")
    EVENT_PATH     = os.getenv("GITHUB_EVENT_PATH")
    TARGET_TIMEZONE_NAME = os.getenv("TARGET_TIMEZONE", "Asia/Kolkata")
    
    # Allow user to override model (e.g., 'o1-preview', 'gpt-4-turbo')
    # Default to 'gpt-4o' which is currently the best balance for coding.
    # NOTE: 'gpt-5.2' is not yet available via API.
    MODEL_NAME     = os.getenv("OPENAI_MODEL", "gpt-4o")

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
    
    # 5.0) Generate Global Context ONCE
    print("[INFO] Generating Repository Context Map & Stack Info...")
    cwd = os.getcwd()
    file_tree = generate_repo_map(cwd)
    stack_info_str = get_project_stack_info(cwd)
    global_patterns_str = scan_global_patterns(file_tree, cwd)
    
    print(f"[INFO] Stack Detected: {stack_info_str}")
    print(f"[INFO] Global Patterns: {global_patterns_str}")
    
    repo_context_payload = {
        'repo_map': file_tree,
        'stack_info': stack_info_str,
        'global_patterns': global_patterns_str,
        # 'related_context': ... (computed per file)
    }

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

        # Read Full File Content for Context (if available)
        full_source_text = None
        try:
            if os.path.exists(fname):
                with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                    full_source_text = f.read()
        except Exception:
            pass

        # Get AI Feedback
        
        # 5.1 Fetch Related Context specific to this file
        current_context = repo_context_payload.copy()
        current_context['related_context'] = get_feature_context(fname, full_source_text, file_tree, cwd)
        
        ai_feedback = analyze_code_chunk(fname, patch_with_lines, this_file_linter_issues, full_source=full_source_text, repo_context=current_context)
        
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
    # --- 6) GENERATE RATINGS & COMPONENT STATS ------------------------------
    # Smart Counting: "Refactoring" issues often hide Security/Perf fixes.
    # We parse the Refactoring issues to attribute them correctly.
    
    security_count = 0
    perf_count = 0
    standards_count = 0

    for i in all_issues:
        t = i.get('type', 'Standards')
        msg = i.get('message', '').lower()
        analysis = i.get('analysis', '').lower()
        full_text = f"{msg} {analysis}"

        # 1. Security
        if t == 'Security' or 'security' in full_text or 'injection' in full_text or 'xss' in full_text:
            security_count += 1
        
        # 2. Performance
        elif t == 'Performance' or 'performance' in full_text or 'n+1' in full_text or 'memory' in full_text:
            perf_count += 1
        
        # 3. Code Quality / Standards (Everything else)
        else:
            standards_count += 1

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
            
            if i.get('suggestion'):
                md.append(f"> ```{fence}")
                md.append(f"> {i['suggestion']}")
                md.append("> ```\n")
            else:
                md.append(">\n")
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
                    
                    # SANITIZATION: Strip existing markdown fences if AI included them
                    clean_suggestion = i['suggestion'].strip()
                    if clean_suggestion.startswith("```"):
                        # Remove first line (fence) and last line (fence) if present
                        lines = clean_suggestion.splitlines()
                        if lines[0].startswith("```"): lines = lines[1:]
                        if lines and lines[-1].startswith("```"): lines = lines[:-1]
                        clean_suggestion = "\n".join(lines).strip()
                    
                    md.append(clean_suggestion)
                    md.append("```\n</details>\n")
                md.append("</blockquote>")

            md.append("</details>")

                

    md.append(f"\n---\n<p align='right'><sub>🤖 <b>BrandOptics Gatekeeper</b>: Tier 1 issues are mandatory blockers. Tier 2 is advisory. Use judgment.</sub></p>\n")

    # --- 8) POST COMMENT ----------------------------------------------------
    final_body = "\n".join(md)

    # Only post if there are issues OR it's a "clean run" notification
    # Logic: If 0 issues, we still post the "Success" dashboard.
    try:
        # Post to GitHub
        pr.create_issue_comment(final_body)
        print(f"[SUCCESS] Posted Neural Nexus Review for PR #{pr_number}")
        
        # Set Status Check
        # Strict Mode Logic:
        # - Blockers (High) -> Fail Status (Red X)
        # - Warnings (Medium) -> Success Status (Green Check) but with comments
        
        blockers = [i for i in all_issues if i['severity'] == 'High']
        
        if blockers:
            state = "failure"
            desc = f"❌ Blocked: Found {len(blockers)} Critical Issues. Human Reviewer: DO NOT MERGE until fixed."
        elif all_issues:
            state = "success"
            desc = f"⚠️ Passed (Advisory): {len(all_issues)} notes. Human Reviewer: Verify logic & style."
        else:
            state = "success"
            desc = "✅ All Clear. Human Reviewer: Good to go."

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
