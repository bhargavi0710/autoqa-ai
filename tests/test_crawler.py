"""Unit tests for the SiteCrawler module."""

from unittest.mock import MagicMock, patch

import pytest

from autoqa.crawler import FieldData, FormData, PageData, SiteCrawler


@pytest.fixture
def mock_driver():
    """Create a mock Selenium WebDriver."""
    driver = MagicMock()
    driver.title = "Test Page"
    driver.page_source = "<html><body><a href='/page2'>Link</a></body></html>"
    driver.execute_script.return_value = 850.0
    return driver


@pytest.fixture
def mock_form_element():
    """Create a mock form element with fields."""
    form_el = MagicMock()
    input_el = MagicMock()
    input_el.tag_name = "input"
    input_el.get_attribute.side_effect = lambda attr: {
        "name": "username",
        "type": "text",
        "required": None,
        "placeholder": "Enter username",
    }.get(attr)
    form_el.get_attribute.side_effect = lambda attr: {
        "action": "/submit",
        "method": "post",
    }.get(attr)
    form_el.find_elements.return_value = [input_el]
    return form_el


@pytest.fixture
def mock_link_element():
    """Create a mock anchor element."""
    anchor = MagicMock()
    anchor.get_attribute.return_value = "https://example.com/page2"
    return anchor


class TestSiteCrawler:
    """Tests for SiteCrawler crawl behavior."""

    def test_crawl_returns_page_data_objects(
        self, mock_driver, mock_form_element, mock_link_element
    ):
        """Test that crawl() returns a list of PageData objects."""
        mock_driver.find_elements.side_effect = lambda by, value: {
            "form": [mock_form_element],
            "a[href]": [mock_link_element],
        }.get(value.split("[")[0].replace("tag name", "form") if "form" in str(value) else "a", [])

        def find_elements_side_effect(by, value):
            if value == "form":
                return [mock_form_element]
            if value == "a[href]":
                return [mock_link_element]
            if "input" in value:
                return mock_form_element.find_elements.return_value
            return []

        mock_driver.find_elements.side_effect = find_elements_side_effect

        crawler = SiteCrawler("https://example.com", mock_driver, max_pages=1)
        pages = crawler.crawl()

        assert isinstance(pages, list)
        assert len(pages) >= 1
        assert isinstance(pages[0], PageData)
        assert pages[0].url == "https://example.com"
        assert pages[0].title == "Test Page"

    def test_crawl_stops_at_max_pages(self, mock_driver):
        """Test that crawl() stops at max_pages limit."""
        mock_driver.find_elements.return_value = []

        with patch.object(SiteCrawler, "_crawl_page") as mock_crawl_page:
            mock_crawl_page.side_effect = lambda url: PageData(
                url=url,
                title="Page",
                load_time_ms=100.0,
                forms=[],
                links=[f"https://example.com/page{i}" for i in range(10)],
                raw_html="<html></html>",
            )

            crawler = SiteCrawler("https://example.com", mock_driver, max_pages=3)
            pages = crawler.crawl()
            assert len(pages) == 3

    def test_crawl_skips_different_domain_links(self, mock_driver):
        """Test that crawl() skips links from different domains."""
        crawler = SiteCrawler("https://example.com", mock_driver, max_pages=5)

        assert crawler._is_same_domain("https://example.com/about") is True
        assert crawler._is_same_domain("https://other.com/page") is False
        assert crawler._is_same_domain("/relative") is True

    def test_page_load_time_is_float(self, mock_driver, mock_form_element):
        """Test that page load time is captured as a float."""
        mock_driver.find_elements.side_effect = lambda by, value: (
            [mock_form_element] if "form" in str(value) else []
        )
        mock_driver.execute_script.return_value = 1234.5

        crawler = SiteCrawler("https://example.com", mock_driver, max_pages=1)
        pages = crawler.crawl()

        assert len(pages) == 1
        assert isinstance(pages[0].load_time_ms, float)
        assert pages[0].load_time_ms == 1234.5

    def test_form_data_structure(self):
        """Test FormData and FieldData dataclass structure."""
        field = FieldData(
            name="email",
            field_type="email",
            required=True,
            placeholder="Enter email",
        )
        form = FormData(action="/login", method="post", fields=[field])

        assert form.action == "/login"
        assert form.method == "post"
        assert len(form.fields) == 1
        assert form.fields[0].name == "email"
