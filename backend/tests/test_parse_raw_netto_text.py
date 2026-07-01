from pathlib import Path

import pytest

from parsing.receipts.parse_raw_netto_text import detect_format, parse_receipt

DATA_DIR = Path(__file__).parent / "data/receipts_netto_raw_text"

EMAIL_FILES = {0, 1, 2, 3, 4, 5, 7, 8, 9, 19, 29, 33, 38, 40, 49}
EMPTY_FILES = {45, 46}


def _read(name: str) -> str:
    return (DATA_DIR / name).read_text()


def _non_empty_files():
    return [
        p for p in sorted(DATA_DIR.glob("*.txt"), key=lambda x: int(x.stem))
        if int(p.stem) not in EMPTY_FILES
    ]


@pytest.fixture
def non_empty_texts():
    return [p.read_text() for p in _non_empty_files()]


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------

def test_detect_format_classifies_all_non_empty():
    for p in _non_empty_files():
        expected = "email" if int(p.stem) in EMAIL_FILES else "ebon"
        assert detect_format(p.read_text()) == expected, p.name


# ---------------------------------------------------------------------------
# all non-empty receipts extract the core fields
# ---------------------------------------------------------------------------

def test_all_have_date(non_empty_texts):
    assert all(parse_receipt(t)["date"] is not None for t in non_empty_texts)


def test_all_have_time(non_empty_texts):
    assert all(parse_receipt(t)["time"] is not None for t in non_empty_texts)


def test_all_have_address(non_empty_texts):
    assert all(parse_receipt(t)["address"] is not None for t in non_empty_texts)


def test_all_have_total(non_empty_texts):
    assert all(parse_receipt(t)["total"] is not None for t in non_empty_texts)


def test_all_have_items(non_empty_texts):
    assert all(len(parse_receipt(t)["items"]) > 0 for t in non_empty_texts)


def test_empty_fixture_returns_empty_result():
    r = parse_receipt(_read("45.txt"))
    assert r["date"] is None
    assert r["total"] is None
    assert r["items"] == []


# ---------------------------------------------------------------------------
# email format — 0.txt
# ---------------------------------------------------------------------------

def test_email_format_detected():
    assert parse_receipt(_read("0.txt"))["format"] == "email"


def test_email_date_time():
    r = parse_receipt(_read("0.txt"))
    assert r["date"] == "17.02.2026"
    assert r["time"] == "10:24"


def test_email_address():
    r = parse_receipt(_read("0.txt"))
    assert r["address"] == "Oudenarder Str. 14, 13347 Berlin-Wedding"


def test_email_total():
    assert parse_receipt(_read("0.txt"))["total"] == "57,71"


def test_email_item_count():
    assert len(parse_receipt(_read("0.txt"))["items"]) == 32


def test_email_items_have_no_tax():
    assert all(i["tax"] is None for i in parse_receipt(_read("0.txt"))["items"])


def test_email_weighted_item_has_detail():
    items = parse_receipt(_read("0.txt"))["items"]
    banane = next(i for i in items if i["name"] == "Bananen Lose MT")
    assert banane["price"] == "1,24"
    assert banane["details"] == ["1,412 x 0,88 EUR/kg"]


# ---------------------------------------------------------------------------
# ebon format — 6.txt
# ---------------------------------------------------------------------------

def test_ebon_format_detected():
    assert parse_receipt(_read("6.txt"))["format"] == "ebon"


def test_ebon_date_year_expanded():
    r = parse_receipt(_read("6.txt"))
    assert r["date"] == "03.07.2024"
    assert r["time"] == "21:45"


def test_ebon_address():
    assert parse_receipt(_read("6.txt"))["address"] == "Oudenarder Str. 14, 13347 Berlin"


def test_ebon_total():
    assert parse_receipt(_read("6.txt"))["total"] == "5,28"


def test_ebon_items_have_tax():
    assert all(i["tax"] in {"A", "B"} for i in parse_receipt(_read("6.txt"))["items"])


def test_ebon_pfand_item_kept():
    items = parse_receipt(_read("6.txt"))["items"]
    assert any("Pfand" in i["name"] for i in items)


# ---------------------------------------------------------------------------
# ebon edge cases
# ---------------------------------------------------------------------------

def test_ebon_superscript_tax_stripped():
    """23.txt has tax letters carrying a superscript ² which must be stripped."""
    items = parse_receipt(_read("23.txt"))["items"]
    assert items, "no items parsed"
    assert all(i["tax"] in {"A", "B"} for i in items)


def test_ebon_quantity_detail_precedes_item():
    """10.txt: '2 x 1,05' printed before 'GL Weidemilch' belongs to it."""
    items = parse_receipt(_read("10.txt"))["items"]
    weidemilch = next(i for i in items if i["name"] == "GL Weidemilch 3,5% 1L")
    assert weidemilch["price"] == "2,10"
    assert weidemilch["details"] == ["2 x 1,05"]


def test_ebon_weight_without_x_parsed():
    """32.txt has weight details in the 'W,WWW kg PRICE EUR/kg' shape (no 'x')."""
    r = parse_receipt(_read("32.txt"))
    assert len(r["items"]) > 0
    assert any("EUR/kg" in d for i in r["items"] for d in i["details"])


def test_ebon_total_falls_back_to_bracket_sum():
    """21.txt lacks the 'SUMME €' line; total comes from 'SUMME [N] X,XX'."""
    assert parse_receipt(_read("21.txt"))["total"] == "3,24"
