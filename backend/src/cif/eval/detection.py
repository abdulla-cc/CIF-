"""Detection metrics: compare axe findings on the seeded test site with ground_truth.json.

Usage: python -m cif.eval.detection   (writes eval/results/detection_seeded.json)
"""

import json
import subprocess
import threading
from contextlib import contextmanager
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from cif.scan.axe import open_page, scan_page

REPO = Path(__file__).resolve().parents[4]
SITE = REPO / "testsite"
RESULTS = REPO / "eval" / "results" / "detection_seeded.json"

# Which bug IDs does each flagged node belong to? Runs in the page so DOM identity is exact.
MATCH_JS = """([bugs, targets]) => {
  const root = document.documentElement;
  const bugEls = bugs.map(b => [b.id, b.selector, document.querySelector(b.selector)]);
  return targets.map(target => {
    if (target.length !== 1) return [];  // node inside an iframe, not a top-level element
    const el = document.querySelector(target[0]);
    const exact = bugEls.filter(([, sel, bugEl]) =>
      bugEl === el || (sel === "head" && el === root));  // document-level issues are reported on <html>
    if (exact.length) return exact.map(([id]) => id);
    // Container bugs only claim nodes that are not some other bug's own element.
    return bugEls.filter(([, , bugEl]) => bugEl && bugEl !== root && bugEl.contains(el))
      .map(([id]) => id);
  });
}"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextmanager
def serve(directory: Path = SITE):
    """Serve a directory on a free local port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=directory))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def match_nodes(page, bugs: list[dict], targets: list[list[str]]) -> list[list[str]]:
    return page.evaluate(MATCH_JS, [bugs, targets])


def _recall(bugs: list[dict], statuses: tuple[str, ...]) -> dict:
    hit = sum(b["status"] in statuses for b in bugs)
    return {"found": hit, "total": len(bugs), "rate": round(hit / len(bugs), 3) if bugs else None}


def evaluate(site_url: str) -> dict:
    truth = json.loads((SITE / "ground_truth.json").read_text(encoding="utf-8"))
    pages = [p for p, split in truth["pages"].items() if split in {"dev", "heldout", "clean"}]
    bugs = [dict(b, split=truth["pages"][b["page"]], status="missed", rules=[]) for b in truth["bugs"]]
    unplanned = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for page_name in pages:
            page = open_page(browser, f"{site_url}/{page_name}")
            scan = scan_page(page)
            page_bugs = [b for b in bugs if b["page"] == page_name]
            for kind, status in (("violations", "detected"), ("incomplete", "review")):
                for rule in scan[kind]:
                    targets = [n["target"] for n in rule["nodes"]]
                    for target, ids in zip(targets, match_nodes(page, page_bugs, targets)):
                        for bug in (b for b in page_bugs if b["id"] in ids):
                            bug["rules"].append(rule["rule"])
                            if bug["status"] != "detected":
                                bug["status"] = status
                        if not ids:
                            unplanned.append({"page": page_name, "kind": kind, "rule": rule["rule"],
                                              "group": rule["group"], "target": target})
            page.context.close()
        chromium = browser.version
        browser.close()

    flagged = [b for b in bugs if b["expected_axe_rule"]]
    return {
        "meta": {
            "date": date.today().isoformat(),
            "axe_version": scan["axe_version"],
            "chromium": chromium,
            "git": subprocess.run(["git", "describe", "--always", "--dirty"], check=False,
                                  cwd=REPO, capture_output=True, text=True).stdout.strip(),
        },
        "recall": {
            "all": _recall(bugs, ("detected",)),
            "all_including_review": _recall(bugs, ("detected", "review")),
            "automatable": _recall([b for b in bugs if b["automatable"]], ("detected",)),
            "not_automatable": _recall([b for b in bugs if not b["automatable"]], ("detected",)),
            "dev": _recall([b for b in bugs if b["split"] == "dev"], ("detected",)),
            "heldout": _recall([b for b in bugs if b["split"] == "heldout"], ("detected",)),
        },
        "rule_predictions_correct": _recall(
            [dict(b, status="hit" if b["expected_axe_rule"] in b["rules"] else "miss") for b in flagged],
            ("hit",)),
        "unplanned_violations": [u for u in unplanned if u["kind"] == "violations"],
        "unplanned_review_items": [u for u in unplanned if u["kind"] == "incomplete"],
        "bugs": [{k: b[k] for k in ("id", "page", "split", "automatable", "expected_axe_rule",
                                    "status", "rules")} for b in bugs],
    }


def main() -> None:
    with serve() as site_url:
        result = evaluate(site_url)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"axe {result['meta']['axe_version']} | Chromium {result['meta']['chromium']} | "
          f"git {result['meta']['git']}\n")
    print(f"{'Recall':28} found / total   rate")
    for name, r in result["recall"].items():
        print(f"{name:28} {r['found']:>5} / {r['total']:<5}  {r['rate']:.0%}")
    p = result["rule_predictions_correct"]
    print(f"{'rule predictions correct':28} {p['found']:>5} / {p['total']:<5}  {p['rate']:.0%}")
    print(f"\nUnplanned violations: {len(result['unplanned_violations'])}, "
          f"unplanned review items: {len(result['unplanned_review_items'])}")
    for u in result["unplanned_violations"] + result["unplanned_review_items"]:
        print(f"  {u['kind']:10} {u['page']:20} {u['rule']:22} {u['target']}")
    missed = [b["id"] for b in result["bugs"] if b["status"] == "missed"]
    print(f"\nMissed: {', '.join(missed) or 'none'}")
    print(f"Written to {RESULTS.relative_to(REPO)}")


if __name__ == "__main__":
    main()
