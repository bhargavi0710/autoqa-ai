<div align="center">

# AutoQA AI

**AI-powered automated QA testing tool that crawls any website, runs comprehensive tests, and generates professional bug reports — fully automated.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Selenium](https://img.shields.io/badge/Selenium-4.0-43B02A?style=flat-square&logo=selenium&logoColor=white)](https://selenium.dev)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Tests](https://img.shields.io/badge/Tests-17%2F19_passing-brightgreen?style=flat-square)](https://github.com/bhargavi0710/autoqa-ai/actions)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

[Features](#features) · [Architecture](#architecture) · [Quick Start](#quick-start) · [Screenshots](#screenshots) · [CLI Reference](#cli-reference)

</div>

---

## What is AutoQA AI?

AutoQA AI is a full-stack automated QA platform that replaces hours of manual website testing with a single command. Point it at any website and it will:

- Crawl every page automatically using Selenium
- Run 5 categories of tests — functional, performance, security, accessibility, and link validation
- Capture screenshots on every failure
- Use **Groq AI** to generate root-cause analysis, fix recommendations, and business impact for every bug
- Produce a professional HTML dashboard with charts, filters, and exportable data

Built as an SDET portfolio project demonstrating browser automation, AI integration, and production-grade Python engineering.

---

## Screenshots

### Web Interface
<table>
  <tr>
    <td><img src="screenshots/dashboard1.png" alt="AutoQA AI Homepage" width="400"/></td>
    <td><img src="screenshots/dashboard2.png" alt="Scan in Progress" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><em>Homepage — submit any URL</em></td>
    <td align="center"><em>Live progress bar during scan</em></td>
  </tr>
</table>

### Generated Reports
<table>
  <tr>
    <td><img src="screenshots/report1.png" alt="Report Dashboard" width="260"/></td>
    <td><img src="screenshots/report2.png" alt="Test Results" width="260"/></td>
    <td><img src="screenshots/report3.png" alt="AI Analysis" width="260"/></td>
  </tr>
  <tr>
    <td align="center"><em>Executive summary & KPIs</em></td>
    <td align="center"><em>Test results with severity</em></td>
    <td align="center"><em>AI root-cause analysis</em></td>
  </tr>
  <tr>
    <td><img src="screenshots/report4.png" alt="Security Checks" width="260"/></td>
    <td><img src="screenshots/report5.png" alt="Performance Results" width="260"/></td>
    <td><img src="screenshots/report6.png" alt="Accessibility Audit" width="260"/></td>
  </tr>
  <tr>
    <td align="center"><em>Security header analysis</em></td>
    <td align="center"><em>Performance benchmarks</em></td>
    <td align="center"><em>Accessibility audit</em></td>
  </tr>
  <tr>
    <td colspan="3" align="center"><img src="screenshots/report7.png" alt="Full Report" width="540"/></td>
  </tr>
  <tr>
    <td colspan="3" align="center"><em>Full report with Chart.js visualisations and expandable failure details</em></td>
  </tr>
</table>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AutoQA AI                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   URL Input                                                     │
│      │                                                          │
│      ▼                                                          │
│  ┌──────────┐    discovers    ┌─────────────────────────────┐   │
│  │  Flask   │ ─────────────► │       SiteCrawler           │   │
│  │  Web App │                │  Selenium • PageData objects │   │
│  │  /scan   │                └──────────────┬──────────────┘   │
│  │  /status │                               │ pages[]          │
│  │  /report │                               ▼                  │
│  └──────────┘         ┌───────────────────────────────────┐    │
│       │               │           AutoTester              │    │
│  job queue            │  ┌─────────┐  ┌───────────────┐  │    │
│  threading            │  │Functional│  │     Link      │  │    │
│                        │  │  Tests  │  │  Validation   │  │    │
│                        │  └─────────┘  └───────────────┘  │    │
│                        │  ┌─────────┐  ┌───────────────┐  │    │
│                        │  │ Perform-│  │   Security    │  │    │
│                        │  │  ance   │  │    Headers    │  │    │
│                        │  └─────────┘  └───────────────┘  │    │
│                        └──────────────────┬────────────────┘   │
│                                           │ TestResult[]        │
│                        ┌──────────────────▼────────────────┐   │
│                        │     AccessibilityTester           │   │
│                        │     axe-core • WCAG checks        │   │
│                        └──────────────────┬────────────────┘   │
│                                           │                     │
│                        ┌──────────────────▼────────────────┐   │
│                        │          AIAnalyzer               │   │
│                        │  Groq API • Root cause • Fixes    │   │
│                        │  Executive summary generation     │   │
│                        └──────────────────┬────────────────┘   │
│                                           │                     │
│                        ┌──────────────────▼────────────────┐   │
│                        │        ReportGenerator            │   │
│                        │  HTML dashboard • JSON • CSV      │   │
│                        │  Chart.js charts • Screenshots    │   │
│                        └───────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Async Job Queue Flow

```
Browser                Flask App              Background Thread
   │                       │                         │
   │── POST /scan ─────────►│                         │
   │◄── { job_id } ────────│── spawn thread ─────────►│
   │                       │                         │ run scan
   │── GET /status ─────────►│                         │ crawl pages
   │◄── { running } ───────│                         │ run tests
   │                       │                         │ generate report
   │── GET /status ─────────►│                         │
   │◄── { done } ──────────│◄── write report ────────│
   │── GET /report ─────────►│                         │
   │◄── HTML report ────────│                         │
```

---

## Features

### Testing capabilities

| Category | Tests Performed |
|----------|----------------|
| **Functional** | Empty form submission, invalid email, SQL injection, XSS payloads, long text overflow, special characters |
| **Link Validation** | HTTP status for all discovered links — catches 404s, 5xx errors, and broken redirects |
| **Performance** | Page load time vs configurable thresholds — PASS / WARNING / FAIL ratings |
| **Security** | X-Frame-Options, Content-Security-Policy, X-Content-Type-Options, HSTS, Referrer-Policy |
| **Accessibility** | axe-core WCAG 2.1 violation detection — images, labels, contrast, ARIA |

### Engineering features

- **Async job queue** — background threading so the web app never blocks or times out on large sites
- **AI enhancement** — Groq LLM adds root-cause analysis, step-by-step fix instructions, and business impact to every failure
- **Executive summary** — AI-generated 3-paragraph summary for non-technical stakeholders
- **Retest mode** — load a previous JSON report and re-run only the tests that failed
- **Screenshot capture** — automatic screenshots saved on every test failure
- **Multi-format export** — HTML dashboard, JSON (for CI integration), and CSV (for spreadsheets)
- **CI/CD pipeline** — GitHub Actions runs unit tests, flake8 linting, and a live demo scan on every push

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/bhargavi0710/autoqa-ai.git
cd autoqa-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your free Groq API key
cp .env.example .env
# Edit .env — add GROQ_API_KEY from https://console.groq.com (free, no credit card)

# 5. Run your first scan
python main.py --url https://books.toscrape.com --headless

# 6. Open the report
# Saved to ./reports/report_YYYYMMDD_HHMMSS.html
```

> **Prerequisites:** Python 3.11+, Google Chrome installed locally

---

## CLI Reference

```bash
python main.py --url <URL> [options]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--url` | Target website URL *(required)* | — |
| `--headless` / `--no-headless` | Run browser headless or visible | `True` |
| `--browser` | Browser engine: `chrome` or `firefox` | `chrome` |
| `--max-pages` | Maximum pages to crawl | `20` |
| `--retest` | Path to previous JSON report — re-run failed tests only | — |
| `--export-csv` | Export results to CSV | `False` |
| `--no-ai` | Skip AI analysis (offline/faster mode) | `False` |
| `--output-dir` | Directory for reports and screenshots | `./reports` |

### Examples

```bash
# Standard scan
python main.py --url https://example.com --headless

# Quick scan — 5 pages, no AI, visible browser
python main.py --url https://example.com --no-headless --max-pages 5 --no-ai

# Re-run only previously failed tests
python main.py --url https://example.com --retest ./reports/report.json

# Full scan with CSV export
python main.py --url https://example.com --headless --export-csv --output-dir ./my-reports
```

---

## Web Interface (Work In Progress)

A Flask web app wraps the CLI for browser-based access. Run it locally:

```bash
python app.py
# Open http://localhost:5000
```

> ⚠️ **Deployment note:** Cloud deployment via Docker on Railway is currently in progress. Chrome/Selenium in containerised environments requires careful configuration. The CLI works fully — the web UI is functional locally.

---

## Project Structure

```
autoqa-ai/
├── main.py                  # CLI entry point
├── app.py                   # Flask web wrapper
├── requirements.txt
├── Dockerfile
├── railway.toml
├── autoqa/
│   ├── crawler.py           # Selenium site crawler
│   ├── tester.py            # Test runner (functional, perf, security, links)
│   ├── accessibility.py     # axe-core accessibility tester
│   ├── ai_analyzer.py       # Groq AI integration
│   ├── reporter.py          # HTML / JSON / CSV report generator
│   └── utils.py             # WebDriver setup, helpers
├── tests/
│   ├── test_crawler.py
│   ├── test_tester.py
│   └── test_reporter.py
└── .github/
    └── workflows/
        └── ci.yml           # GitHub Actions CI pipeline
```

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11 | Core language |
| Selenium 4 | Browser automation and crawling |
| axe-selenium-python | WCAG accessibility testing |
| Groq API (LLaMA 3) | AI bug report enhancement |
| Jinja2 | HTML report templating |
| Chart.js | Report data visualisations |
| Flask + Gunicorn | Web application wrapper |
| Docker | Containerised deployment |
| GitHub Actions | CI/CD — tests, linting, demo scan |
| pytest + pytest-mock | Unit testing |
| flake8 | Code quality linting |

---

## CI/CD Pipeline

Every push to `main` triggers three jobs automatically:

```
push to main
     │
     ├── lint        flake8 autoqa/ --max-line-length=120
     │
     ├── test        pytest tests/ -v --tb=short
     │               17/19 tests passing
     │
     └── demo-run    python main.py --url https://books.toscrape.com
                     --headless --no-ai --output-dir ./demo-reports
```

---

## Author

**Bhargavi Jagdale**

[![GitHub](https://img.shields.io/badge/GitHub-bhargavi0710-181717?style=flat-square&logo=github)](https://github.com/bhargavi0710)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Bhargavi_Jagdale-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/bhargavi-jagdale-a29b69290/)

---

## Getting a Free Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up — no credit card required
3. Click **API Keys** → **Create API Key**
4. Copy the key into your `.env` file as `GROQ_API_KEY=your_key_here`

Free tier: 14,400 requests/day — more than enough for development and demos.

---

<div align="center">
<em>Built to demonstrate automated testing, AI integration, and production Python engineering.</em>
</div>
