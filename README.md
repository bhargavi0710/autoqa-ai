# AutoQA AI 🤖

> AI-powered automated QA tool that crawls websites, generates test cases, executes them, and produces professional bug reports — automatically.

## Demo

> 🎥 (Add a screen recording GIF here — record your terminal running the tool)

## Features

- **Automated Site Crawling** — Selenium-powered crawler discovers pages, forms, links, and load times across your site
- **Functional Testing** — Empty submission, invalid email, SQL injection, XSS, long text overflow, and special character tests on every form
- **Link Validation** — HTTP status checks for all discovered links (404, 5xx, redirects)
- **Performance Testing** — Page load time thresholds with PASS/WARNING/FAIL ratings
- **Security Header Analysis** — Checks X-Frame-Options, CSP, X-Content-Type-Options, and HSTS
- **Accessibility Testing** — axe-core integration for WCAG violation detection
- **AI Bug Reports** — Google Gemini enhances failed tests with summaries, fixes, and business impact
- **Executive Summary** — AI-generated 3-paragraph summary for non-technical stakeholders
- **HTML Dashboard** — Professional dark-navy report with Chart.js charts, filters, and expandable failure details
- **Screenshot Capture** — Automatic screenshots on every failed test
- **CSV & JSON Export** — Structured data export for integration with other tools
- **Retest Mode** — Re-run only previously failed tests from a JSON report
- **CLI Interface** — Full argparse CLI with colored terminal output and live progress
- **Flask Web App** — Browser-based interface for cloud deployment
- **CI/CD Pipeline** — GitHub Actions runs unit tests, linting, and demo scans
- **Railway Deployment** — One-click deploy to Railway.app free tier

## Architecture

```
URL Input → Crawler → Tester → AI Analyzer → Reporter → HTML Dashboard
              ↓           ↓           ↓
           PageData   TestResult   Gemini API
                                      (Free Tier)
```

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/autoqa-ai.git
cd autoqa-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your FREE Gemini API key from https://aistudio.google.com

# 5. Run your first scan
python main.py --url https://books.toscrape.com --headless

# 6. Open the HTML report
# Report saved to ./reports/report_YYYYMMDD_HHMMSS.html
```

## CLI Reference

| Flag | Description | Default |
|------|-------------|---------|
| `--url` | Target website URL (required) | — |
| `--headless` / `--no-headless` | Run browser in headless mode | `True` |
| `--browser` | Browser engine: `chrome` or `firefox` | `chrome` |
| `--retest` | Path to previous JSON report to re-run failed tests | — |
| `--export-csv` | Export results to CSV after run | `False` |
| `--no-ai` | Skip Gemini AI calls (offline mode) | `False` |
| `--output-dir` | Directory for reports and screenshots | `./reports` |

## Test Categories

| Category | What It Tests | Example Finding |
|----------|---------------|-----------------|
| Functional | Form validation, injection, XSS, input handling | SQL injection payload caused database error |
| Link | HTTP status of all discovered links | Link returned HTTP 404 Not Found |
| Performance | Page load time vs thresholds | Page load time 3500ms exceeds 3000ms limit |
| Security | HTTP security headers | Missing Content-Security-Policy header |
| Accessibility | WCAG violations via axe-core | Missing alt text on images (Critical) |

## Zero Cost Setup

- **Gemini API**: Free at [aistudio.google.com](https://aistudio.google.com) (1500 requests/day)
- **GitHub Actions**: Free for public repos
- **Railway.app**: Free tier available

## Deploying to Railway (Free)

1. Push this repo to GitHub (see git commands below)
2. Go to [railway.app](https://railway.app) and log in with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your `autoqa-ai` repository
5. Go to the **Variables** tab and add:
   - `GEMINI_API_KEY` = your key from aistudio.google.com
6. Railway auto-deploys using the `Procfile` and `railway.toml` config
7. Copy the public URL from the **Settings** tab
8. Share the URL — anyone can test any website for free

## Tech Stack

| Tool | Purpose | Cost |
|------|---------|------|
| Python 3.11+ | Core language | Free |
| Selenium 4 | Browser automation | Free |
| axe-core | Accessibility testing | Free |
| Google Gemini | AI bug report enhancement | Free tier |
| Jinja2 | HTML report templating | Free |
| Chart.js | Report charts | Free |
| Flask + Gunicorn | Web app wrapper | Free |
| GitHub Actions | CI/CD pipeline | Free |
| Railway.app | Cloud deployment | Free tier |

## Author

Built as an SDET portfolio project demonstrating automated testing, AI-powered analysis, and CI/CD integration.
