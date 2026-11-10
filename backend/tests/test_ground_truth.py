import json
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

SITE = Path(__file__).resolve().parents[2] / "testsite"
TRUTH = json.loads((SITE / "ground_truth.json").read_text(encoding="utf-8"))
BUGS = TRUTH["bugs"]


def test_bug_ids_are_unique():
    ids = [bug["id"] for bug in BUGS]
    assert len(ids) == len(set(ids))


def test_bugs_are_only_on_dev_or_heldout_pages():
    for bug in BUGS:
        assert TRUTH["pages"][bug["page"]] in {"dev", "heldout"}, bug["id"]


def test_every_listed_page_exists():
    for page in TRUTH["pages"]:
        assert (SITE / page).is_file(), page


@pytest.mark.parametrize("bug", BUGS, ids=lambda bug: bug["id"])
def test_selector_matches_exactly_one_element(bug):
    html = (SITE / bug["page"]).read_text(encoding="utf-8")
    matches = BeautifulSoup(html, "html.parser").select(bug["selector"])
    # JS-rendered bugs must be absent from the source, proving the scanner reads the rendered DOM.
    assert len(matches) == (0 if bug["js_rendered"] else 1)


def test_site_files_do_not_leak_bug_ids():
    # The LLM will see page snippets later; any answer-key hint would inflate results.
    for path in SITE.rglob("*"):
        if path.suffix in {".html", ".css", ".svg", ".txt"}:
            assert not re.search(r"\bB\d{2}\b", path.read_text(encoding="utf-8")), path.name
