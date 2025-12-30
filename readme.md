<div align="center">
  <img src="https://raw.githubusercontent.com/brandOptics/brandOptics_ai_review_bot_action/main/.github/assets/bailogo.png" height="120" />
  <h1>BrandOptics Neural Nexus</h1>
  <h3>Enterprise-Grade AI Code Review Agent</h3>

  <p>
    <a href="#-key-features">Key Features</a> •
    <a href="#-visual-showcase">Visual Showcase</a> •
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-configuration-guides">Configuration Guides</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Version-v3.5.0-success?style=for-the-badge" />
    <img src="https://img.shields.io/badge/AI-GPT--4o-blue?style=for-the-badge" />
    <img src="https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge" />
  </p>
</div>

---

## 🧠 What is Neural Nexus?
**Neural Nexus** is not just another wrapper around ChatGPT. It is a **Hybrid Intelligent System** that combines the **mathematical precision** of industry-standard linters (ESLint, SQLFluff, Flake8) with the **reasoning capabilities** of Large Language Models (GPT-4o).

It acts as your **Senior Code Architect**, providing:
1.  **Smart Quality Gates:** Fails builds on **Security Risks** & **Critical Bugs**, but only warns on stylistic issues.
2.  **Executive Dashboard:** A stunning, branded GitHub comment summary (Badges, Ratings, Collapsible Details).
3.  **Educational Insights:** Doesn't just fix code; explains *why* the fix matters (e.g., OWASP vulnerabilities, O(n) complexity).

---

## 📸 Visual Showcase
The bot posts a **"Neural Nexus Dashboard"** on every Pull Request.

<details>
<summary><b>👀 Click to view output preview</b></summary>

### ⭐⭐⭐ Code Janitor
*"A busy day at the office! Let's polish this diamond."*

| Author | Files | Security | Quality |
| :---: | :---: | :---: | :---: |
| @dev | 12 | 🔴 Critical | 🟡 Warnings |

#### 🚨 Critical Focus
> **🔴 Hardcoded AWS Secret** in `backend/config.py`
> **Analysis:** Detected a potential AWS Secret Access Key. Violates OWASP A07.
> ```python
> # ✅ Fix:
> AWS_SECRET = os.getenv("AWS_SECRET_KEY")
> ```

#### 📂 File-by-File Analysis
...
</details>

---

## 🚀 Quick Start
Add this workflow to your repository at `.github/workflows/review.yml`:

```yaml
name: "Neural Nexus AI Review"

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  statuses: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run Neural Nexus
        uses: brandoptics/brandOptics_ai_review_bot_action@v3.5.0
        with:
          openai_key: ${{ secrets.OPENAI_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

---

## ⚙️ Configuration Guides

### 1. Flutter Setup (Detailed)
For complex Flutter projects, use this setup to handle private packages and lint rules.

```yaml
steps:
  - name: Checkout code
    uses: actions/checkout@v4
    
  # Example: Clone private dependencies if needed
  - name: Clone eit_design_system_flutter
    shell: bash
    run: |
      git clone --depth 1 "https://x-access-token:${{ secrets.PAT }}@github.com/org/repo.git" "../packages/repo"

  - name: Run Neural Nexus
    uses: brandoptics/brandOptics_ai_review_bot_action@v3.5.0
    with:
      openai_key: ${{ secrets.OPENAI_API_KEY}}
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

#### Recommended `analysis_options.yaml`
Add this to your Flutter project root to enforce strict rules that the bot understands:

<details>
<summary><b>View full analysis_options.yaml</b></summary>

```yaml
include: package:flutter_lints/flutter.yaml
linter:
  rules:
    avoid_print: true
    prefer_const_constructors: true
    use_build_context_synchronously: true
    # ... (Add standard rules here)
```
</details>

---

### 2. React Setup
To ensure the bot picks up your React specific rules, create `eslint.config.js` at root:

```js
import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    plugins: { react, 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn'
    }
  }
];
```

---

### 3. Node.js Setup
For generic Node/Express apps, use this `eslint.config.js`:

```js
const js = require("@eslint/js");
module.exports = [
  js.configs.recommended,
  {
    rules: { "no-console": "warn", "no-unused-vars": "error" }
  }
];
```

---

## 🔑 Secrets Configuration

### Required: `OPENAI_API_KEY`
1. Navigate to your GitHub repository triggers.
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Create new secret: `OPENAI_API_KEY`
4. Value: Your OpenAI secret key (Request from Admin).

*Note: `GITHUB_TOKEN` is provided automatically by GitHub.*

---

## 🛠 Supported Languages & Roadmap

| Language | Engine | Status |
| :--- | :--- | :--- |
| **Python** | `Flake8` + `AI` | ✅ Stable |
| **JS / Node** | `ESLint` + `AI` | ✅ Stable |
| **React** | `ESLint Plugin React` + `AI` | ✅ Stable |
| **Vue.js** | `ESLint Plugin Vue` + `AI` | ✅ Stable |
| **Flutter** | `Dart Analyzer` + `AI` | ✅ Stable |
| **SQL** | `SQLFluff` + `AI` | ✅ Stable |
| **HTML/CSS** | `Stylelint` + `AI` | ✅ Stable |
| **.NET** | `dotnet-format` + `AI` | ✅ Stable |

**Roadmap:**
*   [ ] Dockerized Runtime for 10x Speed
*   [ ] Advanced Web Dashboard
*   [ ] Customizable `.bobot.yaml` config

---

> **By BrandOptics R&D** • *Empowering Developers with Intelligent Automation.*
