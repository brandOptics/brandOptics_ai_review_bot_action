# Release v3.9.5: Custom AI Gateways & Model Freedom

### 🚀 Major Feature: Enterprise & Custom Model Support
Neural Nexus now breaks free from the default OpenAI constraints. This release introduces full support for **Custom OpenAI Base URLs** and **Flexible Model Selection**.

- **Enterprise Proxy Support**: Use Neural Nexus behind your corporate firewall or API gateway using `openai_base_url`.
- **Local & Alternative LLMs**: Connect to any OpenAI-compatible endpoint (e.g., LocalAI, vLLM, DeepSeek) by simply pointing the URL and specifying the model name.
- **Global Model Consistency**: The configured model is now enforced across **ALL** bot interactions (Code Analysis, Fixer Mode, Ratings, and "Troll" comments).

### ⚙️ How to Configure
Update your `.github/workflows/review.yml`:

```yaml
- uses: brandoptics/brandOptics_ai_review_bot_action@v3
  with:
    openai_key: ${{ secrets.OPENAI_KEY }}
    # [NEW] Connect to your custom endpoint
    openai_base_url: "https://api.your-enterprise.com/v1"
    # [NEW] Use any compatible model
    openai_model: "deepseek-coder-v2"
```

### 🛠️ Improvements
- **Global Variable Refactor**: The internal Python engine (`bobot_review.py`) has been refactored to ensure the selected model `MODEL_NAME` is used in every single API call, eliminating hardcoded fallbacks to `gpt-4o`.
