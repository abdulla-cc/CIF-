# CIF: Crawl, Identify, Fix

A website accessibility auditor that **proves its fixes work**.

You give CIF a URL. It does five things:

1. **Crawls** the site politely, respecting robots.txt, rate limits and depth/page caps.
2. **Identifies** accessibility violations with axe-core in a headless browser.
3. **Fixes**: an LLM explains each issue in plain English and proposes a concrete HTML/CSS/ARIA fix.
4. **Verifies** each fix by applying it to the live DOM and re-running the check. A fix is labelled *verified* only if the violation is gone and nothing new broke.
5. **Judges alt text** with a vision model, because automated checkers only test that alt text *exists*, not that it describes the image.

> **Status:** early development.

## Honest limitations

- Automated testing finds only a portion of accessibility issues. A clean CIF report does **not** mean a site is accessible or compliant.
- Verification is DOM-level. It shows the patched page passes the automated check for that rule, not that your source code is fixed.
- Only audit websites you are authorised to test.

## Evaluation

Measured results (detection rate, fix verification rate, alt-text judgment quality, cost and latency per page) will be published here from the evaluation harness. Every number will be traceable to a committed results file.

## Tech stack

FastAPI · Playwright + axe-core · Google Gemini API · SQLite (SQLAlchemy) · React + Vite + TypeScript
