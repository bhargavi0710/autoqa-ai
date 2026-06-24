"""Utility functions for AutoQA AI."""

from pathlib import Path
import json
import logging
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

logger = logging.getLogger(__name__)


def _resolve_driver_executable(manager_path: str, executable_name: str) -> str:
    """Resolve the actual WebDriver executable from webdriver-manager output.

    webdriver-manager 4.0.1 can return a non-executable file (e.g. THIRD_PARTY_NOTICES)
    instead of chromedriver.exe on Windows. Search the install directory when that happens.
    """
    path = Path(manager_path)

    if path.name.lower() == executable_name.lower() and path.is_file():
        return str(path)

    search_root = path.parent if path.is_file() else path
    matches = sorted(search_root.rglob(executable_name))
    if matches:
        return str(matches[0])

    raise FileNotFoundError(
        f"Could not locate {executable_name} near webdriver-manager path: {manager_path}"
    )


def setup_driver(browser: str = "chrome", headless: bool = True) -> webdriver.Remote:
    """Initialize and return a configured Selenium WebDriver."""
    if browser == "chrome":
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        driver_path = _resolve_driver_executable(
            ChromeDriverManager().install(),
            "chromedriver.exe",
        )
        driver = webdriver.Chrome(
            service=ChromeService(driver_path),
            options=options,
        )
    elif browser == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        driver_path = _resolve_driver_executable(
            GeckoDriverManager().install(),
            "geckodriver.exe",
        )
        driver = webdriver.Firefox(
            service=FirefoxService(driver_path),
            options=options,
        )
    else:
        raise ValueError(f"Unsupported browser: {browser}")

    driver.implicitly_wait(5)
    driver.set_page_load_timeout(15)
    return driver


def create_output_dirs(output_dir: str) -> tuple[Path, Path]:
    """Create output and screenshots directories. Returns (output_path, screenshots_path)."""
    out = Path(output_dir)
    screenshots = out / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    screenshots.mkdir(parents=True, exist_ok=True)
    return out, screenshots


def format_duration(ms: float) -> str:
    """Format milliseconds as human readable string."""
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{ms:.0f}ms"


def sanitize_filename(url: str) -> str:
    """Convert a URL into a safe filename string."""
    return re.sub(r"[^\w\-_]", "_", url)[:50]


def load_json_report(path: str) -> dict:
    """Load a previous JSON report from disk for retest mode."""
    report_path = Path(path)
    with report_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def get_failed_test_ids(report: dict) -> list[str]:
    """Extract test IDs that previously failed from a loaded JSON report."""
    results = report.get("results", report if isinstance(report, list) else [])
    if isinstance(results, list):
        return [entry["test_id"] for entry in results if entry.get("status") == "FAIL"]
    return []
