# QA AI Agent 🛡️
> **Autonomous Polyglot QA Test Suite Generator, Runner & Reporter**

An intelligent, autonomous QA AI Agent designed to integrate with **any software project** (Python, JavaScript/TypeScript, Go, Java, Rust, etc.). It analyzes your codebase architecture, extracts endpoints and business logic, generates complete **Unit, API, and End-to-End (E2E)** test suites into a dedicated folder (`tests/qa_agent/`), allows instant download of the project with tests, executes the tests in an isolated sandbox, and produces comprehensive interactive QA reports.

---

## 🌟 Key Features

- **🌐 Dual Interface:**
  - **Modern Web Dashboard**: Drag & drop `.zip` upload, interactive visual profiling, live terminal log streaming, and one-click download.
  - **Command-Line Interface (CLI)**: Run tests locally inside private codebases without uploading code.
- **🤖 GitHub Action CI/CD Integration:**
  - Automated test generation and execution on Git Push or Pull Requests.
  - Posts interactive test reports and pass/fail badges directly as PR comments!
- **🌍 True Polyglot Support:**
  - Auto-detects frameworks across **Python** (FastAPI, Flask, Django), **JavaScript / TypeScript** (Express, Next.js, React, Vitest, Jest), **Go**, **Java**, and more.
- **🧪 Multi-Tier Test Generation:**
  - **Unit Tests**: Edge cases, boundary inputs, null values, exceptions.
  - **API / Integration Tests**: Route status codes (200/201/400/404/422), payload schemas, mocked database/auth.
  - **E2E Tests**: Full lifecycle user journeys across operations.
- **⚡ LLM Brain (Gemini Flash Optimized):**
  - Uses `gemini-2.5-flash` / `gemini-3.8-flash` for high speed and ultra-low token consumption, allowing long sessions without hitting rate limits.
  - Includes smart fallback templates when running offline or without an API key.
- **📦 One-Click Download:**
  - Instantly download the complete project with generated tests packaged in a `.zip`.
- **🚀 Automated Test Execution (Sandbox):**
  - Safely executes tests in an isolated subprocess with timeouts and environment isolation.
  - Real-time streaming of stdout/stderr to the web console via WebSockets.
- **📊 Comprehensive Reports:**
  - Standalone, beautiful HTML reports and Markdown summaries with pass rates, execution metrics, and failure diagnostics.
- **☁️ Ready for Public Cloud Deployment:**
  - Pre-configured with production `Dockerfile`, `docker-compose.yml`, `Procfile`, and `render.yaml` for 1-click deployment on Render, Railway, or Fly.io.

---

## 📦 Installation & Setup

### Option 1: Install as a Global CLI via pip
```bash
git clone https://github.com/your-username/QA_Agent.git
cd QA_Agent
pip install -e .
```
Now you can run the agent anywhere on your system:
```bash
qa-agent --help
qa-agent-ui          # Launches the Web Dashboard
```

### Option 2: Run via Standard Python
```bash
pip install -r requirements.txt
python main.py       # Launches the Web Dashboard
```

### Option 3: Build a Standalone Executable (.exe)
```bash
python build_exe.py
# Standalone binary created at dist/qa-agent/qa-agent.exe
```

---

## 💻 Web Dashboard

To launch the web interface:

```bash
python main.py
# or: qa-agent-ui
```

This starts the server on `http://127.0.0.1:8000` and automatically opens your default browser.

### The 4-Step Web Flow:
1. **Ingest**: Upload a project `.zip` or type a local folder path.
2. **Profile**: View detected languages, frameworks, endpoints, and key functions.
3. **Generate**: Select test types (Unit, API, E2E) and click **"Generate Test Suites"**.
4. **Action**:
   - Click **"Download Project with Tests (.ZIP)"** to save your updated codebase.
   - Click **"Run Tests Automatically"** to watch the real-time test execution in the terminal window.
   - Click **"HTML Report"** or **"Markdown Report"** to export results.

---

## 🤖 GitHub Action CI/CD Integration

Run automated QA testing on every Pull Request or commit in your repositories!

### Add to your repository: `.github/workflows/qa_agent.yml`

```yaml
name: QA Agent CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

permissions:
  contents: write
  pull-requests: write

jobs:
  automated-qa:
    name: Autonomous QA Test Suite
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run QA AI Agent
        uses: your-username/QA_Agent@v1   # Or path to action.yml
        with:
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          test-types: 'unit,api,e2e'
          post-pr-comment: 'true'
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload Test Report Artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: qa-report
          path: tests/qa_agent/qa_report.*
```

---

## ⌨️ Command Line Interface (CLI)

### 1. Profile a Project
```bash
qa-agent analyze /path/to/project
```

### 2. Generate Tests
```bash
qa-agent generate /path/to/project --types unit,api,e2e
```

### 3. Run Generated Tests
```bash
qa-agent test /path/to/project --report
```

### 4. Full Pipeline (Analyze + Generate + Execute + Report)
```bash
qa-agent run /path/to/project
```

---

## 🌐 Deploy to the Public Web (Free Cloud Hosting)

You can deploy this website to the internet in 2 minutes so anyone can access it via a public URL:

### Option A: 1-Click Deploy on Render (Free)
1. Push this repository to your GitHub account.
2. Go to [Render.com](https://render.com) and click **New > Web Service**.
3. Select your GitHub repository.
4. Render will automatically detect `render.yaml` and configure:
   - **Build Command:** `pip install -r requirements.txt && pip install -e .`
   - **Start Command:** `uvicorn qa_agent.server.app:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**. Your app is live at `https://your-app-name.onrender.com`!

### Option B: Deploy on Railway (Free)
1. Go to [Railway.app](https://railway.app).
2. Click **New Project > Deploy from GitHub repo**.
3. Railway automatically detects the `Dockerfile` and `Procfile`.
4. Add environment variable `GEMINI_API_KEY` (optional).
5. Generate a public domain under Settings.

### Option C: Run with Docker / Docker Compose
```bash
docker compose up -d
```
Accessible at `http://localhost:8000`.

---

## 📂 Generated Structure Inside Target Projects

When QA Agent runs on a project, it creates clean, isolated test suites inside:

```text
your_project/
└── tests/
    └── qa_agent/
        ├── unit/           # Unit tests for functions and classes
        ├── api/            # API integration tests for endpoints
        ├── e2e/            # End-to-end user workflow tests
        ├── conftest.py     # Root test setup and sys.path resolution
        ├── test_summary.md # Quick breakdown of generated suites
        └── qa_report.md    # Automated execution report & metrics
```

---

## 🧪 Automated Self-Verification

Run the automated test suite to verify the agent's core components:

```bash
python -m pytest tests/ -v
```
All core tests will verify file analysis, test planning, file generation, isolated execution, and API endpoints.
