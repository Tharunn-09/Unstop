# 🚀 Unstop Problem of the Day (POTD) Automated Bot

An automated Python bot that fetches the daily Problem of the Day from [Unstop](https://unstop.com), generates optimal Python 3 solutions using Google Gemini AI, and submits them automatically.

Runs automatically every morning at **9:30 AM IST (04:00 UTC)** via GitHub Actions or triggered on-demand via the GitHub REST API.

---

## 📋 Features

- ⚡ **Automated Daily Solving**: Solves daily coding problems hands-free.
- 🧠 **AI-Powered Solver**: Uses Google Gemini API with competitive programming prompt tuning (fast I/O, optimal $O(N)$ time complexity, recursion depth handling).
- 🔄 **Self-Correction & Refinement**: Re-evaluates and refines code if initial submission detects sample testcase errors.
- 🕒 **GitHub Actions & API Trigger**: Scheduled to run daily at 9:30 AM IST; also triggerable via external schedulers (e.g. cron-job.org, AWS EventBridge, webhooks).
- 🔒 **Secure**: Zero hardcoded secrets; utilizes GitHub Repository Secrets and `.env` files.

---

## 🛠️ Authentication & Setup

### 1. Extract Your Unstop Cookies (Takes 30 seconds)
1. Open your browser and log in to [unstop.com](https://unstop.com).
2. Go to the [Unstop Practice / POTD](https://unstop.com/practice/potd) page.
3. Open Chrome / Edge Developer Tools by pressing **`F12`** (or Right-Click $\rightarrow$ **Inspect**).
4. Go to the **Network** tab, check the **Fetch/XHR** filter, and refresh the page (`F5`).
5. Click on any network request sent to `unstop.com` (e.g. `potd`, `user`, or `profile`).
6. Scroll down to **Request Headers**, find **`Cookie`**, and copy the entire cookie string (e.g., `d2c_session=...; XSRF-TOKEN=...; remember_web_...=...`).
7. Paste this into your `.env` as `UNSTOP_COOKIES` (or as a GitHub Secret).

*The bot automatically parses all session keys, authentication cookies, and extracts `XSRF-TOKEN` / `CSRF` headers for secure submissions.*

---

### 2. Google Gemini API Key (Free)
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Click **Get API Key** and create an API key.
3. Save this as `GEMINI_API_KEY`.

---

## 💻 Local Testing & Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd <repo-folder>
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure `.env`**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Fill in your `GEMINI_API_KEY` and `UNSTOP_AUTH_TOKEN` / `UNSTOP_COOKIE`.

4. **Test run**:
   - **Dry Run (test AI solver & parsing without submitting)**:
     Set `RUN_MODE=dry-run` in `.env` and run:
     ```bash
     python main.py
     ```
   - **Live Run (fetches, solves, and submits to Unstop)**:
     Set `RUN_MODE=live` in `.env` and run:
     ```bash
     python main.py
     ```

---

## ⚙️ GitHub Actions Automation

### 1. Configure Repository Secrets
Push your code to a private GitHub repository, then navigate to:
**Repository Settings -> Secrets and variables -> Actions -> New repository secret**

Add the following secrets:

| Secret Name | Description | Required |
|---|---|---|
| `UNSTOP_COOKIES` | Full cookie string from your logged-in Unstop session | **Yes** |
| `GEMINI_API_KEY` | Your Google Gemini API Key | **Yes** |
| `GEMINI_MODEL` | `gemini-1.5-flash` (or `gemini-2.0-flash`) | Optional |
| `RUN_MODE` | `live` (default) or `dry-run` | Optional |

---

## 🌐 External Cron Scheduler Setup (GitHub API)

You can trigger the workflow anytime using an external cron scheduler (e.g., [cron-job.org](https://cron-job.org), AWS EventBridge, Cloudflare Workers, or FastCron):

### 1. Create a GitHub Personal Access Token (PAT)
1. Go to **GitHub Settings $\rightarrow$ Developer Settings $\rightarrow$ Personal Access Tokens $\rightarrow$ Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Name it `Unstop BOT Trigger` and check the **`repo`** (or **`workflow`**) scope.
4. Copy your token (starts with `ghp_...`).

---

### 2. Configure Your External Cron Job
Set up an HTTP **POST** request in your cron scheduler:

- **HTTP Method**: `POST`
- **URL**:
  ```text
  https://api.github.com/repos/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>/actions/workflows/daily_potd.yml/dispatches
  ```
- **Headers**:
  ```http
  Accept: application/vnd.github+json
  Authorization: Bearer <YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>
  X-GitHub-Api-Version: 2022-11-28
  Content-Type: application/json
  User-Agent: Cron-Scheduler
  ```
- **Body (JSON)**:
  ```json
  {
    "ref": "main",
    "inputs": {
      "question_id": "potd",
      "run_mode": "live"
    }
  }
  ```

---

### 3. Test with cURL (Terminal)
```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \

---

## 📁 Project Structure

```
.
## 🎯 How to Use

### 1. Run Today's Official POTD (Default)
```bash
python main.py
```
*(Automatically discovers the official Unstop POTD, solves with Dual-AI, submits, and sends the email report!)*

---

### 2. Solve Any Practice Question (by URL or Question ID)
You can solve **any question** on Unstop simply by passing its URL or ID as an argument:

```bash
# By Question ID:
python main.py 250146

# By Unstop Practice URL:
python main.py https://unstop.com/code/practice/250146
```

---

### 3. Run in Dry-Run Mode (Test without submitting)
In your `.env` file, set:
```ini
RUN_MODE=dry-run
```
Or run:
```bash
python main.py --dry-run
```

---

## 📂 Project Structure

```text
├── .github/
│   └── workflows/
│       └── daily_potd.yml     # Automated workflow at 9:30 AM IST + Manual Dispatch
├── src/
│   ├── __init__.py
│   ├── config.py              # Environment and configuration settings
│   ├── cleaner.py             # Pure Python code cleaner (Zero comments/docstrings)
│   ├── evaluator.py           # Local testcase runner & Dual-AI benchmark engine
│   ├── groq_solver.py         # Groq AI solver (Qwen / LLaMA)
│   ├── solver.py              # Google Gemini AI solver
│   ├── notifier.py            # Resend HTML email dispatcher
│   ├── logger.py              # Clean formatted console logger
│   └── unstop_client.py       # Unstop API client & Dynamic POTD discovery
├── main.py                    # Main pipeline orchestrator
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Excludes credentials and cache files
└── README.md                  # Documentation
```

---

## ⚖️ Disclaimer
This project is for educational and personal practice tracking purposes. Please adhere to Unstop's terms of service and community guidelines.
