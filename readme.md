![brandOptics Logo](https://raw.githubusercontent.com/brandOptics/brandOptics_ai_review_bot_action/main/.github/assets/bailogo.png)

# brandOptics AI Neural Nexus Code Review

The **brandOptics AI Neural Nexus** GitHub Action delivers automated, AI-assisted code reviews across multiple programming languages. It supports advanced linting for Flutter and React, with Angular and .NET support actively in development.

---

## 🔖 Current Version

**v3.0.7** – Full support for Flutter & React. Angular and .NET support is in progress.

---

## 📚 Table of Contents

1. [Usage in CI/CD](#usage-in-cicd)
2. [Flutter Setup](#flutter-setup)
3. [React Setup](#react-setup)
4. [React Setup](#react-setup)
5. [Secrets Configuration](#secrets-configuration)
6. [Supported Languages](#supported-languages)
7. [Roadmap](#roadmap)

---

## 🚀 Usage in CI/CD

Create `.github/workflows/ci.yml` in your project repository:

```yaml
title: brandOptics AI Neural Nexus Code Review

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
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run brandOptics AI review
        uses: brandoptics/brandOptics_ai_review_bot_action@v3.1.3
        with:
          openai_key:   ${{ secrets.OPENAI_API_KEY }} # Need to add this as a repository secrets with the name "OPENAI_API_KEY"
          github_token: ${{ secrets.GITHUB_TOKEN }}  # Automatically provided
```

---

## 🧪 Flutter Setup

Add the following `analysis_options.yaml` file to the root of your Flutter project (next to `pubspec.yaml`).

```yaml
include: package:flutter_lints/flutter.yaml

linter:
  rules:
    # Optional additional lint rules
    always_declare_return_types: true
    always_put_control_body_on_new_line: true
    always_put_required_named_parameters_first: true
    always_require_non_null_named_parameters: true
    always_specify_types: true

    camel_case_extensions: true
    camel_case_types: true
    constant_identifier_names: true
    non_constant_identifier_names: true
    file_names: true
    library_prefixes: true
    package_names: true
    package_prefixed_library_names: true

    avoid_annotating_with_dynamic: true
    avoid_bool_literals_in_conditional_expressions: true
    avoid_catches_without_on_clauses: true
    avoid_catching_errors: true
    avoid_empty_else: true
    avoid_field_initializers_in_const_classes: true
    avoid_function_literals_in_foreach_calls: true
    avoid_init_to_null: true
    avoid_multiple_declarations_per_line: true
    avoid_null_checks_in_equality_operators: true
    avoid_positional_boolean_parameters: true
    avoid_print: true
    avoid_private_typedef_functions: true
    avoid_redundant_argument_values: true
    avoid_returning_this: true
    avoid_setters_without_getters: true
    avoid_shadowing_type_parameters: true
    avoid_single_cascade_in_expression_statements: true
    avoid_slow_async_io: true
    avoid_type_to_string: true
    avoid_types_as_parameter_names: true
    avoid_unnecessary_containers: true
    avoid_unused_constructor_parameters: true

    await_only_futures: true
    cancel_subscriptions: true
    cast_nullable_to_non_nullable: true
    close_sinks: true
    collection_methods_unrelated_type: true
    combinators_ordering: true
    comment_references: true
    conditional_uri_does_not_exist: true
    control_flow_in_finally: true
    curly_braces_in_flow_control_structures: true
    deprecated_consistency: true
    empty_catches: true
    empty_constructor_bodies: true
    empty_statements: true
    exhaustive_cases: true
    implicit_call_tearoffs: true
    implicit_reopen: true
    invalid_case_patterns: true
    join_return_with_assignment: true
    leading_newlines_in_multiline_strings: true
    no_logic_in_create_state: true
    no_runtimeType_toString: true
    null_check_on_nullable_type_parameter: true
    null_closures: true
    omit_local_variable_types: false

    only_throw_errors: true
    overridden_fields: true
    parameter_assignments: true
    use_build_context_synchronously: true
    use_function_type_syntax_for_parameters: true
    use_to_and_as_if_applicable: true
    valid_regexps: true
    void_checks: true

    prefer_adjacent_string_concatenation: true
    prefer_asserts_in_initializer_lists: true
    prefer_asserts_with_message: true
    prefer_collection_literals: true
    prefer_conditional_assignment: true
    prefer_const_constructors: true
    prefer_const_constructors_in_immutables: true
    prefer_const_declarations: true
    prefer_const_literals_to_create_immutables: true
    prefer_constructors_over_static_methods: true
    prefer_contains: true
    prefer_double_quotes: true
    prefer_equal_for_default_values: true
    prefer_expression_function_bodies: true
    prefer_final_fields: true
    prefer_final_in_for_each: true
    prefer_final_locals: true
    prefer_final_parameters: true
    prefer_for_elements_to_map_fromIterable: true
    prefer_foreach: true
    prefer_function_declarations_over_variables: true
    prefer_generic_function_type_aliases: true
    prefer_if_elements_to_conditional_expressions: true
    prefer_if_null_operators: true
    prefer_initializing_formals: true
    prefer_inlined_adds: true
    prefer_int_literals: true
    prefer_interpolation_to_compose_strings: true
    prefer_is_empty: true
    prefer_is_not_empty: true
    prefer_is_not_operator: true
    prefer_iterable_whereType: true
    prefer_mixin: true
    prefer_null_aware_method_calls: true
    prefer_null_aware_operators: true
    prefer_relative_imports: true

    provide_deprecation_message: true
    recursive_getters: true
    require_trailing_commas: true
    slash_for_doc_comments: true
    sort_child_properties_last: true
    sort_constructors_first: true
    sort_unnamed_constructors_first: true
    test_types_in_equals: true
    throw_in_finally: true
    tighten_type_of_initializing_formals: true
    type_annotate_public_apis: true
    type_init_formals: true
    unawaited_futures: true

    unnecessary_await_in_return: true
    unnecessary_brace_in_string_interps: true
    unnecessary_const: true
    unnecessary_constructor_name: true
    unnecessary_getters_setters: true
    unnecessary_lambdas: true
    unnecessary_library_directive: true
    unnecessary_new: true
    unnecessary_null_aware_assignments: true
    unnecessary_null_in_if_null_operators: true
    unnecessary_nullable_for_final_variable_declarations: true
    unnecessary_overrides: true
    unnecessary_parenthesis: true
    unnecessary_raw_strings: true
    unnecessary_statements: true
    unnecessary_string_escapes: true
    unnecessary_string_interpolations: true
    unnecessary_this: true
    unnecessary_to_list_in_spreads: true
    unrelated_type_equality_checks: true
```

> 💡 **Note:** You may comment out rules that aren't applicable to your project.

---

## ⚛️ React Setup

Create `eslint.config.js` at your project root:

```js
import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import importPlugin from 'eslint-plugin-import';
import sonarjs from 'eslint-plugin-sonarjs';
import babelParser from '@babel/eslint-parser';

export default [
  { ignores: ['dist', 'build', 'node_modules'] },
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      parser: babelParser,
      globals: globals.browser,
      parserOptions: {
        requireConfigFile: false,
        errorRecovery: true,
        babelOptions: { presets: ['@babel/preset-react'] },
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'jsx-a11y': jsxA11y,
      import: importPlugin,
      sonarjs,
    },
    settings: {
      react: { version: 'detect' },
    },
    rules: {
      ...js.configs.recommended.rules,
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...reactRefresh.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      ...importPlugin.configs.recommended.rules,
      ...sonarjs.configs.recommended.rules,
      'no-undef': 'error',
      'no-unused-vars': ['error', { args: 'after-used', argsIgnorePattern: '^_', varsIgnorePattern: '^[A-Z_]' }],
      'eqeqeq': ['error', 'always'],
      'no-console': 'warn',
      'no-debugger': 'error',
      'no-var': 'error',
      'prefer-const': 'error',
    },
  },
];
```

---




> 💡 **Note:** You may comment out rules that aren't applicable to your project.

---

## 🟩 Node Setup

Create `eslint.config.js` at your project root:

```js
// eslint.config.cjs
const js = require("@eslint/js");
const globals = require("globals");
const importPlugin = require("eslint-plugin-import");
const sonarjs = require("eslint-plugin-sonarjs");
const n = require("eslint-plugin-n");

module.exports = [
  { ignores: ["dist", "build", "node_modules"] },

  // avoid false positives for the config file itself
  {
    files: [
      "eslint.config.cjs",
      "eslint.config.js",
      ".eslintrc.cjs",
      ".eslintrc.js",
    ],
    rules: {
      "n/no-unpublished-import": "off",
      "n/no-unpublished-require": "off",
    },
  },

  {
    files: ["**/*.{js,cjs,mjs,ts}"],
    languageOptions: {
      globals: {
        ...globals.node,
      },
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    plugins: {
      import: importPlugin,
      sonarjs,
      n,
    },
    settings: {
      // Make import plugin resolve Node modules cleanly
      "import/resolver": {
        node: { extensions: [".js", ".cjs", ".mjs", ".ts", ".json"] },
      },
    },
    rules: {
      // Core ESLint
      ...js.configs.recommended.rules,

      // Node plugin (flat config)
      ...n.configs["flat/recommended"].rules,

      // Import
      ...importPlugin.configs.recommended.rules,

      // SonarJS
      ...sonarjs.configs.recommended.rules,

      // Your custom overrides
      "no-undef": "error",
      "no-unused-vars": [
        "error",
        {
          args: "after-used",
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^[A-Z_]",
        },
      ],
      eqeqeq: ["error", "always"],
      "no-console": "warn",
      "no-debugger": "error",
      "no-var": "error",
      "prefer-const": "error",

      // A few handy Node-centric tweaks (optional)
      "n/no-missing-import": "error",
      "n/no-unsupported-features/es-builtins": "off", // if you target modern Node
      "n/no-unsupported-features/node-builtins": "off",
    },
  },
];

```

---

## 🔐 Secrets Configuration

### ✅ Required: `OPENAI_API_KEY`

#### To set:

1. Navigate to your GitHub repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `OPENAI_API_KEY`
5. Value: Your OpenAI secret key

✅ `GITHUB_TOKEN` is auto-injected by GitHub.

---

## 🧠 Supported Languages

| Language | Status           |
| -------- | ---------------- |
| Flutter  | ✅ Stable         |
| React    | ✅ Stable         |
| Angular  | 🚧 In Progress   |
| .NET     | 🚧 In Progress   |
| Python   | ✅ Basic (Flake8) |
| Node   | ✅ Stable|

---

## 🛣️ Roadmap

* ✅ Improve feedback formatting
* 🚧 Angular support (TypeScript / HTML)
* 🚧 .NET C# support
* 🚧 Markdown and stylelint integration

---

> Made with ❤️ by the brandOptics AI R\&D team
