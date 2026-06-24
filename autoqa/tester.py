"""Automated test execution module for AutoQA AI."""

from __future__ import annotations

import logging
import random
import string
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from selenium.common.exceptions import (
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from autoqa.crawler import FormData, PageData

logger = logging.getLogger(__name__)

SQL_INJECTION_PAYLOAD = "' OR '1'='1'; DROP TABLE users;--"
XSS_PAYLOAD = "<script>alert('XSS')</script>"
INVALID_EMAIL = "notanemail@@@@"
SPECIAL_CHARS = '!@#$%^&*()_+{}|:"<>?`~'
LONG_TEXT_LENGTH = 5000

DB_ERROR_PATTERNS = [
    "sql syntax",
    "mysql",
    "postgresql",
    "sqlite",
    "ora-",
    "database error",
    "sqlstate",
    "unhandled exception",
]


@dataclass
class TestResult:
    """Represents the outcome of a single automated test."""

    __test__ = False

    test_id: str
    test_name: str
    category: str
    page_url: str
    precondition: str
    steps: list[str]
    expected_result: str
    actual_result: str
    status: str
    severity: str
    screenshot_path: str | None
    execution_time_ms: float
    summary: str | None = None
    recommended_fix: str | None = None
    business_impact: str | None = None


class AutoTester:
    """Runs functional, link, performance, and security tests against crawled pages."""

    def __init__(
        self,
        driver: WebDriver,
        pages: list[PageData],
        output_dir: str,
        retest_ids: list[str] | None = None,
    ) -> None:
        """Initialize tester with driver, pages, output directory, and optional retest filter."""
        self.driver = driver
        self.pages = pages
        self.output_path = Path(output_dir)
        self.screenshots_path = self.output_path / "screenshots"
        self.screenshots_path.mkdir(parents=True, exist_ok=True)
        self.retest_ids = set(retest_ids or [])
        self._test_counter = 0
        self.results: list[TestResult] = []

    def run_all_tests(self) -> list[TestResult]:
        """Execute all test suites and return aggregated results."""
        self.results = []
        self._test_counter = 0

        total_pages = len(self.pages)
        for index, page in enumerate(self.pages, 1):
            print(f"  [{index}/{total_pages}] Testing page: {page.url} ...", flush=True)
            for form in page.forms:
                self._run_functional_tests(page, form)

            for link in page.links:
                self._run_link_test(link)

            self._run_performance_test(page)
            self._run_security_header_tests(page)

        if self.retest_ids:
            self.results = [
                result for result in self.results if result.test_id in self.retest_ids
            ]

        return self.results

    def _next_test_id(self) -> str:
        """Generate the next sequential test ID."""
        self._test_counter += 1
        return f"TC-{self._test_counter:03d}"

    def _record_result(self, result: TestResult) -> None:
        """Append result and capture screenshot on failure."""
        if result.status == "FAIL" and result.screenshot_path is None:
            screenshot_path = self.screenshots_path / f"{result.test_id}.png"
            try:
                self.driver.save_screenshot(str(screenshot_path))
                result.screenshot_path = str(screenshot_path)
            except Exception as exc:
                logger.warning(
                    "Failed to save screenshot for %s: %s", result.test_id, exc
                )
        self.results.append(result)

    def _run_functional_tests(self, page: PageData, form: FormData) -> None:
        """Run all functional test cases against a form."""
        test_cases = [
            self._test_empty_submission,
            self._test_invalid_email,
            self._test_sql_injection,
            self._test_xss,
            self._test_long_text_overflow,
            self._test_special_characters,
        ]
        for test_fn in test_cases:
            try:
                result = test_fn(page, form)
                if result:
                    self._record_result(result)
            except Exception as exc:
                logger.warning(
                    "Functional test %s failed on %s: %s",
                    test_fn.__name__,
                    page.url,
                    exc,
                )

    def _navigate_to_form(self, page: PageData, form: FormData) -> bool:
        """Navigate to page and locate the target form."""
        try:
            self.driver.get(page.url)
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            if not forms:
                return False
            for form_el in forms:
                action = form_el.get_attribute("action") or page.url
                action = urljoin(page.url, action)
                method = (form_el.get_attribute("method") or "get").lower()
                if action == form.action or method == form.method:
                    return True
            return len(forms) > 0
        except WebDriverException as exc:
            logger.warning("Navigation to form failed on %s: %s", page.url, exc)
            return False

    def _fill_text_fields(self, value: str, skip_types: set[str] | None = None) -> int:
        """Fill all text-like inputs with the given value. Returns count filled."""
        skip = skip_types or {"submit", "button", "reset", "hidden", "file", "image"}
        filled = 0
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
            for element in inputs:
                tag = element.tag_name.lower()
                if tag == "select":
                    continue
                field_type = (element.get_attribute("type") or "text").lower()
                if field_type in skip:
                    continue
                if not element.is_displayed() or not element.is_enabled():
                    continue
                try:
                    element.clear()
                    element.send_keys(value)
                    filled += 1
                except Exception as exc:
                    logger.warning("Could not fill field: %s", exc)
        except Exception as exc:
            logger.warning("Error filling text fields: %s", exc)
        return filled

    def _submit_form(self) -> None:
        """Submit the first visible form on the page."""
        try:
            submit_btn = self.driver.find_elements(
                By.CSS_SELECTOR,
                "form button[type='submit'], form input[type='submit'], form button",
            )
            if submit_btn:
                submit_btn[0].click()
                return
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            if forms:
                forms[0].submit()
        except Exception as exc:
            logger.warning("Form submission failed: %s", exc)

    def _dismiss_alert_if_present(self) -> bool:
        """Dismiss any JavaScript alert and return True if one was present."""
        try:
            alert = self.driver.switch_to.alert
            alert.dismiss()
            return True
        except NoAlertPresentException:
            return False
        except Exception as exc:
            logger.warning("Error handling alert: %s", exc)
            return False

    def _page_has_validation_error(self) -> bool:
        """Check if page shows HTML5 or visible validation errors."""
        try:
            invalid_fields = self.driver.find_elements(By.CSS_SELECTOR, ":invalid")
            if invalid_fields:
                return True
            error_selectors = [
                ".error",
                ".invalid",
                ".validation-error",
                "[role='alert']",
                ".alert-danger",
                ".field-error",
            ]
            for selector in error_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if any(el.is_displayed() for el in elements):
                    return True
        except Exception as exc:
            logger.warning("Error checking validation: %s", exc)
        return False

    def _page_crashed_or_db_error(self) -> bool:
        """Detect server crashes or database error messages."""
        try:
            page_source = self.driver.page_source.lower()
            for pattern in DB_ERROR_PATTERNS:
                if pattern in page_source:
                    return True
            if self.driver.title and "error" in self.driver.title.lower():
                if "500" in page_source or "internal server" in page_source:
                    return True
        except Exception as exc:
            logger.warning("Error checking page crash state: %s", exc)
        return False

    def _test_empty_submission(self, page: PageData, form: FormData) -> TestResult | None:
        """Test form rejects empty submission."""
        start = time.perf_counter()
        test_id = self._next_test_id()
        steps = [
            "Navigate to page containing the form",
            "Clear all form fields",
            "Submit the form without entering data",
        ]

        if not self._navigate_to_form(page, form):
            return None

        self._fill_text_fields("")
        for element in self.driver.find_elements(By.CSS_SELECTOR, "input, textarea"):
            try:
                element.clear()
            except Exception:
                pass

        self._submit_form()
        time.sleep(0.5)

        has_validation = self._page_has_validation_error()
        still_on_page = form.action in self.driver.current_url or page.url in self.driver.current_url
        submitted_successfully = not has_validation and not still_on_page

        status = "FAIL" if submitted_successfully else "PASS"
        actual = (
            "Form submitted successfully with no data"
            if submitted_successfully
            else "Validation error displayed or form not submitted"
        )

        return TestResult(
            test_id=test_id,
            test_name=f"Empty submission — {form.action}",
            category="Functional",
            page_url=page.url,
            precondition="Form is accessible on the page",
            steps=steps,
            expected_result="Validation error appears when submitting empty form",
            actual_result=actual,
            status=status,
            severity="High",
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _test_invalid_email(self, page: PageData, form: FormData) -> TestResult | None:
        """Test email fields reject invalid format."""
        email_fields = [
            field_item
            for field_item in form.fields
            if field_item.field_type == "email"
            or "email" in field_item.name.lower()
        ]
        if not email_fields:
            return None

        start = time.perf_counter()
        test_id = self._next_test_id()

        if not self._navigate_to_form(page, form):
            return None

        for field_item in email_fields:
            selector = f"input[name='{field_item.name}'], input[type='email']"
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    element.clear()
                    element.send_keys(INVALID_EMAIL)
                except Exception as exc:
                    logger.warning("Could not fill email field: %s", exc)

        self._submit_form()
        time.sleep(0.5)

        has_validation = self._page_has_validation_error()
        status = "PASS" if has_validation else "FAIL"
        actual = (
            "Email validation error shown"
            if has_validation
            else "No email validation error for invalid format"
        )

        return TestResult(
            test_id=test_id,
            test_name=f"Invalid email format — {form.action}",
            category="Functional",
            page_url=page.url,
            precondition="Form contains email field",
            steps=[
                "Navigate to form",
                f"Enter invalid email: {INVALID_EMAIL}",
                "Submit form",
            ],
            expected_result="Email validation error shown",
            actual_result=actual,
            status=status,
            severity="Medium",
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _test_sql_injection(self, page: PageData, form: FormData) -> TestResult | None:
        """Test form handles SQL injection payloads safely."""
        text_fields = [
            field_item
            for field_item in form.fields
            if field_item.field_type
            in {"text", "search", "password", "textarea", "url", "tel"}
        ]
        if not text_fields:
            return None

        start = time.perf_counter()
        test_id = self._next_test_id()

        if not self._navigate_to_form(page, form):
            return None

        self._fill_text_fields(SQL_INJECTION_PAYLOAD)
        self._submit_form()
        time.sleep(0.5)

        crashed = self._page_crashed_or_db_error()
        status = "FAIL" if crashed else "PASS"
        actual = (
            "Page crash or database error detected after SQL injection payload"
            if crashed
            else "Form rejected payload or showed safe error"
        )

        return TestResult(
            test_id=test_id,
            test_name=f"SQL injection — {form.action}",
            category="Functional",
            page_url=page.url,
            precondition="Form contains text input fields",
            steps=[
                "Navigate to form",
                "Enter SQL injection payload into all text fields",
                "Submit form",
            ],
            expected_result="Form rejects or shows safe error without DB exposure",
            actual_result=actual,
            status=status,
            severity="Critical",
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _test_xss(self, page: PageData, form: FormData) -> TestResult | None:
        """Test form sanitizes XSS payloads."""
        text_fields = [
            field_item
            for field_item in form.fields
            if field_item.field_type
            in {"text", "search", "textarea", "url", "email", "password"}
        ]
        if not text_fields:
            return None

        start = time.perf_counter()
        test_id = self._next_test_id()

        if not self._navigate_to_form(page, form):
            return None

        self._fill_text_fields(XSS_PAYLOAD)
        alert_fired = False
        try:
            self._submit_form()
            time.sleep(0.5)
            alert_fired = self._dismiss_alert_if_present()
        except UnexpectedAlertPresentException:
            alert_fired = True
            self._dismiss_alert_if_present()

        script_in_dom = XSS_PAYLOAD.lower() in self.driver.page_source.lower()
        failed = alert_fired or script_in_dom
        status = "FAIL" if failed else "PASS"
        actual_parts = []
        if alert_fired:
            actual_parts.append("JavaScript alert fired")
        if script_in_dom:
            actual_parts.append("Unescaped script tag found in DOM")
        actual = "; ".join(actual_parts) if actual_parts else "Input appears sanitized"

        return TestResult(
            test_id=test_id,
            test_name=f"XSS injection — {form.action}",
            category="Functional",
            page_url=page.url,
            precondition="Form contains text input fields",
            steps=[
                "Navigate to form",
                f"Enter XSS payload: {XSS_PAYLOAD}",
                "Submit form",
            ],
            expected_result="Input is sanitized; no alert or unescaped script in DOM",
            actual_result=actual,
            status=status,
            severity="Critical",
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _test_long_text_overflow(self, page: PageData, form: FormData) -> TestResult | None:
        """Test form handles extremely long text input."""
        text_inputs = [
            field_item
            for field_item in form.fields
            if field_item.field_type in {"text", "search", "textarea", "email", "url"}
        ]
        if not text_inputs:
            return None

        start = time.perf_counter()
        test_id = self._next_test_id()
        long_text = "".join(
            random.choices(string.ascii_letters + string.digits, k=LONG_TEXT_LENGTH)
        )

        if not self._navigate_to_form(page, form):
            return None

        self._fill_text_fields(long_text)
        self._submit_form()
        time.sleep(0.5)

        crashed = self._page_crashed_or_db_error()
        layout_broken = False
        try:
            body_width = self.driver.execute_script(
                "return document.body.scrollWidth > window.innerWidth * 3;"
            )
            layout_broken = bool(body_width)
        except Exception as exc:
            logger.warning("Layout check failed: %s", exc)

        failed = crashed or layout_broken
        status = "FAIL" if failed else "PASS"
        actual = (
            "Page crash or layout break detected with long text input"
            if failed
            else "Page handled long text input without crash or layout break"
        )

        return TestResult(
            test_id=test_id,
            test_name=f"Long text overflow — {form.action}",
            category="Functional",
            page_url=page.url,
            precondition="Form contains text input fields",
            steps=[
                "Navigate to form",
                f"Enter {LONG_TEXT_LENGTH} character random string into text inputs",
                "Submit form",
            ],
            expected_result="Page handles long input without crash or layout break",
            actual_result=actual,
            status=status,
            severity="Low",
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _test_special_characters(self, page: PageData, form: FormData) -> TestResult | None:
        """Test form handles special characters safely."""
        text_fields = [
            field_item
            for field_item in form.fields
            if field_item.field_type in {"text", "search", "textarea", "password", "url"}
        ]
        if not text_fields:
            return None

        start = time.perf_counter()
        test_id = self._next_test_id()

        if not self._navigate_to_form(page, form):
            return None

        self._fill_text_fields(SPECIAL_CHARS)
        self._submit_form()
        time.sleep(0.5)

        crashed = self._page_crashed_or_db_error()
        status = "FAIL" if crashed else "PASS"
        actual = (
            "Page crash or unhandled server error with special characters"
            if crashed
            else "Form handled special characters without error"
        )

        return TestResult(
            test_id=test_id,
            test_name=f"Special characters — {form.action}",
            category="Functional",
            page_url=page.url,
            precondition="Form contains text input fields",
            steps=[
                "Navigate to form",
                f"Enter special characters: {SPECIAL_CHARS}",
                "Submit form",
            ],
            expected_result="No page crash or unhandled server error",
            actual_result=actual,
            status=status,
            severity="Medium",
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _run_link_test(self, link: str) -> None:
        """Check HTTP status of a link."""
        if not hasattr(self, "_link_cache"):
            self._link_cache = {}

        start = time.perf_counter()
        test_id = self._next_test_id()

        if link in self._link_cache:
            status, severity, actual = self._link_cache[link]
            result = TestResult(
                test_id=test_id,
                test_name=f"Link check — {link[:60]}",
                category="Link",
                page_url=link,
                precondition="Link discovered during crawl (cached)",
                steps=["Retrieve cached HTTP verification result"],
                expected_result="HTTP 200 OK",
                actual_result=actual,
                status=status,
                severity=severity,
                screenshot_path=None,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
            self._record_result(result)
            return

        status = "PASS"
        severity = "Info"
        actual = "HTTP 200 OK"

        try:
            response = requests.head(link, timeout=10, allow_redirects=False)
            code = response.status_code

            if code in {301, 302, 303, 307, 308}:
                status = "WARNING"
                severity = "Medium"
                actual = f"HTTP {code} redirect"
            elif code == 404:
                status = "FAIL"
                severity = "High"
                actual = f"HTTP {code} Not Found"
            elif code >= 500:
                status = "FAIL"
                severity = "High"
                actual = f"HTTP {code} Server Error"
            elif code == 200:
                status = "PASS"
                severity = "Info"
                actual = f"HTTP {code} OK"
            else:
                status = "PASS"
                actual = f"HTTP {code}"
        except requests.RequestException:
            try:
                response = requests.get(link, timeout=10, allow_redirects=False)
                code = response.status_code
                if code in {301, 302}:
                    status = "WARNING"
                    severity = "Medium"
                    actual = f"HTTP {code} redirect (GET fallback)"
                elif code >= 400:
                    status = "FAIL"
                    severity = "High"
                    actual = f"HTTP {code} (GET fallback)"
                else:
                    actual = f"HTTP {code} (GET fallback)"
            except requests.RequestException as get_exc:
                logger.warning("Link check failed for %s: %s", link, get_exc)
                status = "FAIL"
                severity = "High"
                actual = f"Request failed: {get_exc}"

        self._link_cache[link] = (status, severity, actual)

        result = TestResult(
            test_id=test_id,
            test_name=f"Link check — {link[:60]}",
            category="Link",
            page_url=link,
            precondition="Link discovered during crawl",
            steps=["Send HTTP HEAD request to link", "Verify response status code"],
            expected_result="HTTP 200 OK",
            actual_result=actual,
            status=status,
            severity=severity,
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )
        self._record_result(result)

    def _run_performance_test(self, page: PageData) -> None:
        """Evaluate page load time against thresholds."""
        start = time.perf_counter()
        test_id = self._next_test_id()
        load_ms = page.load_time_ms

        if load_ms > 7000:
            status = "FAIL"
            severity = "High"
            actual = f"Page load time: {load_ms:.0f}ms (exceeds 7000ms threshold)"
        elif load_ms > 3000:
            status = "WARNING"
            severity = "Medium"
            actual = f"Page load time: {load_ms:.0f}ms (exceeds 3000ms threshold)"
        else:
            status = "PASS"
            severity = "Info"
            actual = f"Page load time: {load_ms:.0f}ms (within acceptable range)"

        result = TestResult(
            test_id=test_id,
            test_name=f"Page load performance — {page.title or page.url}",
            category="Performance",
            page_url=page.url,
            precondition="Page was crawled and load time measured",
            steps=[
                "Navigate to page",
                "Measure domContentLoadedEventEnd - navigationStart",
                "Compare against performance thresholds",
            ],
            expected_result="Page load time <= 1500ms",
            actual_result=actual,
            status=status,
            severity=severity,
            screenshot_path=None,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )
        self._record_result(result)

    def _run_security_header_tests(self, page: PageData) -> None:
        """Check security headers for each page URL."""
        header_checks = [
            ("X-Frame-Options", "Medium", True),
            ("Content-Security-Policy", "High", True),
            ("X-Content-Type-Options", "Low", True),
            ("Strict-Transport-Security", "High", False),
        ]

        try:
            response = requests.get(page.url, timeout=10)
            headers = {key.lower(): value for key, value in response.headers.items()}
        except requests.RequestException as exc:
            logger.warning("Security header fetch failed for %s: %s", page.url, exc)
            return

        is_https = urlparse(page.url).scheme == "https"

        for header_name, severity, always_check in header_checks:
            if header_name == "Strict-Transport-Security" and not is_https:
                continue
            if not always_check and not is_https:
                continue

            start = time.perf_counter()
            test_id = self._next_test_id()
            header_present = header_name.lower() in headers

            result = TestResult(
                test_id=test_id,
                test_name=f"Security header: {header_name} — {page.url}",
                category="Security",
                page_url=page.url,
                precondition=f"HTTP GET request to {page.url}",
                steps=[
                    f"Fetch HTTP headers for {page.url}",
                    f"Check for {header_name} header",
                ],
                expected_result=f"{header_name} header present",
                actual_result=(
                    f"{header_name} header present: {headers.get(header_name.lower(), 'MISSING')}"
                    if header_present
                    else f"{header_name} header is MISSING"
                ),
                status="PASS" if header_present else "FAIL",
                severity=severity if not header_present else "Info",
                screenshot_path=None,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
            self._record_result(result)
