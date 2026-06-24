"""Accessibility testing module using axe-core."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests
from selenium.webdriver.remote.webdriver import WebDriver

from autoqa.crawler import PageData
from autoqa.tester import TestResult

logger = logging.getLogger(__name__)

AXE_CORE_CDN = (
    "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"
)


class AccessibilityTester:
    """Runs axe-core accessibility scans on crawled pages."""

    def __init__(
        self,
        driver: WebDriver,
        pages: list[PageData],
        output_dir: str | None = None,
    ) -> None:
        """Initialize with WebDriver, pages, and optional screenshot output directory."""
        self.driver = driver
        self.pages = pages
        self.screenshots_path = Path(output_dir) / "screenshots" if output_dir else None
        if self.screenshots_path:
            self.screenshots_path.mkdir(parents=True, exist_ok=True)
        self._test_counter = 0
        self._axe_loaded = False

    def run(self) -> list[TestResult]:
        """Run accessibility tests on all pages and return TestResult list."""
        results: list[TestResult] = []
        total_pages = len(self.pages)
        for index, page in enumerate(self.pages, 1):
            print(f"  [{index}/{total_pages}] Scanning accessibility: {page.url} ...", flush=True)
            try:
                self.driver.get(page.url)
                self._ensure_axe_loaded()
                violations = self._run_axe()
                for violation in violations:
                    results.append(self._violation_to_result(violation, page.url))
            except Exception as exc:
                logger.warning(
                    "Accessibility test failed for %s: %s", page.url, exc
                )
        return results

    def _ensure_axe_loaded(self) -> None:
        """Inject axe-core JavaScript into the page if not already loaded."""
        try:
            loaded = self.driver.execute_script("return typeof axe !== 'undefined';")
            if loaded:
                return
        except Exception as exc:
            logger.warning("Error checking axe load state: %s", exc)

        if not hasattr(AccessibilityTester, "_axe_script_cache") or not AccessibilityTester._axe_script_cache:
            try:
                response = requests.get(AXE_CORE_CDN, timeout=10)
                response.raise_for_status()
                AccessibilityTester._axe_script_cache = response.text
            except Exception as exc:
                logger.warning("Failed to load axe-core from CDN: %s", exc)
                raise

        try:
            self.driver.execute_script(AccessibilityTester._axe_script_cache)
            self._axe_loaded = True
        except Exception as exc:
            logger.warning("Failed to inject axe-core: %s", exc)
            raise

    def _run_axe(self) -> list[dict]:
        """Execute axe.run asynchronously and return violations."""
        try:
            result = self.driver.execute_async_script(
                """
                var callback = arguments[arguments.length - 1];
                if (typeof axe === 'undefined') {
                    callback({violations: []});
                    return;
                }
                axe.run(document, function(err, results) {
                    if (err) {
                        callback({violations: []});
                    } else {
                        callback(results);
                    }
                });
                """
            )
            if result and isinstance(result, dict):
                return result.get("violations", [])
            return []
        except Exception as exc:
            logger.warning("axe.run execution failed: %s", exc)
            return []

    def _next_test_id(self) -> str:
        """Generate the next sequential test ID."""
        self._test_counter += 1
        return f"TC-{self._test_counter:03d}"

    def _map_impact(self, impact: str | None) -> str:
        """Map axe impact levels to severity strings."""
        mapping = {
            "critical": "Critical",
            "serious": "High",
            "moderate": "Medium",
            "minor": "Low",
        }
        return mapping.get((impact or "").lower(), "Info")

    def _violation_to_result(self, violation: dict, page_url: str) -> TestResult:
        """Convert an axe violation dict to a TestResult."""
        rule_id = violation.get("id", "unknown")
        description = violation.get("description", "Accessibility violation")
        impact = violation.get("impact", "minor")
        nodes = violation.get("nodes", [])
        target = nodes[0].get("target", ["unknown"])[0] if nodes else "unknown"

        start = time.perf_counter()
        test_id = self._next_test_id()
        screenshot_path = None

        if self.screenshots_path:
            screenshot_file = self.screenshots_path / f"{test_id}.png"
            try:
                self.driver.save_screenshot(str(screenshot_file))
                screenshot_path = str(screenshot_file)
            except Exception as exc:
                logger.warning(
                    "Failed to save accessibility screenshot for %s: %s",
                    test_id,
                    exc,
                )

        elapsed = (time.perf_counter() - start) * 1000

        return TestResult(
            test_id=test_id,
            test_name=f"Accessibility: {rule_id}",
            category="Accessibility",
            page_url=page_url,
            precondition=f"Page loaded at {page_url}",
            steps=[
                "Navigate to page",
                "Run axe-core accessibility scan",
                f"Inspect rule: {rule_id}",
            ],
            expected_result="No accessibility violations for this rule",
            actual_result=f"{description} — Element: {target}",
            status="FAIL",
            severity=self._map_impact(impact),
            screenshot_path=screenshot_path,
            execution_time_ms=elapsed,
            summary=None,
            recommended_fix=None,
            business_impact=None,
        )
