"""Flask web wrapper for AutoQA AI cloud deployment."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from flask import Flask, request

app = Flask(__name__)
logger = logging.getLogger(__name__)

REPORT_DIR = Path(__file__).resolve().parent / "reports"


@app.route("/")
def index():
    """Serve the AutoQA AI web interface."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AutoQA AI</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: #f1f5f9;
      min-height: 100vh;
    }
    .header {
      background: #0f172a;
      color: #ffffff;
      padding: 24px 32px;
      text-align: center;
    }
    .header h1 { font-size: 28px; font-weight: 700; }
    .header p { color: #94a3b8; margin-top: 8px; font-size: 14px; }
    .container {
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 48px 24px;
    }
    .card {
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      padding: 40px;
      width: 100%;
      max-width: 520px;
    }
    .card h2 { font-size: 20px; margin-bottom: 8px; color: #0f172a; }
    .card p { color: #64748b; font-size: 14px; margin-bottom: 24px; }
    label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #334155; }
    input[type="url"] {
      width: 100%;
      padding: 12px 16px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      font-size: 16px;
      font-family: inherit;
      margin-bottom: 20px;
    }
    input[type="url"]:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }
    button {
      width: 100%;
      padding: 14px;
      background: #0f172a;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
    }
    button:hover { background: #1e293b; }
    .note {
      text-align: center;
      margin-top: 16px;
      font-size: 13px;
      color: #94a3b8;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>AutoQA AI</h1>
    <p>AI-Powered Automated QA Testing</p>
  </div>
  <div class="container">
    <div class="card">
      <h2>Run a Website Scan</h2>
      <p>Enter a URL to automatically crawl, test, and generate a QA report.</p>
      <form action="/run" method="POST">
        <label for="url">Website URL</label>
        <input type="url" id="url" name="url" placeholder="https://example.com" required>
        <button type="submit">Run Tests</button>
      </form>
      <p class="note">Scan takes 2-5 minutes depending on site size</p>
    </div>
  </div>
</body>
</html>
"""


@app.route("/run", methods=["POST"])
def run_scan():
    """Execute AutoQA scan via subprocess and return HTML report."""
    try:
        url = request.form.get("url", "").strip()
        if not url.startswith(("http://", "https://")):
            return _error_page("Please enter a valid URL starting with http:// or https://")

        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "main.py",
            "--url",
            url,
            "--headless",
            "--no-ai",
            "--output-dir",
            str(REPORT_DIR),
        ]

        result = subprocess.run(
            cmd,
            timeout=300,
            capture_output=True,
            text=True,
        )

        if result.returncode not in (0, 1):
            error_msg = result.stderr or result.stdout or "Unknown error during scan"
            logger.error("Scan subprocess failed: %s", error_msg)
            return _error_page(f"Scan failed: {error_msg[:500]}")

        html_files = sorted(
            REPORT_DIR.glob("*.html"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        if not html_files:
            return _error_page("Scan completed but no HTML report was generated.")

        report_content = html_files[0].read_text(encoding="utf-8")
        return report_content, 200, {"Content-Type": "text/html; charset=utf-8"}

    except subprocess.TimeoutExpired:
        logger.error("Scan timed out after 300 seconds")
        return _error_page("Scan timed out after 5 minutes. Try a smaller website.")
    except Exception as exc:
        logger.error("Run scan error: %s", exc, exc_info=True)
        return _error_page(f"An error occurred: {exc}")


def _error_page(message: str) -> str:
    """Return a friendly HTML error page."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AutoQA AI — Error</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {{
      font-family: 'Inter', sans-serif;
      background: #f1f5f9;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
    }}
    .error-card {{
      background: #ffffff;
      border-radius: 12px;
      padding: 40px;
      max-width: 500px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      text-align: center;
    }}
    h1 {{ color: #dc2626; font-size: 24px; margin-bottom: 16px; }}
    p {{ color: #64748b; line-height: 1.6; }}
    a {{ color: #2563eb; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="error-card">
    <h1>Scan Error</h1>
    <p>{message}</p>
    <p style="margin-top: 24px;"><a href="/">← Back to Home</a></p>
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
