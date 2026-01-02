<div align="center">
  <img src=".github/assets/brandoptics_neural_nexus_banner.jpeg" width="100%" alt="BrandOptics Neural Nexus - AI Code Review" />

  <br />
  
  <h1>BrandOptics Neural Nexus</h1>
  <h3>Automated Code Intelligence v3.5</h3>

  <p>
    <a href="#-core-intelligence">Core Intelligence</a> •
    <a href="#-capabilities">Capabilities</a> •
    <a href="#-integration">Integration</a> •
    <a href="#-configuration">Configuration</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Status-Production_Ready-success?style=for-the-badge&logo=github" />
    <img src="https://img.shields.io/badge/Engine-Hybrid_Neuro--Symbolic-blue?style=for-the-badge&logo=openai" />
    <img src="https://img.shields.io/badge/License-Proprietary-1f2937?style=for-the-badge" />
  </p>
</div>

---

## ⚡ Core Intelligence

**Neural Nexus** is an autonomous code quality gate designed for high-velocity engineering teams. Unlike standard linters that merely flag syntax errors, Neural Nexus employs a **Hybrid Neuro-Symbolic Architecture**:

1.  **Symbolic Logic (Deterministic)**: Executes industry-standard static analysis (ESLint, Flake8, Dart Analyzer, SQLFluff) to catch hard syntax errors and style violations.
2.  **Neural Reasoning (Probabilistic)**: Uses sophisticated LLM context windows (GPT-4o) to analyze logic flow, architectural integrity, and security vulnerabilities that static tools miss.

This duality ensures **zero-tolerance** for bugs while providing **senior-level refactoring** suggestions for complex logic.

---

## 🎯 Capabilities

### 1. Auto-Refactoring & Duplication Detection
Instead of leaving vague comments like "duplicate code", Neural Nexus rewrites the code for you.
- **Deep Refactoring**: Identifies God Classes or massive functions and suggests modular breakdowns.
- **Helper Extraction**: Detecting duplicated logic across files? The bot suggests a shared utility method.
- **Inline Explanations**: Every code change includes comments explaining the *reasoning* (e.g., `// Extracted to reduce cyclomatic complexity`).

### 2. Security & Performance Guardrails
We map findings directly to **OWASP Top 10** and **SonarWay** quality profiles.
- **Security**: SQL Injection, Hardcoded Secrets, PII exposure.
- **Performance**: O(n²) loops, memory leaks, unoptimized database queries.
- **Reliability**: Empty catch blocks, race conditions, improper state management.

### 3. The Executive Dashboard
Pull Requests are annotated with a high-fidelity dashboard summarizing the health of the codebase.
- **Letter Grades**: A / B / C ratings for Security, Quality, and Performance.
- **Visual Badges**: Instant visibility into the impact of the PR.
- **Collapsible Insights**: Deep dives into specific files without cluttering the main conversation.

---

## 🌐 Language Support Matrix

| Ecosystem | Static Analysis | Neural Review | Version Support |
| :--- | :--- | :--- | :--- |
| **Flutter / Dart** | `Dart Analyzer` | ✅ Logic, Arch, Widgets | Flutter 3.x+ |
| **JavaScript / TS** | `ESLint` | ✅ Security, Hooks, A11y | Semicolon/Standard |
| **Node.js** | `ESLint` | ✅ Async Logic, Security | v18+ |
| **Python** | `Flake8` | ✅ PEP8, Complexity | 3.8+ |
| **SQL** | `SQLFluff` | ✅ Query Opt, Dialects | Postgres, MySQL |
| **.NET / C#** | `dotnet format` | ✅ Style, Patterns | .NET 6+ |

---

## 🗺️ Roadmap

- [x] **v3.5**: Mandatory Code Fixes & Deduplication Logic
- [x] **v3.5**: Enterprise Configuration Rules (Strict)
- [ ] **v4.0**: Automatic Pull Request Description Generation
- [ ] **v4.0**: JIRA / Linear Ticket Linking
- [ ] **v4.5**: Custom LLM Fine-tuning Support (Bring Your Own Model)
- [ ] **v5.0**: IDE Extensions (VS Code / IntelliJ Plugin)

---

## 🧠 Core Capabilities & Intelligence

BrandOptics Neural Nexus is not just a linter wrapper; it is a **Hybrid Intelligence Engine** that combines deterministic static analysis with probabilistic LLM reasoning.

### 🛡️ Why Trust This Review?
*   **Context-Aware Analysis**: Unlike basic bots that only see changed lines, Neural Nexus reads the **Full File Context**. It understands your imports, class definitions, and existing methods, preventing false positives about "undefined variables" or "missing validations."
*   **Anti-Hallucination Protocols**: strict directives prevent the AI from "guessing" dependencies. If it's not sure, it adheres to specific "Conservative Refactoring" rules.
*   **Hybrid Verification**: We use standard linters (ESLint, Flake8, Dart Analyzer) as the "Source of Truth" for syntax, and use the AI only to **Fix** them or find deeper Logic/Security issues that linters miss.

### 📏 Review Standards (The "Code Guardian" Protocol)
The bot enforces a strict "Clean Code" policy based on **SonarWay** and **OWASP** standards:

| Category | Specific Checks & Metrics |
| :--- | :--- |
| **Security 🔴** | • **OWASP Top 10** (SQL Injection, XSS, CSRF)<br>• Hardcoded Secrets (API Keys, Tokens)<br>• PII Leaks (Email/Phone exposure) |
| **Reliability 🟠** | • **Cognitive Complexity**: Flags methods with complexity rating > 15.<br>• **N+1 Queries**: Detects database calls inside loops.<br>• **Resource Leaks**: Unclosed streams/connections. |
| **Maintainability 🟡** | • **Hard Metrics**: Nesting Depth > 4, Function Params > 7.<br>• **DRY Principle**: Detects copy-pasted code blocks (Junk Code).<br>• **SOLID**: Flags God Classes or tight coupling. |

---

## 🚀 Integration

Deploy Neural Nexus as a standard GitHub Action. Add the following to `.github/workflows/review.yml`:

```yaml
name: Neural Nexus Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      statuses: write
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Execute Neural Nexus
        uses: brandoptics/brandOptics_ai_review_bot_action@v3
        with:
          openai_key: ${{ secrets.OPENAI_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

> **Note**: We recommend pinning to the major version (`@v3`) to receive non-breaking updates automatically. For strict stability, use a specific tag (`@v3.5.0`) or SHA.

### Required Secrets
Navigate to **Settings → Secrets → Actions** and add:
- `OPENAI_API_KEY`: A valid OpenAI API key with GPT-4o access.

---

## ⚙️ Configuration Guides

Neural Nexus works out-of-the-box, but for enterprise environments, precise configuration is key. Below are elaborate guides for supported ecosystems.

### 1. Flutter & Dart (Mobile)
For production Flutter apps, you often need to handle private packages and strict linting rules.

**Workflow Setup (`.github/workflows/review.yml`):**
```yaml
steps:
  - name: Checkout Source
    uses: actions/checkout@v4

  # Optional: Authenticate for private pub packages
  - name: Setup Private Packages
    run: |
      git config --global url."https://${{ secrets.PAT }}@github.com/".insteadOf "https://github.com/"

  - name: Run Neural Nexus
    uses: brandoptics/brandOptics_ai_review_bot_action@v3
    with:
      openai_key: ${{ secrets.OPENAI_API_KEY }}
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

**Linting Rules (`analysis_options.yaml`):**
Place this file in your project root to enforce rules that Neural Nexus will respect and automatically fix.
```yaml
include: package:flutter_lints/flutter.yaml

linter:
  rules:
    # --- ERROR RESILIENCE ---
    avoid_print: true
    empty_catches: true
    use_build_context_synchronously: true
    always_declare_return_types: true
    cancel_subscriptions: true
    close_sinks: true
    control_flow_in_finally: true
    no_duplicate_case_values: true
    unrelated_type_equality_checks: true
    
    # --- STYLE & READABILITY ---
    prefer_const_constructors: true
    prefer_final_locals: true
    prefer_final_parameters: true
    always_specify_types: true
    camel_case_types: true
    camel_case_extensions: true
    file_names: true
    
    # --- ARCHITECTURE ---
    await_only_futures: true
    unnecessary_await_in_return: true
    avoid_void_async: true
    prefer_expression_function_bodies: true
    
    # --- PUBSPEC CHECKS ---
    sort_pub_dependencies: true
    package_names: true
```

---

### 2. React & TypeScript (Web)
Ensure your `eslint.config.js` (or `.eslintrc`) is present so Neural Nexus can detect your specific style guide (Airbnb, Standard, etc.).

**Recommended `eslint.config.js`:**
```javascript
import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import tseslint from 'typescript-eslint';

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      react,
      'react-hooks': reactHooks,
      'jsx-a11y': jsxA11y
    },
    languageOptions: {
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
      }
    },
    rules: {
      // --- REACT HOOKS (CRITICAL) ---
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      
      // --- BEST PRACTICES ---
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'prefer-const': 'error',
      'no-var': 'error',
      'eqeqeq': 'error',
      'no-unused-vars': 'off', // Handled by TS
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/explicit-function-return-type': 'warn',
      
      // --- ACCESSIBILITY ---
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/anchor-has-content': 'error',
      'jsx-a11y/aria-props': 'error',
      
      // --- REACT IDIOMS ---
      'react/jsx-boolean-value': 'error',
      'react/self-closing-comp': 'error',
      'react/jsx-key': 'error'
    },
  },
];
```

---

### 3. Node.js (Backend)
For Express, NestJS, or raw Node.js services, enforce secure coding practices.

**Minimal `eslint.config.js`:**
```javascript
module.exports = [
  js.configs.recommended,
  {
    files: ["**/*.js"],
    languageOptions: {
        ecmaVersion: 2022,
        sourceType: "module"
    },
    rules: {
      // --- SECURITY & SAFETY ---
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      "no-caller": "error",
      "no-proto": "error",
      "no-iterator": "error",
      
      // --- BUG PREVENTION ---
      "eqeqeq": ["error", "always"],
      "no-return-await": "error",
      "require-await": "error",
      "array-callback-return": "error",
      "no-self-compare": "error",
      "no-template-curly-in-string": "error",
      "no-unmodified-loop-condition": "error",
      
      // --- STYLE & MAINTENANCE ---
      "camelcase": ["warn", { "properties": "never" }],
      "complexity": ["warn", 15],
      "max-depth": ["warn", 4],
      "max-params": ["warn", 5],
      "no-shadow": "warn"
    }
  }
];
```

---

### 4. Python (Data & Backend)
Neural Nexus checks for PEP8 compliance and cognitive complexity.

**Required `.flake8` Config:**
Add this to your root to avoid linting virtualenvs or cache files.
```ini
[flake8]
# --- CORE SETTINGS ---
max-line-length = 100
max-complexity = 15
exclude = .git,__pycache__,docs/source/conf.py,old,build,dist,venv,env,migrations

# --- ERROR CODES TO IGNORE (Black Compatible) ---
# E203: Whitespace before ':'
# W503: Line break before binary operator
ignore = E203, W503

# --- ENFORCEMENT ---
# C901: Function verification complexity
# F401: Module imported but unused
select = C,E,F,W,B,B950
```

---

### 5. SQL (Database)
Ensure your queries remain optimized and readable across dialects (Postgres, MySQL, BigQuery).

**Required `.sqlfluff` Config:**
```ini
[sqlfluff]
dialect = postgres
templater = raw
# Exclude dbt packages/macros content
exclude_rules = L009

[sqlfluff:indentation]
indent_unit = space
tab_space_size = 4

[sqlfluff:rules]
max_line_length = 80
allow_scalar = True
single_table_references = consistent
unquoted_identifiers_policy = all

[sqlfluff:rules:L010]
# Keywords Uppercase
capitalisation_policy = upper

[sqlfluff:rules:L014]
# Unquoted identifiers Lowercase
extended_capitalisation_policy = lower
```

---

### 6. .NET / C#
For Enterprise C# applications, we use `dotnet format`.

**Required `root.editorconfig`:**
Standardize your C# formatting rules.
```ini
root = true

[*.cs]
# --- INDENTATION ---
indent_style = space
indent_size = 4

# --- NEWLINES ---
end_of_line = lf
insert_final_newline = true
new_line_before_open_brace = all

# --- LANGUAGE RULES ---
# Prefer 'var' only when obvious
csharp_style_var_for_built_in_types = false:warning
csharp_style_var_when_type_is_apparent = true:warning
csharp_style_var_elsewhere = false:warning

# --- EXPRESSION BODIES ---
csharp_style_expression_bodied_methods = when_on_single_line:suggestion
csharp_style_expression_bodied_properties = true:suggestion

# --- PATTERN MATCHING ---
csharp_style_pattern_matching_over_is_with_cast_check = true:suggestion
csharp_style_pattern_matching_over_as_with_null_check = true:suggestion
```

---

<div align="center">
  <sub><b>BrandOptics Engineering</b> • <i>Building the future of automated software assurance.</i></sub>
</div>
