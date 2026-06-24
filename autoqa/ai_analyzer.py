"""AI-powered bug report enhancement using Groq (free, unlimited)."""

from __future__ import annotations

import json
import logging
import re
import time

from autoqa.tester import TestResult

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Enhances test results with AI-generated summaries using Groq."""

    def __init__(self, api_key: str | None) -> None:
        """Configure Groq client if API key is provided."""
        self.client = None
        if api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=api_key)
                logger.info("Groq AI initialized successfully")
            except Exception as exc:
                logger.warning("Failed to initialize Groq: %s", exc)
                self.client = None

    def _clean_text(self, text: str) -> str:
        """Remove markdown formatting from AI response."""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'#{1,6}\s*', '', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        return text.strip()

    def enhance_bug_report(self, results: list[TestResult]) -> list[TestResult]:
        """Enhance Critical and High failed tests with AI-generated summaries."""
        if self.client is None:
            return results

        to_analyze = [
            r for r in results
            if r.status == "FAIL" and r.severity in ("Critical", "High")
        ]

        logger.info("AI analyzing %d Critical/High bugs...", len(to_analyze))

        for i, result in enumerate(to_analyze):
            try:
                logger.info(
                    "  AI analyzing [%d/%d] %s...",
                    i + 1, len(to_analyze), result.test_id
                )

                prompt = f"""You are a senior QA engineer writing professional bug reports.
Test failure details:
- Test Name: {result.test_name}
- Page URL: {result.page_url}
- Category: {result.category}
- Severity: {result.severity}
- Expected: {result.expected_result}
- Actual: {result.actual_result}

IMPORTANT: Respond with ONLY a raw JSON object. No markdown. No asterisks. No bold. No backticks. No explanation. Just pure JSON.
{{"summary": "one sentence professional bug summary",
  "recommended_fix": "plain English recommended fix for a developer",
  "business_impact": "one sentence explaining business impact"}}"""

                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.3
                )

                text = response.choices[0].message.content.strip()
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
                parsed = json.loads(text)

                result.summary = self._clean_text(parsed.get("summary", ""))
                result.recommended_fix = self._clean_text(parsed.get("recommended_fix", ""))
                result.business_impact = self._clean_text(parsed.get("business_impact", ""))

                if i < len(to_analyze) - 1:
                    time.sleep(1)

            except Exception as exc:
                logger.warning(
                    "AI enhancement failed for %s: %s", result.test_id, exc
                )

        return results

    def generate_executive_summary(self, results: list[TestResult]) -> str:
        """Generate an executive summary for stakeholders."""
        total = len(results)
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        critical = sum(1 for r in results if r.severity == "Critical")
        high = sum(1 for r in results if r.severity == "High")
        medium = sum(1 for r in results if r.severity == "Medium")
        low = sum(1 for r in results if r.severity == "Low")

        fallback = (
            f"AutoQA AI completed a scan and executed {total} automated tests "
            f"across 5 categories. {passed} tests passed and {failed} failed. "
            f"{critical} critical and {high} high severity issues were detected "
            f"that pose immediate risk to users or security."
        )

        if self.client is None:
            return fallback

        failed_names = [r.test_name for r in results if r.status == "FAIL"][:20]

        try:
            prompt = f"""Write a 3-paragraph executive summary for a non-technical stakeholder about a website QA scan.

IMPORTANT RULES:
- Do NOT use markdown formatting
- Do NOT use asterisks, bold, italics, or any special characters
- Do NOT add headers or titles
- Write plain sentences only
- Separate paragraphs with a blank line

Statistics:
- Total tests: {total}
- Passed: {passed}
- Failed: {failed}
- Critical: {critical}, High: {high}, Medium: {medium}, Low: {low}

Sample failed tests:
{chr(10).join(f'- {name}' for name in failed_names)}

Write in plain English. Cover overall health, key risks, and recommended next steps."""

            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            raw = response.choices[0].message.content.strip()
            return self._clean_text(raw)

        except Exception as exc:
            logger.warning("Executive summary generation failed: %s", exc)
            return fallback