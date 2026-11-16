"""Module catalogue and official resources tests."""
from __future__ import annotations

from .conftest import client


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_modules_lists_all_four() -> None:
    resp = client.get("/api/modules")
    assert resp.status_code == 200
    slugs = [item["slug"] for item in resp.json()]
    assert slugs == ["listening", "reading", "writing", "speaking"]
    for item in resp.json():
        assert item["time_minutes"]
        assert item["questions"]
        assert item["description"]
        assert "Practice available" in item["status"]


def test_module_detail() -> None:
    resp = client.get("/api/modules/listening")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Listening"
    assert "40 questions" in body["questions"]


def test_module_unknown_is_404() -> None:
    assert client.get("/api/modules/grammar").status_code == 404


def test_resources_are_official_links_only() -> None:
    resp = client.get("/api/resources")
    assert resp.status_code == 200
    links = resp.json()
    assert len(links) >= 4
    for link in links:
        assert link["url"].startswith("https://"), link
        assert link["title"] and link["description"] and link["provider"]
    hosts = {link["url"] for link in links}
    assert any("ielts.org" in url for url in hosts)
    assert any("britishcouncil.org" in url for url in hosts)
    assert any("idp.com" in url for url in hosts)
    # No Cambridge book content, no file downloads, no mirrors.
    assert not any("cambridge" in url.lower() for url in hosts)
    assert not any(url.endswith(".pdf") for url in hosts)
