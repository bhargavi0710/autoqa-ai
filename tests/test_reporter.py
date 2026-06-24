"""Unit tests for the ReportGenerator module."""

import json
from pathlib import Path

import pytest

from autoqa.reporter import ReportGenerator
from autoqa.tester import TestResult


@pytest.fixture
def sample_results():
    """Create sample TestResult objects for reporting tests."""
    return [
        TestResult(
            test_id="TC-001",
            test_name="Empty submission test",
            category="Functional",
            page_url="https://example.com",
            precondition="Form is visible",
            steps=["Clear fields", "Submit"],
            expected_result="Validation error",
            actual_result="Validation error shown",
            status="PASS",
            severity="Info",
            screenshot_path=None,
            execution_time_ms=150.0,
        ),
        TestResult(
            test_id="TC-002",
            test_name="SQL injection test",
            category="Functional",
            page_url="https://example.com",
            precondition="Form has text fields",
            steps=["Enter payload", "Submit"],
            expected_result="Safe rejection",
            actual_result="Database error exposed",
            status="FAIL",
            severity="Critical",
            screenshot_path=None,
            execution_time_ms=320.0,
            summary="Critical SQL injection vulnerability detected",
            recommended_fix="Use parameterized queries",
            business_impact="User data could be compromised",
        ),
    ]


@pytest.fixture
def reporter(sample_results, tmp_path):
    """Create a ReportGenerator instance with sample data."""
    return ReportGenerator(
        results=sample_results,
        target_url="https://example.com",
        output_dir=str(tmp_path),
        executive_summary="Test executive summary for the scan.",
        browser="chrome",
        scan_duration_seconds=45.5,
    )


class TestReportGenerator:
    """Tests for report generation methods."""

    def test_generate_csv_creates_file_with_headers(self, reporter, tmp_path, sample_results):
        """Test generate_csv() creates a file with correct headers."""
        csv_path = reporter.generate_csv()
        assert Path(csv_path).exists()

        content = Path(csv_path).read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        header = lines[0]

        assert "test_id" in header
        assert "test_name" in header
        assert "category" in header
        assert "severity" in header
        assert "status" in header
        assert len(lines) == len(sample_results) + 1

    def test_generate_json_round_trips(self, reporter, tmp_path, sample_results):
        """Test generate_json() creates valid JSON that round-trips correctly."""
        json_path = reporter.generate_json()
        assert Path(json_path).exists()

        with Path(json_path).open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        assert data["target_url"] == "https://example.com"
        assert len(data["results"]) == len(sample_results)
        assert data["results"][0]["test_id"] == "TC-001"
        assert data["results"][1]["status"] == "FAIL"
        assert data["executive_summary"] == "Test executive summary for the scan."

    def test_generate_html_creates_nonempty_file(self, reporter, tmp_path):
        """Test generate_html() creates a non-empty .html file."""
        html_path = reporter.generate_html()
        html_file = Path(html_path)

        assert html_file.exists()
        assert html_file.suffix == ".html"

        content = html_file.read_text(encoding="utf-8")
        assert len(content) > 0
        assert "AutoQA AI" in content
        assert "TC-001" in content
        assert "TC-002" in content
        assert "chart.js" in content.lower() or "Chart" in content

    def test_compute_stats(self, reporter):
        """Test internal stats computation."""
        stats = reporter._compute_stats()
        assert stats["total"] == 2
        assert stats["passed"] == 1
        assert stats["failed"] == 1
        assert stats["severity_counts"]["Critical"] == 1
