"""Flask web wrapper for AutoQA AI cloud deployment."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
logger = logging.getLogger(__name__)

REPORT_DIR = Path("/tmp/autoqa-reports")

# In-memory job store: { job_id: { status, report_html, error } }
jobs: dict[str, dict] = {}


def run_scan_worker(job_id: str, url: str) -> None:
    """Background thread: runs the scan and updates job store when done."""
    jobs[job_id]["status"] = "running"
    logger.info("Job %s started for %s", job_id, url)

    job_report_dir = REPORT_DIR / job_id
    job_report_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "main.py",
        "--url",
        url,
        "--headless",
        "--max-pages", "5",
        "--output-dir",
        str(job_report_dir),
    ]

    logger.info("Job %s cmd: %s", job_id, " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            timeout=480,
            capture_output=True,
            text=True,
        )

        logger.info("Job %s exit code: %s", job_id, result.returncode)
        if result.stdout:
            logger.info("Job %s stdout:\n%s", job_id, result.stdout[:5000])
        if result.stderr:
            logger.error("Job %s stderr:\n%s", job_id, result.stderr[:5000])

        html_files = sorted(
            job_report_dir.glob("*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if html_files:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["report_html"] = html_files[0].read_text(encoding="utf-8")
            logger.info("Job %s completed successfully", job_id)
        else:
            debug = (result.stdout or "")[-800:] + (result.stderr or "")[-400:]
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = f"No report generated. Output: {debug}"
            logger.error("Job %s: no HTML report found", job_id)

    except subprocess.TimeoutExpired:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "Scan timed out after 8 minutes."
        logger.error("Job %s timed out", job_id)
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        logger.error("Job %s failed: %s", job_id, exc, exc_info=True)


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
    outline:none;
    transition:border-color .2s, box-shadow .2s;
}

input[type=url]:focus{
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

button:disabled{
    background:#94a3b8;
    cursor:not-allowed;
}

.status-box{
    display:none;
    margin-top:24px;
    padding:20px;
    border-radius:12px;
    background:#eff6ff;
    border:1px solid #bfdbfe;
}

.status-box.error{
    background:#fef2f2;
    border-color:#fecaca;
}

.status-top{
    display:flex;
    align-items:center;
    gap:10px;
    margin-bottom:12px;
}

.spinner{
    width:18px;
    height:18px;
    border:2px solid #bfdbfe;
    border-top:2px solid #2563eb;
    border-radius:50%;
    animation:spin .8s linear infinite;
    flex-shrink:0;
}

.status-box.error .spinner{
    display:none;
}

.status-text{
    font-size:15px;
    font-weight:500;
    color:#1e40af;
}

.status-box.error .status-text{
    color:#991b1b;
}

.status-sub{
    font-size:13px;
    color:#64748b;
    margin-bottom:12px;
}

.progress-track{
    height:6px;
    background:#dbeafe;
    border-radius:3px;
    overflow:hidden;
}

.progress-fill{
    height:100%;
    width:0%;
    background:#2563eb;
    border-radius:3px;
    transition:width .6s ease;
}

.status-box.error .progress-fill{
    background:#ef4444;
}

@keyframes spin{
    100%{ transform:rotate(360deg); }
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

@media(max-width:768px){
    .hero h1{ font-size:40px; }
    .scan-card{ padding:25px; }
}
</style>
</head>
<body>

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

        <input type="url" id="url-input" placeholder="https://example.com" autocomplete="off">
        <button id="scan-btn" onclick="startScan()">Start Automated Scan &rarr;</button>

        <div class="status-box" id="status-box">
            <div class="status-top">
                <div class="spinner" id="spinner"></div>
                <span class="status-text" id="status-text">Starting scan...</span>
            </div>
            <div class="status-sub" id="status-sub">This may take 2&ndash;5 minutes for large sites.</div>
            <div class="progress-track">
                <div class="progress-fill" id="progress-fill"></div>
            </div>
        </div>

        <p style="margin-top:15px;color:#94a3b8;font-size:14px;">
            Typical scan duration: 2&ndash;5 minutes
        </p>
    </div>
</section>

<section class="stats">
    <div class="stat-card">
        <h3>&#9889; Performance</h3>
        <p>Page load testing and responsiveness analysis</p>
    </div>
    <div class="stat-card">
        <h3>&#128274; Security</h3>
        <p>HTTP headers and vulnerability checks</p>
    </div>
    <div class="stat-card">
        <h3>&#9855; Accessibility</h3>
        <p>Automated WCAG compliance validation</p>
    </div>
    <div class="stat-card">
        <h3>&#129302; AI Analysis</h3>
        <p>Root cause detection and remediation suggestions</p>
    </div>
</section>

<section class="features">
    <h2>Platform Features</h2>
    <div class="feature-grid">
        <div class="feature">
            <h3>Website Crawling</h3>
            <p>Automatically discover pages and collect testing targets.</p>
        </div>
        <div class="feature">
            <h3>Automated QA Testing</h3>
            <p>Validate performance, functionality and reliability.</p>
        </div>
        <div class="feature">
            <h3>Accessibility Audits</h3>
            <p>Identify accessibility issues using automated checks.</p>
        </div>
        <div class="feature">
            <h3>Professional Reports</h3>
            <p>Generate detailed HTML reports with actionable findings.</p>
        </div>
    </div>
</section>

<div class="footer">
    AutoQA AI &bull; Automated Website Quality Assurance Platform
</div>

<script>
let pollInterval = null;
let progressVal = 0;

function startScan() {
    const url = document.getElementById('url-input').value.trim();
    if (!url.startsWith('http')) {
        alert('Please enter a valid URL starting with http:// or https://');
        return;
    }

    document.getElementById('scan-btn').disabled = true;
    showStatus('Submitting scan...', 'Connecting to server...', false);
    progressVal = 5;
    setProgress(progressVal);

    fetch('/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'url=' + encodeURIComponent(url)
    })
    .then(r => r.json())
    .then(data => {
        if (data.job_id) {
            showStatus('Scan started', 'Crawling site and running tests...', false);
            pollJob(data.job_id);
        } else {
            showStatus('Failed to start scan', data.error || 'Unknown error', true);
            document.getElementById('scan-btn').disabled = false;
        }
    })
    .catch(err => {
        showStatus('Network error', String(err), true);
        document.getElementById('scan-btn').disabled = false;
    });
}

function pollJob(jobId) {
    clearInterval(pollInterval);
    let elapsed = 0;

    pollInterval = setInterval(function() {
        elapsed += 3;

        if (progressVal < 30) progressVal += 3;
        else if (progressVal < 70) progressVal += 1.5;
        else if (progressVal < 90) progressVal += 0.5;
        setProgress(progressVal);

        var mainMsg, subMsg;
        if (elapsed < 20) {
            mainMsg = 'Initialising browser...';
            subMsg = 'Starting headless Chrome on the server.';
        } else if (elapsed < 60) {
            mainMsg = 'Crawling pages...';
            subMsg = 'Discovering and loading pages on the target site.';
        } else if (elapsed < 150) {
            mainMsg = 'Running tests...';
            subMsg = 'Checking performance, security, accessibility and functionality.';
        } else if (elapsed < 240) {
            mainMsg = 'Generating AI analysis...';
            subMsg = 'AI is analysing findings and writing recommendations.';
        } else {
            mainMsg = 'Finalising report...';
            subMsg = 'Almost done — building your HTML report.';
        }
        showStatus(mainMsg, subMsg, false);

        fetch('/status/' + jobId)
        .then(r => r.json())
        .then(function(data) {
            if (data.status === 'done') {
                clearInterval(pollInterval);
                setProgress(100);
                showStatus('Scan complete!', 'Loading your report...', false);
                setTimeout(function() {
                    window.location.href = '/report/' + jobId;
                }, 600);
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                showStatus('Scan failed', data.error || 'Unknown error', true);
                document.getElementById('scan-btn').disabled = false;
            }
        })
        .catch(function() {});
    }, 3000);
}

function showStatus(main, sub, isError) {
    var box = document.getElementById('status-box');
    box.style.display = 'block';
    box.className = 'status-box' + (isError ? ' error' : '');
    document.getElementById('status-text').textContent = main;
    document.getElementById('status-sub').textContent = sub;
    if (isError) setProgress(100);
}

function setProgress(val) {
    document.getElementById('progress-fill').style.width = val + '%';
}
</script>

</body>
</html>
"""


@app.route("/scan", methods=["POST"])
def submit_scan():
    """Accept scan request, spin up background thread, return job_id immediately."""
    url = request.form.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL — must start with http:// or https://"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "report_html": None, "error": None}

    thread = threading.Thread(
        target=run_scan_worker,
        args=(job_id, url),
        daemon=True,
    )
    thread.start()

    logger.info("Job %s queued for %s", job_id, url)
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def job_status(job_id: str):
    """Return current job status for polling."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job["status"],
        "error": job.get("error"),
    })


@app.route("/report/<job_id>")
def view_report(job_id: str):
    """Serve the completed HTML report."""
    job = jobs.get(job_id)
    if not job:
        return _error_page("Report not found. It may have expired — please run a new scan."), 404
    if job["status"] == "error":
        return _error_page(f"Scan failed: {job.get('error', 'Unknown error')}"), 500
    if job["status"] != "done":
        return _error_page(
            f"Report not ready yet (status: {job['status']}). "
            f"Please wait and refresh."
        ), 202
    return job["report_html"], 200, {"Content-Type": "text/html; charset=utf-8"}


def _error_page(message: str) -> str:
    """Return a friendly HTML error page."""
    return f"""<!DOCTYPE html>
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
      max-width: 560px;
      width: 100%;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      text-align: center;
    }}
    h1 {{ color: #dc2626; font-size: 24px; margin-bottom: 16px; }}
    p {{ color: #64748b; line-height: 1.6; font-size: 14px; word-break: break-word; }}
    a {{ color: #2563eb; text-decoration: none; display: inline-block; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="error-card">
    <h1>Scan Error</h1>
    <p>{message}</p>
    <a href="/">&#8592; Back to Home</a>
  </div>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)