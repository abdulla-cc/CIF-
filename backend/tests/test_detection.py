from playwright.sync_api import sync_playwright

from cif.eval.detection import evaluate, match_nodes

PAGE = """<!doctype html><html lang="en"><head><title>t</title></head><body>
<div id="box"><a id="inner" href="#">x</a><h4 id="nested">h</h4></div><p id="other">y</p>
</body></html>"""

BUGS = [
    {"id": "CONTAINER", "selector": "#box"},
    {"id": "NESTED", "selector": "#nested"},
    {"id": "HEAD", "selector": "head"},
    {"id": "ROOT", "selector": "html"},
]


def test_matching_rules():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(PAGE)
        targets = [["#inner"], ["#nested"], ["#other"], ["html"], ["iframe", "#x"]]
        matches = match_nodes(page, BUGS, targets)
        browser.close()

    assert matches == [
        ["CONTAINER"],      # node inside a container bug's element
        ["NESTED"],         # a bug's own element counts only for that bug, not its container
        [],                 # unrelated node: an html-selector bug must not swallow it
        ["HEAD", "ROOT"],   # document root: matches document-level bugs
        [],                 # node inside an iframe: never matched to a top-level bug
    ]


def test_harness_on_seeded_site(site_url):
    result = evaluate(site_url)
    status = {b["id"]: b["status"] for b in result["bugs"]}

    assert status["B33"] == "detected"  # JavaScript-rendered bug
    assert status["B13"] == "missed"    # file-name alt text: automatable, but axe has no rule
    assert result["recall"]["all"]["total"] == 33
    assert not any(u["page"] == "accessibility.html" for u in result["unplanned_violations"])
