from cif.scan.axe import scan_url


def _flagged(result: dict) -> set[tuple[str, str]]:
    return {
        (rule["rule"], node["target"][-1])
        for rule in result["violations"]
        for node in rule["nodes"]
    }


def test_clean_page_has_no_violations(site_url):
    result = scan_url(f"{site_url}/accessibility.html")

    assert result["violations"] == []
    assert result["axe_version"] == "4.14.0"


def test_scanner_sees_javascript_rendered_dom(site_url):
    # #share-btn does not exist in pricing.html's source; JavaScript adds it after load.
    assert ("button-name", "#share-btn") in _flagged(scan_url(f"{site_url}/pricing.html"))


def test_support_pages_inside_iframes_add_no_violations(site_url):
    flagged = _flagged(scan_url(f"{site_url}/gallery.html"))

    assert ("frame-title", "#store-map") in flagged
    assert not any(rule == "landmark-unique" for rule, _ in flagged)
