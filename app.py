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

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">

<style>
*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:'Inter',sans-serif;
    background:#f8fafc;
    color:#0f172a;
}

.hero{
    background:linear-gradient(135deg,#0f172a,#1e3a8a);
    color:white;
    padding:80px 20px;
    text-align:center;
}

.hero h1{
    font-size:56px;
    font-weight:800;
    margin-bottom:16px;
}

.hero p{
    font-size:18px;
    color:#cbd5e1;
    max-width:700px;
    margin:auto;
}

.scan-section{
    max-width:900px;
    margin:-50px auto 0;
    padding:0 20px;
}

.scan-card{
    background:white;
    border-radius:20px;
    padding:40px;
    box-shadow:0 15px 40px rgba(0,0,0,.08);
}

.scan-card h2{
    margin-bottom:10px;
}

.scan-card p{
    color:#64748b;
    margin-bottom:24px;
}

input[type=url]{
    width:100%;
    padding:18px;
    border:1px solid #cbd5e1;
    border-radius:12px;
    font-size:16px;
    margin-bottom:20px;
}

input[type=url]:focus{
    outline:none;
    border-color:#2563eb;
    box-shadow:0 0 0 4px rgba(37,99,235,.15);
}

button{
    width:100%;
    padding:18px;
    border:none;
    border-radius:12px;
    background:#2563eb;
    color:white;
    font-size:17px;
    font-weight:700;
    cursor:pointer;
    transition:.2s;
}

button:hover{
    background:#1d4ed8;
}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:20px;
    max-width:1100px;
    margin:70px auto;
    padding:0 20px;
}

.stat-card{
    background:white;
    border-radius:16px;
    padding:25px;
    text-align:center;
    box-shadow:0 4px 20px rgba(0,0,0,.05);
}

.stat-card h3{
    font-size:18px;
    margin-bottom:10px;
}

.stat-card p{
    color:#64748b;
    font-size:14px;
}

.features{
    max-width:1200px;
    margin:40px auto 80px;
    padding:0 20px;
}

.features h2{
    text-align:center;
    margin-bottom:40px;
    font-size:34px;
}

.feature-grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
    gap:24px;
}

.feature{
    background:white;
    padding:30px;
    border-radius:18px;
    box-shadow:0 4px 20px rgba(0,0,0,.05);
}

.feature h3{
    margin-bottom:10px;
}

.feature p{
    color:#64748b;
    line-height:1.6;
}

.footer{
    text-align:center;
    padding:40px;
    color:#64748b;
}

.loader{
    display:none;
    position:fixed;
    inset:0;
    background:rgba(255,255,255,.95);
    z-index:9999;
    justify-content:center;
    align-items:center;
    flex-direction:column;
}

.spinner{
    width:70px;
    height:70px;
    border:7px solid #e2e8f0;
    border-top:7px solid #2563eb;
    border-radius:50%;
    animation:spin 1s linear infinite;
    margin-bottom:20px;
}

.loader h2{
    margin-bottom:10px;
}

.loader p{
    color:#64748b;
}

@keyframes spin{
    100%{
        transform:rotate(360deg);
    }
}

@media(max-width:768px){

.hero h1{
    font-size:40px;
}

.scan-card{
    padding:25px;
}

}
</style>

<script>
function showLoader(){
    document.getElementById('loader').style.display='flex';
}
</script>

</head>
<body>

<div id="loader" class="loader">
    <div class="spinner"></div>
    <h2>Running AutoQA Scan...</h2>
    <p>
        Initializing Browser • Crawling Website • Running Tests • Generating Report
    </p>
</div>

<section class="hero">
    <h1>AutoQA AI</h1>
    <p>
        AI-Powered Automated Website Testing Platform for
        Performance, Security, Accessibility and Quality Assurance.
    </p>
</section>

<section class="scan-section">
    <div class="scan-card">
        <h2>Run Automated Website Testing</h2>
        <p>
            Enter any website URL and receive a comprehensive QA report
            with security checks, accessibility audits and AI-powered insights.
        </p>

        <form action="/run" method="POST" onsubmit="showLoader()">
            <input
                type="url"
                name="url"
                placeholder="https://example.com"
                required
            >

            <button type="submit">
                Start Automated Scan →
            </button>
        </form>

        <p style="margin-top:15px;color:#94a3b8;font-size:14px;">
            Typical scan duration: 2–5 minutes
        </p>
    </div>
</section>

<section class="stats">

<div class="stat-card">
    <h3>⚡ Performance</h3>
    <p>Page load testing and responsiveness analysis</p>
</div>

<div class="stat-card">
    <h3>🔒 Security</h3>
    <p>HTTP headers and vulnerability checks</p>
</div>

<div class="stat-card">
    <h3>♿ Accessibility</h3>
    <p>Automated WCAG compliance validation</p>
</div>

<div class="stat-card">
    <h3>🤖 AI Analysis</h3>
    <p>Root cause detection and remediation suggestions</p>
</div>

</section>

<section class="features">

<h2>Platform Features</h2>

<div class="feature-grid">

<div class="feature">
    <h3>Website Crawling</h3>
    <p>
        Automatically discover pages and collect testing targets.
    </p>
</div>

<div class="feature">
    <h3>Automated QA Testing</h3>
    <p>
        Validate performance, functionality and reliability.
    </p>
</div>

<div class="feature">
    <h3>Accessibility Audits</h3>
    <p>
        Identify accessibility issues using automated checks.
    </p>
</div>

<div class="feature">
    <h3>Professional Reports</h3>
    <p>
        Generate detailed HTML reports with actionable findings.
    </p>
</div>

</div>

</section>

<div class="footer">
    AutoQA AI • Automated Website Quality Assurance Platform
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
            timeout=600,
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
      logger.error("Scan timed out after 600 seconds")
      return _error_page(
        "Scan timed out after 10 minutes. Try a smaller website."
      )
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
