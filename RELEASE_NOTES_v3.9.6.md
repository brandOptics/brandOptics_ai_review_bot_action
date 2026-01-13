# Release v3.9.6: Azure Foundry & Enterprise Scale

### ☁️ Native Azure OpenAI Support
Neural Nexus now includes a first-class integration with **Azure OpenAI Service** (Azure Foundry). This allows Enterprise teams to leverage their secure, compliant Azure infrastructure directly.

- **Seamless Switching**: Simply setting `openai_api_type: "azure"` automatically reconfigures the internal engine to use `AzureOpenAI` headers and authentication protocols.
- **Enhanced Configuration**: Full support for `openai_api_version` ensures compatibility with the latest API previews (e.g., `2025-01-01-preview`).

### 🛡️ Critical Failure Reporting
We have improved visibility into system health.
- **Immediate Alerts**: If the AI API fails (due to Keys, Rate Limiting, or Firewall), the bot now posts a **Critical System Notice** prominently in the PR comment, ensuring developers aren't left guessing why the review is empty.
- **Debug Trace**: Console logs now output initializing connection types for easier troubleshooting in GitHub Actions logs.

### ⚙️ How to Upgrade
```yaml
- uses: brandoptics/brandOptics_ai_review_bot_action@v3
  with:
    openai_key: ${{ secrets.AZURE_API_KEY }}
    openai_base_url: "https://your-org.openai.azure.com"
    openai_model: "gpt-4o"
    openai_api_type: "azure"           # [NEW]
    openai_api_version: "2024-02-15-preview" # [NEW]
```
