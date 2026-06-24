"""Unit tests for the AutoTester module."""

from unittest.mock import MagicMock, patch

import pytest

from autoqa.crawler import FieldData, FormData, PageData
from autoqa.tester import (
    INVALID_EMAIL,
    SQL_INJECTION_PAYLOAD,
    SPECIAL_CHARS,
    XSS_PAYLOAD,
    AutoTester,
    TestResult,
)


@pytest.fixture
def sample_page():
    """Create a sample PageData object with a form."""
    fields = [
        FieldData(name="email", field_type="email", required=True, placeholder="Email"),
        FieldData(name="username", field_type="text", required=False, placeholder="Name"),
    ]
    form = FormData(action="https://example.com/submit", method="post", fields=fields)
    return PageData(
        url="https://example.com",
        title="Example",
        load_time_ms=1200.0,
        forms=[form],
        links=["https://example.com/about"],
        raw_html="<html></html>",
    )


@pytest.fixture
def mock_driver():
    """Create a mock WebDriver for form interaction tests."""
    driver = MagicMock()
    driver.title = "Example"
    driver.page_source = "<html><body>No errors</body></html>"
    driver.current_url = "https://example.com"
    driver.find_elements.return_value = []
    driver.execute_script.return_value = False
    return driver


class TestAutoTesterConstants:
    """Tests for test payload constants."""

    def test_sql_injection_string(self):
        """Test that SQL injection string is correct."""
        assert SQL_INJECTION_PAYLOAD == "' OR '1'='1'; DROP TABLE users;--"

    def test_xss_string(self):
        """Test that XSS string is correct."""
        assert XSS_PAYLOAD == "<script>alert('XSS')</script>"

    def test_invalid_email_string(self):
        """Test invalid email constant."""
        assert INVALID_EMAIL == "notanemail@@@@"

    def test_special_chars_string(self):
        """Test special characters constant."""
        assert SPECIAL_CHARS == '!@#$%^&*()_+{}|:"<>?`~'


class TestAutoTesterSeverity:
    """Tests for severity mapping logic."""

    def test_performance_severity_high(self, mock_driver, sample_page):
        """Test High severity for load time > 3000ms."""
        slow_page = PageData(
            url="https://example.com/slow",
            title="Slow",
            load_time_ms=3500.0,
            forms=[],
            links=[],
            raw_html="",
        )
        tester = AutoTester(mock_driver, [slow_page], "reports")
        results = tester.run_all_tests()
        perf_results = [r for r in results if r.category == "Performance"]
        assert len(perf_results) == 1
        assert perf_results[0].status == "FAIL"
        assert perf_results[0].severity == "High"

    def test_performance_severity_medium(self, mock_driver, sample_page):
        """Test Medium severity for load time > 1500ms."""
        medium_page = PageData(
            url="https://example.com/medium",
            title="Medium",
            load_time_ms=2000.0,
            forms=[],
            links=[],
            raw_html="",
        )
        tester = AutoTester(mock_driver, [medium_page], "reports")
        results = tester.run_all_tests()
        perf_results = [r for r in results if r.category == "Performance"]
        assert perf_results[0].status == "WARNING"
        assert perf_results[0].severity == "Medium"

    def test_performance_severity_pass(self, mock_driver):
        """Test PASS for load time <= 1500ms."""
        fast_page = PageData(
            url="https://example.com/fast",
            title="Fast",
            load_time_ms=800.0,
            forms=[],
            links=[],
            raw_html="",
        )
        tester = AutoTester(mock_driver, [fast_page], "reports")
        results = tester.run_all_tests()
        perf_results = [r for r in results if r.category == "Performance"]
        assert perf_results[0].status == "PASS"
        assert perf_results[0].severity == "Info"


class TestAutoTesterTestIds:
    """Tests for sequential test ID generation."""

    def test_test_id_increments(self, mock_driver, tmp_path):
        """Test that test_id increments correctly (TC-001, TC-002...)."""
        page = PageData(
            url="https://example.com",
            title="Test",
            load_time_ms=500.0,
            forms=[],
            links=["https://example.com/a", "https://example.com/b"],
            raw_html="",
        )

        with patch("autoqa.tester.requests.head") as mock_head:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response

            with patch("autoqa.tester.requests.get") as mock_get:
                mock_get_response = MagicMock()
                mock_get_response.status_code = 200
                mock_get_response.headers = {
                    "X-Frame-Options": "DENY",
                    "Content-Security-Policy": "default-src 'self'",
                    "X-Content-Type-Options": "nosniff",
                }
                mock_get.return_value = mock_get_response

                tester = AutoTester(mock_driver, [page], str(tmp_path))
                results = tester.run_all_tests()

        test_ids = [r.test_id for r in results]
        assert test_ids[0] == "TC-001"
        assert test_ids[1] == "TC-002"
        for index, test_id in enumerate(test_ids, start=1):
            assert test_id == f"TC-{index:03d}"


class TestAutoTesterFormInteraction:
    """Tests for form interaction with mocked WebDriver."""

    def test_functional_tests_with_mock_driver(self, mock_driver, sample_page, tmp_path):
        """Test functional test execution with mocked WebDriver."""
        mock_driver.find_elements.return_value = []
        tester = AutoTester(mock_driver, [sample_page], str(tmp_path))

        with patch.object(tester, "_navigate_to_form", return_value=True):
            with patch.object(tester, "_fill_text_fields", return_value=1):
                with patch.object(tester, "_submit_form"):
                    with patch.object(tester, "_page_has_validation_error", return_value=True):
                        result = tester._test_empty_submission(
                            sample_page, sample_page.forms[0]
                        )

        assert result is not None
        assert result.category == "Functional"
        assert result.status == "PASS"

    def test_test_result_dataclass(self):
        """Test TestResult dataclass fields."""
        result = TestResult(
            test_id="TC-001",
            test_name="Test",
            category="Functional",
            page_url="https://example.com",
            precondition="Page loaded",
            steps=["Step 1"],
            expected_result="Expected",
            actual_result="Actual",
            status="PASS",
            severity="Info",
            screenshot_path=None,
            execution_time_ms=100.0,
        )
        assert result.summary is None
        assert result.recommended_fix is None
        assert result.business_impact is None
