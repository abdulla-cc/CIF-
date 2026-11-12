"""Run axe-core on a web page inside headless Chromium."""

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

AXE_JS = (Path(__file__).parent / "vendor" / "axe.min.js").read_text(encoding="utf-8")
WCAG_TAGS = {"wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"}
RUN_OPTIONS = {"runOnly": {"type": "tag", "values": [*sorted(WCAG_TAGS), "best-practice"]}}


def _rule(result: dict) -> dict:
    return {
        "rule": result["id"],
        "group": "wcag" if WCAG_TAGS & set(result["tags"]) else "best-practice",
        "impact": result["impact"],
        "help": result["help"],
        "help_url": result["helpUrl"],
        "nodes": [
            {"target": n["target"], "html": n["html"], "summary": n.get("failureSummary")}
            for n in result["nodes"]
        ],
    }


def scan_page(page: Page) -> dict:
    """Run axe on an already-loaded page (axe must have been added as an init script)."""
    raw = page.evaluate("options => axe.run(document, options)", RUN_OPTIONS)
    return {
        "url": raw["url"],
        "axe_version": raw["testEngine"]["version"],
        "violations": [_rule(r) for r in raw["violations"]],
        "incomplete": [_rule(r) for r in raw["incomplete"]],
    }


def open_page(browser, url: str) -> Page:
    # Init scripts run in every frame and are not blocked by a site's Content Security Policy.
    context = browser.new_context()
    context.add_init_script(script=AXE_JS)
    page = context.new_page()
    page.goto(url, wait_until="load")
    return page


def scan_url(url: str) -> dict:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            return scan_page(open_page(browser, url))
        finally:
            browser.close()
