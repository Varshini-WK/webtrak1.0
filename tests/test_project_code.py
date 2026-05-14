from app.domain.project_code import format_auto_project_code, slug_from_label


def test_slug_from_label_normalizes() -> None:
    assert slug_from_label("  Acme & Co.  ") == "ACME_CO"


def test_format_auto_project_code() -> None:
    assert format_auto_project_code(1, "Acme") == "P001_ACME"
    assert format_auto_project_code(42, "Big Client LLC") == "P042_BIG_CLIENT_LLC"
