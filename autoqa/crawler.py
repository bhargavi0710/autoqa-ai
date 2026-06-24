"""Website crawler module for AutoQA AI."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


@dataclass
class FieldData:
    """Represents a single form field."""

    name: str
    field_type: str
    required: bool
    placeholder: str


@dataclass
class FormData:
    """Represents an HTML form and its fields."""

    action: str
    method: str
    fields: list[FieldData] = field(default_factory=list)


@dataclass
class PageData:
    """Collected data from a crawled page."""

    url: str
    title: str
    load_time_ms: float
    forms: list[FormData]
    links: list[str]
    raw_html: str


class SiteCrawler:
    """Crawls a website using Selenium and collects page data."""

    def __init__(self, base_url: str, driver: WebDriver, max_pages: int = 20) -> None:
        """Initialize the crawler with base URL, driver, and page limit."""
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        self.base_domain = parsed.netloc
        self.driver = driver
        self.max_pages = max_pages

    def crawl(self) -> list[PageData]:
        """Crawl the site starting from base_url and return collected page data."""
        visited: set[str] = set()
        queue: list[str] = [self.base_url]
        pages: list[PageData] = []

        while queue and len(pages) < self.max_pages:
            current_url = queue.pop(0)
            normalized = self._normalize_url(current_url)

            if normalized in visited:
                continue
            visited.add(normalized)

            try:
                print(f"  [{len(pages) + 1}/{self.max_pages}] Crawling: {normalized} ...", flush=True)
                page_data = self._crawl_page(normalized)
                pages.append(page_data)

                for link in page_data.links:
                    if link not in visited and link not in queue:
                        if len(pages) + len(queue) < self.max_pages * 2:
                            queue.append(link)
            except WebDriverException as exc:
                logger.warning("Failed to crawl page %s: %s", normalized, exc)
            except Exception as exc:
                logger.warning("Unexpected error crawling %s: %s", normalized, exc)

        return pages

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragment and trailing slash."""
        parsed = urlparse(url)
        normalized = parsed._replace(fragment="").geturl()
        return normalized.rstrip("/") or normalized

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as base URL."""
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return True
            return parsed.netloc == self.base_domain
        except Exception as exc:
            logger.warning("Error checking domain for %s: %s", url, exc)
            return False

    def _crawl_page(self, url: str) -> PageData:
        """Visit a single page and extract its data."""
        start = time.perf_counter()
        self.driver.get(url)

        load_time_ms = self._get_load_time_ms()
        if load_time_ms == 0.0:
            load_time_ms = (time.perf_counter() - start) * 1000

        title = self.driver.title or ""
        raw_html = self.driver.page_source
        forms = self._extract_forms(url)
        links = self._extract_links(url)

        return PageData(
            url=url,
            title=title,
            load_time_ms=load_time_ms,
            forms=forms,
            links=links,
            raw_html=raw_html,
        )

    def _get_load_time_ms(self) -> float:
        """Measure page load time using window.performance.timing."""
        try:
            load_time = self.driver.execute_script(
                """
                var timing = window.performance.timing;
                if (timing && timing.domContentLoadedEventEnd && timing.navigationStart) {
                    return timing.domContentLoadedEventEnd - timing.navigationStart;
                }
                return 0;
                """
            )
            return float(load_time) if load_time else 0.0
        except Exception as exc:
            logger.warning("Could not measure load time: %s", exc)
            return 0.0

    def _extract_forms(self, page_url: str) -> list[FormData]:
        """Extract all forms and their fields from the current page."""
        forms: list[FormData] = []
        try:
            form_elements = self.driver.find_elements(By.TAG_NAME, "form")
            for form_el in form_elements:
                action = form_el.get_attribute("action") or page_url
                action = urljoin(page_url, action)
                method = (form_el.get_attribute("method") or "get").lower()
                fields = self._extract_form_fields(form_el)
                if fields:
                    forms.append(FormData(action=action, method=method, fields=fields))
        except Exception as exc:
            logger.warning("Error extracting forms from %s: %s", page_url, exc)
        return forms

    def _extract_form_fields(self, form_el) -> list[FieldData]:
        """Extract input, select, textarea, and button fields from a form."""
        fields: list[FieldData] = []
        selectors = "input, select, textarea, button"
        try:
            for element in form_el.find_elements(By.CSS_SELECTOR, selectors):
                tag = element.tag_name.lower()
                name = element.get_attribute("name") or element.get_attribute("id") or ""
                if tag == "button":
                    field_type = element.get_attribute("type") or "button"
                elif tag == "select":
                    field_type = "select"
                elif tag == "textarea":
                    field_type = "textarea"
                else:
                    field_type = element.get_attribute("type") or "text"

                required_attr = element.get_attribute("required")
                required = required_attr is not None and required_attr != "false"
                placeholder = element.get_attribute("placeholder") or ""

                fields.append(
                    FieldData(
                        name=name or f"unnamed_{len(fields)}",
                        field_type=field_type.lower(),
                        required=required,
                        placeholder=placeholder,
                    )
                )
        except Exception as exc:
            logger.warning("Error extracting form fields: %s", exc)
        return fields

    def _extract_links(self, page_url: str) -> list[str]:
        """Extract same-domain links from the current page."""
        links: list[str] = []
        try:
            hrefs = self.driver.execute_script(
                """
                var anchors = document.querySelectorAll('a[href]');
                var hrefs = [];
                for (var i = 0; i < anchors.length; i++) {
                    hrefs.push(anchors[i].href);
                }
                return hrefs;
                """
            )
            if hrefs:
                for href in hrefs:
                    if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                        continue
                    normalized = self._normalize_url(href)
                    if self._is_same_domain(normalized) and normalized not in links:
                        links.append(normalized)
        except Exception as exc:
            logger.warning("Error extracting links from %s: %s", page_url, exc)
        return links
