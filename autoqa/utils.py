"""Utility functions for AutoQA AI."""

from pathlib import Path
import json
import logging
import re
import platform
import os
import stat
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


def _resolve_driver_executable(manager_path: str, executable_name: str) -> str:
    """Resolve the actual WebDriver executable from webdriver-manager output."""
    path = Path(manager_path)

    if path.is_file():
        if path.name in (
            executable_name,
            executable_name.replace(".exe", ""),
        ):
            return str(path)

    search_root = path.parent if path.is_file() else path

    candidates = [
        executable_name,
        executable_name.replace(".exe", ""),
    ]

    for candidate in candidates:
        matches = sorted(search_root.rglob(candidate))
        if matches:
            return str(matches[0])

    raise FileNotFoundError(
        f"Could not locate {executable_name} near webdriver-manager path: {manager_path}"
    )


def setup_driver(browser: str = "chrome", headless: bool = True) -> webdriver.Remote:
    """Initialize and return a configured Selenium WebDriver."""

    if browser == "chrome":
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--single-process")
        options.add_argument("--no-zygote")

        # All possible chromium binary locations across Railway/nixpacks/Ubuntu
        chromium_candidates = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/snap/bin/chromium",
        ]
        chromedriver_candidates = [
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
        ]

        chromium_path = next(
            (p for p in chromium_candidates if Path(p).exists()), None
        )
        chromedriver_path = next(
            (p for p in chromedriver_candidates if Path(p).exists()), None
        )

        if not chromium_path:
            chromium_path = (
                shutil.which("chromium")
                or shutil.which("chromium-browser")
                or shutil.which("google-chrome")
            )

        if not chromedriver_path:
            chromedriver_path = shutil.which("chromedriver")

        if chromium_path and chromedriver_path:
            logger.info("Using system Chromium at %s", chromium_path)
            logger.info("Using system ChromeDriver at %s", chromedriver_path)
            options.binary_location = chromium_path
            service = ChromeService(executable_path=chromedriver_path)
        else:
            logger.info("System Chromium not found, using webdriver-manager")
            logger.info(
                "Chromium found: %s | ChromeDriver found: %s",
                chromium_path,
                chromedriver_path,
            )
            chrome_executable = (
                "chromedriver.exe"
                if platform.system() == "Windows"
                else "chromedriver"
            )
            driver_path = _resolve_driver_executable(
                ChromeDriverManager().install(),
                chrome_executable,
            )
            if platform.system() != "Windows":
                os.chmod(
                    driver_path,
                    os.stat(driver_path).st_mode | stat.S_IEXEC,
                )
            service = ChromeService(driver_path)

        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5)
        driver.set_page_load_timeout(15)
        return driver

    elif browser == "firefox":
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        from selenium.webdriver.firefox.service import Service as FirefoxService
        from webdriver_manager.firefox import GeckoDriverManager

        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")

        firefox_executable = (
            "geckodriver.exe"
            if platform.system() == "Windows"
            else "geckodriver"
        )
        driver_path = _resolve_driver_executable(
            GeckoDriverManager().install(),
            firefox_executable,
        )
        if platform.system() != "Windows":
            os.chmod(
                driver_path,
                os.stat(driver_path).st_mode | stat.S_IEXEC,
            )
        driver = webdriver.Firefox(
            service=FirefoxService(driver_path),
            options=options,
        )
        driver.implicitly_wait(5)
        driver.set_page_load_timeout(15)
        return driver

    else:
        raise ValueError(f"Unsupported browser: {browser}")


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
        return [
            entry["test_id"]
            for entry in results
            if entry.get("status") == "FAIL"
        ]

    return []
