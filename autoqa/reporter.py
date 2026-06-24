"""HTML, CSV, and JSON report generation for AutoQA AI."""

from __future__ import annotations

import base64
import csv
import json
import logging
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from autoqa.tester import TestResult

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates HTML, CSV, and JSON reports from test results."""

    def __init__(
        self,
        results: list[TestResult],
        target_url: str,
        output_dir: str,
        executive_summary: str,
        browser: str = "chrome",
        scan_duration_seconds: float = 0.0,
    ) -> None:
        """Initialize report generator with results and metadata."""
        self.results = results
        self.target_url = target_url
        self.output_dir = Path(output_dir)
        self.executive_summary = executive_summary
        self.browser = browser
        self.scan_duration_seconds = scan_duration_seconds
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _compute_stats(self) -> dict:
        """Compute summary statistics for the report."""
        severity_counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
            "Info": 0,
        }
        category_counts: dict[str, dict[str, int]] = {}

        for result in self.results:
            if result.severity in severity_counts:
                severity_counts[result.severity] += 1

            if result.category not in category_counts:
                category_counts[result.category] = {"pass": 0, "fail": 0, "warning": 0}

            status_key = result.status.lower()
            if status_key == "pass":
                category_counts[result.category]["pass"] += 1
            elif status_key == "fail":
                category_counts[result.category]["fail"] += 1
            elif status_key == "warning":
                category_counts[result.category]["warning"] += 1

        total = len(self.results)
        passed = sum(1 for result in self.results if result.status == "PASS")
        failed = sum(1 for result in self.results if result.status == "FAIL")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "severity_counts": severity_counts,
            "category_counts": category_counts,
        }

    def _encode_screenshots(self) -> dict[str, str]:
        """Read screenshot files and encode as base64 strings."""
        encoded: dict[str, str] = {}
        for result in self.results:
            if not result.screenshot_path:
                continue
            screenshot_path = Path(result.screenshot_path)
            if not screenshot_path.exists():
                logger.warning("Screenshot not found: %s", screenshot_path)
                continue
            try:
                data = screenshot_path.read_bytes()
                encoded[result.test_id] = base64.b64encode(data).decode("utf-8")
            except Exception as exc:
                logger.warning(
                    "Failed to encode screenshot %s: %s", screenshot_path, exc
                )
        return encoded

    def generate_html(self) -> str:
        """Generate an HTML dashboard report and return the file path."""
        template_dir = Path(__file__).resolve().parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("report.html")

        stats = self._compute_stats()
        screenshots_b64 = self._encode_screenshots()

        html_content = template.render(
            results=self.results,
            target_url=self.target_url,
            scan_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            browser=self.browser,
            executive_summary=self.executive_summary,
            severity_counts=stats["severity_counts"],
            category_counts=stats["category_counts"],
            total_tests=stats["total"],
            passed_tests=stats["passed"],
            failed_tests=stats["failed"],
            scan_duration_seconds=self.scan_duration_seconds,
            screenshots_b64=screenshots_b64,
        )

        output_path = self.output_dir / f"report_{self.timestamp}.html"
        output_path.write_text(html_content, encoding="utf-8")
        logger.info("HTML report saved to %s", output_path)
        return str(output_path)

    def generate_csv(self) -> str:
        """Generate a CSV export of all test results."""
        output_path = self.output_dir / f"report_{self.timestamp}.csv"
        field_names = [field_item.name for field_item in fields(TestResult)]

        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()
            for result in self.results:
                row = asdict(result)
                row["steps"] = " | ".join(result.steps)
                writer.writerow(row)

        logger.info("CSV report saved to %s", output_path)
        return str(output_path)

    def generate_json(self) -> str:
        """Generate a JSON export of all test results."""
        output_path = self.output_dir / f"report_{self.timestamp}.json"
        payload = {
            "target_url": self.target_url,
            "scan_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "browser": self.browser,
            "executive_summary": self.executive_summary,
            "scan_duration_seconds": self.scan_duration_seconds,
            "results": [asdict(result) for result in self.results],
        }

        with output_path.open("w", encoding="utf-8") as json_file:
            json.dump(payload, json_file, indent=2)

        logger.info("JSON report saved to %s", output_path)
        return str(output_path)
