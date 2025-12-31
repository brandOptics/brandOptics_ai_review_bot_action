# 🤖 Setting Up a Custom BrandOptics Bot Identity

Follow this guide to make your PR comments appear from **"BrandOptics AI"** (with your custom logo) instead of the generic `github-actions[bot]`.

## Phase 1: Create the GitHub App

1.  Navigate to your GitHub Organization or Personal Settings.
    *   **Organization**: Settings -> Developer Settings -> GitHub Apps
    *   **Personal**: Settings -> Developer Settings -> GitHub Apps
2.  Click **"New GitHub App"**.
3.  **Register New App**:
    *   **GitHub App Name**: `BrandOptics AI` (This is the name that will appear on comments).
    *   **Homepage URL**: You can use your repo URL (e.g., `https://github.com/brandoptics/...`).
    *   **Callback URL**: (Ignore/Uncheck "Active").
    *   **Webhook**: Uncheck "Active".
4.  **Permissions**:
    Expand "Repository permissions" and set the following:
    *   **Contents**: `Read-only` (To read the code).
    *   **Pull Requests**: `Read and write` (To post comments).
    *   **Statuses**: `Read and write` (To set pass/fail checks).
    *   **Metadata**: `Read-only` (Default).
5.  **Subscribe to events**:
    *   Check `Pull request`.
6.  **Where can this installation be used?**:
    *   Select "Only on this account" (unless you plan to publish strictly for others to install).
7.  **Create GitHub App**.

## Phase 2: Branding & Keys

1.  **Upload Logo**:
    *   On the App settings page, scroll to "Display information".
    *   Upload your **BrandOptics Logo**. This will be the avatar for the bot.
2.  **Generate Private Key**:
    *   Scroll down to "Private keys".
    *   Click **"Generate a private key"**.
    *   A `.pem` file will download to your computer. **Keep this safe!**
3.  **Get App ID**:
    *   Scroll to the very top "About" section.
    *   Copy the **App ID** (an integer, e.g., `123456`).

## Phase 3: Install the App

1.  On the left sidebar of the App settings, click **"Install App"**.
2.  Click **"Install"** next to your account/organization.
3.  Select which repositories to install it on (or "All repositories").
4.  Click **"Install"**.

## Phase 4: Configure Repository Secrets

Go to the repository where you are running the Action (where `.github/workflows/review.yml` is).

1.  **Settings** -> **Secrets and variables** -> **Actions**.
2.  Click **"New repository secret"**.
3.  **Secret 1**:
    *   Name: `APP_ID`
    *   Value: Paste the App ID you copied earlier (e.g., `123456`).
4.  **Secret 2**:
    *   Name: `APP_PRIVATE_KEY`
    *   Value: Open the `.pem` file you downloaded in a text editor. Copy the **entire contents** (including `-----BEGIN RSA PRIVATE KEY-----`). Paste it here.

## Phase 5: Update Your Workflow

Finally, update your `.github/workflows/review.yml` to generate a token from this App and use it.

```yaml
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 1. Generate the Token using your new Secrets
      - name: Generate BrandOptics Token
        uses: actions/create-github-app-token@v1
        id: app-token
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      # 2. Pass the token to Neural Nexus
      - name: Run Neural Nexus
        uses: brandoptics/brandOptics_ai_review_bot_action@v3
        with:
          openai_key: ${{ secrets.OPENAI_API_KEY }}
          github_token: ${{ steps.app-token.outputs.token }} # <--- VITAL CHANGE
```

## 🎉 Verification

Next time you open a PR:
1.  The comment will come from **BrandOptics AI**.
2.  The Avatar will be your **custom logo**.
3.  The "Badge" on the comment will say **Bot** (but with your name).
