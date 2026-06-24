"""AutoQA AI — CLI entry point."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from colorama import Fore, Style, init
from dotenv import load_dotenv

from autoqa.accessibility import AccessibilityTester
from autoqa.ai_analyzer import AIAnalyzer
from autoqa.crawler import SiteCrawler
from autoqa.reporter import ReportGenerator
from autoqa.tester import AutoTester, TestResult
from autoqa.utils import (
    create_output_dirs,
    get_failed_test_ids,
    load_json_report,
    setup_driver,
)

init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def print_banner(url: str) -> None:
    """Print the AutoQA AI startup banner."""
    banner = f"""
{Fore.CYAN}+----------------------------------------------------------+
|              AutoQA AI v1.0                              |
|     AI-Powered Automated QA Testing Tool                 |
+----------------------------------------------------------+{Style.RESET_ALL}
{Fore.CYAN}Target URL:{Style.RESET_ALL} {url}
"""
    try:
        print(banner)
    except UnicodeEncodeError:
        # Fallback if standard print fails for any other unicode characters
        print(banner.encode('ascii', errors='replace').decode('ascii'))


def print_test_result(result: TestResult) -> None:
    """Print a single test result with color-coded status."""
    if result.status == "PASS":
        status_color = Fore.GREEN
    elif result.status == "FAIL":
        status_color = Fore.RED
    else:
        status_color = Fore.YELLOW

    print(
        f"  {result.test_id} | {result.test_name[:60]:<60} "
        f"{status_color}{result.status}{Style.RESET_ALL}"
    )


def print_summary_table(results: list[TestResult]) -> None:
    """Print a summary table of test results."""
    total = len(results)
    passed = sum(1 for result in results if result.status == "PASS")
    failed = sum(1 for result in results if result.status == "FAIL")
    critical = sum(1 for result in results if result.severity == "Critical")
    high = sum(1 for result in results if result.severity == "High")
    medium = sum(1 for result in results if result.severity == "Medium")
    low = sum(1 for result in results if result.severity == "Low")

    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"  TEST SUMMARY")
    print(f"{'=' * 60}{Style.RESET_ALL}")
    print(f"  {'Total Tests:':<20} {total}")
    print(f"  {Fore.GREEN}{'Passed:':<20} {passed}{Style.RESET_ALL}")
    print(f"  {Fore.RED}{'Failed:':<20} {failed}{Style.RESET_ALL}")
    print(f"  {Fore.RED}{'Critical Bugs:':<20} {critical}{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}{'High Bugs:':<20} {high}{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}{'Medium Bugs:':<20} {medium}{Style.RESET_ALL}")
    print(f"  {'Low Bugs:':<20} {low}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")


def renumber_test_ids(results: list[TestResult]) -> None:
    """Renumber test IDs sequentially across combined result sets."""
    for index, result in enumerate(results, start=1):
        result.test_id = f"TC-{index:03d}"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AutoQA AI — AI-powered automated QA testing tool"
    )
    parser.add_argument("--url", required=True, help="Target website URL")
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run browser in headless mode (default: True)",
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox"],
        default="chrome",
        help="Browser to use (default: chrome)",
    )
    parser.add_argument(
        "--retest",
        type=str,
        default=None,
        help="Path to a previous JSON report to re-run only failed tests",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export bug report to CSV after run",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip Gemini AI calls (for offline use)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./reports",
        help="Directory to save reports and screenshots (default: ./reports)",
    )
    return parser.parse_args()


def main() -> int:
    """Run the AutoQA AI scan pipeline."""
    load_dotenv()
    args = parse_args()

    print_banner(args.url)
    scan_start = time.perf_counter()

    output_path, _ = create_output_dirs(args.output_dir)

    retest_names: set[str] = set()
    if args.retest:
        try:
            report = load_json_report(args.retest)
            retest_names = {
                entry["test_name"]
                for entry in report.get("results", [])
                if entry.get("status") == "FAIL"
            }
            failed_ids = get_failed_test_ids(report)
            print(
                f"{Fore.YELLOW}Retest mode: re-running {len(failed_ids)} "
                f"previously failed tests{Style.RESET_ALL}"
            )
        except Exception as exc:
            logger.error("Failed to load retest report %s: %s", args.retest, exc)
            return 1

    api_key = None
    if not args.no_ai:
        import os

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            api_key = None
            print(
                f"{Fore.YELLOW}GROQ_API_KEY not set — skipping AI analysis{Style.RESET_ALL}"
            )

    driver = None
    try:
        print(f"{Fore.CYAN}Initializing {args.browser} WebDriver...{Style.RESET_ALL}")
        driver = setup_driver(browser=args.browser, headless=args.headless)

        print(f"{Fore.CYAN}Crawling website...{Style.RESET_ALL}")
        crawler = SiteCrawler(args.url, driver, max_pages=20)
        pages = crawler.crawl()
        print(f"{Fore.CYAN}Crawled {len(pages)} pages{Style.RESET_ALL}")

        print(f"{Fore.CYAN}Running automated tests...{Style.RESET_ALL}")
        tester = AutoTester(driver, pages, str(output_path))
        results = tester.run_all_tests()

        print(f"{Fore.CYAN}Running accessibility tests...{Style.RESET_ALL}")
        accessibility = AccessibilityTester(driver, pages, str(output_path))
        a11y_results = accessibility.run()
        results.extend(a11y_results)

        if retest_names:
            results = [result for result in results if result.test_name in retest_names]

        renumber_test_ids(results)

        print(f"\n{Fore.CYAN}Test Results:{Style.RESET_ALL}")
        for result in results:
            print_test_result(result)

        analyzer = AIAnalyzer(api_key)
        results = analyzer.enhance_bug_report(results)
        executive_summary = analyzer.generate_executive_summary(results)

        scan_duration = time.perf_counter() - scan_start

        print(f"{Fore.CYAN}Generating reports...{Style.RESET_ALL}")
        reporter = ReportGenerator(
            results=results,
            target_url=args.url,
            output_dir=str(output_path),
            executive_summary=executive_summary,
            browser=args.browser,
            scan_duration_seconds=scan_duration,
        )

        html_path = reporter.generate_html()
        json_path = reporter.generate_json()
        print(f"{Fore.GREEN}HTML report: {html_path}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}JSON report: {json_path}{Style.RESET_ALL}")

        if args.export_csv:
            csv_path = reporter.generate_csv()
            print(f"{Fore.GREEN}CSV report: {csv_path}{Style.RESET_ALL}")

        print_summary_table(results)

        failed_count = sum(1 for result in results if result.status == "FAIL")
        return 1 if failed_count > 0 else 0

    except Exception as exc:
        logger.error("AutoQA scan failed: %s", exc, exc_info=True)
        print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}")
        return 1
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as exc:
                logger.warning("Failed to quit WebDriver: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
