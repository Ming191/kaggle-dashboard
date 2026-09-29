from pathlib import Path

from app.kaggle_client import load_accounts, parse_hours, parse_quota_rows


def test_parse_hours():
    assert parse_hours("5.00h") == 5.0
    assert parse_hours("0.25h") == 0.25
    assert parse_hours(3) == 3.0


def test_parse_quota_rows():
    rows = [
        {
            "resource": "GPU",
            "used": "5.00h",
            "remaining": "25.00h",
            "total": "30.00h",
            "refreshAt": "2026-06-01T00:00:00+00:00",
        },
        {
            "resource": "TPU",
            "used": "2.00h",
            "remaining": "18.00h",
            "total": "20.00h",
            "refreshAt": "2026-06-01T00:00:00+00:00",
        },
    ]

    quota = parse_quota_rows(rows)

    assert quota["GPU"].used_hours == 5
    assert quota["GPU"].remaining_hours == 25
    assert quota["GPU"].total_hours == 30
    assert quota["TPU"].remaining_hours == 18


def test_auto_discover_accounts(tmp_path: Path):
    (tmp_path / "student-b").mkdir()
    (tmp_path / "student-a").mkdir()
    (tmp_path / ".hidden").mkdir()

    accounts = load_accounts(str(tmp_path / "missing.json"), str(tmp_path))

    assert [account.id for account in accounts] == ["student-a", "student-b"]
