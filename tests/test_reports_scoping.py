"""Saved Reports library — the access-control guarantee that a user can only
see and delete their OWN reports (High-Stakes Oversight). Runs against a
throwaway SQLite file, never the real reports.db."""
from datetime import datetime, timezone

import pytest
from src import config, reports


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPORTS_DB_PATH", str(tmp_path / "reports.db"))
    reports.init_db()


def test_save_and_list_scoped_to_user(clean_db):
    rid = reports.save_report("alice", "Q3 returns", "body")
    assert reports.list_reports("alice")[0]["id"] == rid
    assert reports.list_reports("bob") == []          # bob sees nothing of alice's


def test_get_by_id_only_for_owner(clean_db):
    rid = reports.save_report("alice", "t", "body")
    assert reports.get_by_id("alice", rid)["id"] == rid
    assert reports.get_by_id("bob", rid) is None       # cannot read another's report


def test_delete_scoped_to_owner(clean_db):
    rid = reports.save_report("alice", "t", "body")
    assert reports.delete_reports("bob", [rid]) == 0   # bob can't delete alice's
    assert reports.get_by_id("alice", rid) is not None # still there
    assert reports.delete_reports("alice", [rid]) == 1 # owner can
    assert reports.get_by_id("alice", rid) is None


def test_find_by_keyword_scoped(clean_db):
    reports.save_report("alice", "Nike returns", "about Nike")
    reports.save_report("alice", "Adidas", "about Adidas")
    reports.save_report("bob", "Nike stuff", "nike for bob")
    hits = reports.find_reports("alice", keyword="Nike")
    assert len(hits) == 1                              # bob's Nike report excluded
    assert hits[0]["title"] == "Nike returns"


def test_find_by_date(clean_db):
    reports.save_report("alice", "today report", "body")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert len(reports.find_reports("alice", on_date=today)) == 1
    assert reports.find_reports("alice", on_date="2000-01-01") == []
