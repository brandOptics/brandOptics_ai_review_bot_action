# Instructions & Coding Standards (Agent Protocol)

All agents working on this repository MUST adhere to these strict guidelines. Failure to comply results in broken builds and rejected PRs.

## 1. File & Project Structure
- **Absolute Paths**: Always use absolute paths when reading or writing files.
- **No Orphan Checkouts**: When exploring, always start by listing the root directory to locate the correct workspace.
- **Manifest First**: Always read `action.yml`, `package.json`, or `requirements.txt` first to understand dependencies.

## 2. Code Modification Protocol
1.  **Read Before Write**: NEVER edit a file you haven't read in the current session.
2.  **Atomic Edits**: Use `replace_file_content` for single blocks. Use `multi_replace_file_content` ONLY for scattered edits.
3.  **Contextual Anchors**: When replacing code, ensure your `TargetContent` includes enough unique context (surrounding lines) to prevent ambiguous matches.
4.  **No Placeholders**: NEVER leave comments like `// ... rest of code`. You must write the FULL and COMPLETE functional code.

## 3. Python Standards (Scripts)
- **Type Hints**: Use Python type hinting (`def foo(bar: str) -> int:`) where possible.
- **Error Handling**: No bare `except:`. Catch specific exceptions (`except Exception as e:` is acceptable for top-level catches).
- **Environment Vars**: Always use `os.getenv('VAR', 'default')` for configuration. Never hardcode credentials.
- **Imports**: Group imports: Standard Library, Third Party, Local.

## 4. Documentation Standards
- **Markdown**: Use GFM (GitHub Flavored Markdown).
- **Artifacts**: Store planning docs in the brain directory (`<appDataDir>/brain/<uuid>`).
- **Updates**: When changing code, YOU MUST update the corresponding `readme.md` or documentation.

## 5. Agentic Workflow
1.  **Plan**: Create `implementation_plan.md`.
2.  **Review**: Ask user for confirmation.
3.  **Execute**: Implement changes.
4.  **Verify**: Run a verification script or test to prove it works.
