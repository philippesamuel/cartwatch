from pathlib import Path
from typing import Iterable

import pytest

from parsing.receipts.parse_raw_rewe_pdf_text import parse_receipt

DATA_DIR = Path(__file__).parent / "data/receipts_rewe_pdf_text"


_BON_NR_RECEIPT = """\
REWE Josef Seifert oHG
Müllerstraße 141
13353 Berlin
UID Nr.: DE331216382
EUR
MOZZAREL.MAX.45% 1,99 B
PANE RUSTICO 1,39 B
OLIV KNOBL 150G 1,89 B
OLIVEN CHILI 1,89 B
GEMUESEMAULTASCH 2,19 B
KR.BUTTERBAGUETT 0,99 B
NEKTARINE 1,99 B
RUCOLA 0,99 B
STAUDENSEL.BIO 1,99 B
RISPENTOMATE 0,64 B
0,538 kg x 1,19 EUR/kg
SALATGURKE 0,69 B
PAPRIKA MIX REWE 1,49 B
LAYS GESALZEN 1,19 B
BAD LIEB.MEDIUM 0,79 A
PFAND 0,25 EURO 0,25 A *
APFEL DS NL 1,79 A
PAPIER TASCHE GR 1,10 A
2 Stk x 0,55
--------------------------------------
SUMME EUR 23,25
======================================
Geg. BAR EUR 24,00
Rückgeld BAR EUR 0,75
Steuer % Netto Steuer Brutto
A= 19,0% 3,30 0,63 3,93
B= 7,0% 18,06 1,26 19,32
Gesamtbetrag 21,36 1,89 23,25
30.05.2025 17:27 Bon-Nr.:7326
"""


@pytest.fixture
def all_texts() -> Iterable[str]:
    return (p.read_text() for p in sorted(DATA_DIR.glob("*.txt")))


@pytest.fixture
def receipt_with_datum_format() -> str:
    """9.txt — uses Datum: / Uhrzeit: label format."""
    return (DATA_DIR / "9.txt").read_text()


@pytest.fixture
def receipt_with_bon_nr_format() -> str:
    """Full receipt using DD.MM.YYYY HH:MM Bon-Nr. date format; contains PFAND ... * item."""
    return _BON_NR_RECEIPT


@pytest.fixture
def receipt_with_weighted_item() -> str:
    """3.txt — contains kg x EUR/kg detail lines."""
    return (DATA_DIR / "3.txt").read_text()


@pytest.fixture
def receipt_with_multi_quantity() -> str:
    """9.txt — contains N Stk x price detail lines."""
    return (DATA_DIR / "9.txt").read_text()


# ---------------------------------------------------------------------------
# parse_receipt — all 14 receipts
# ---------------------------------------------------------------------------

def test_parse_receipt_all_have_address(all_texts):
    assert all(parse_receipt(t)["address"] is not None for t in all_texts)


def test_parse_receipt_all_have_total(all_texts):
    assert all(parse_receipt(t)["total"] is not None for t in all_texts)


def test_parse_receipt_all_have_items_block(all_texts):
    assert all(parse_receipt(t)["items"] is not None for t in all_texts)


# ---------------------------------------------------------------------------
# parse_receipt — specific values
# ---------------------------------------------------------------------------

def test_datum_format_date(receipt_with_datum_format: str) -> None:
    assert parse_receipt(receipt_with_datum_format)["date"] == "27.01.2026"


def test_datum_format_time(receipt_with_datum_format: str) -> None:
    assert parse_receipt(receipt_with_datum_format)["time"] == "20:49:41"


def test_bon_nr_format_date(receipt_with_bon_nr_format: str) -> None:
    assert parse_receipt(receipt_with_bon_nr_format)["date"] == "30.05.2025"


def test_bon_nr_format_time(receipt_with_bon_nr_format: str) -> None:
    assert parse_receipt(receipt_with_bon_nr_format)["time"] == "17:27"


def test_address_extraction(receipt_with_datum_format: str) -> None:
    assert parse_receipt(receipt_with_datum_format)["address"] == "Müllerstraße 141, 13353 Berlin"


def test_total_extraction(receipt_with_datum_format: str) -> None:
    assert parse_receipt(receipt_with_datum_format)["total"] == "12,70"


# ---------------------------------------------------------------------------
# parse_items — counts
# ---------------------------------------------------------------------------

def test_item_count_basic(receipt_with_datum_format: str) -> None:
    items = parse_receipt(receipt_with_datum_format)["items"]
    assert len(items) == 9


def test_item_count_pfand_included(receipt_with_bon_nr_format: str) -> None:
    """PFAND item ending in ' *' must be counted, not silently dropped."""
    items = parse_receipt(receipt_with_bon_nr_format)["items"]
    names = [i["name"] for i in items]
    assert any("PFAND" in n for n in names), "PFAND item was dropped"
    assert len(items) == 17


# ---------------------------------------------------------------------------
# parse_items — item fields
# ---------------------------------------------------------------------------

def test_item_has_required_keys(receipt_with_datum_format: str) -> None:
    items = parse_receipt(receipt_with_datum_format)["items"]
    for item in items:
        assert set(item.keys()) == {"name", "price", "tax", "details"}


def test_weighted_item_has_detail_line(receipt_with_weighted_item: str) -> None:
    items = parse_receipt(receipt_with_weighted_item)["items"]
    nusskern = next(i for i in items if i["name"] == "NUSSKERNMISCHUNG")
    assert nusskern["details"] == ["0,628 kg x 2,79 EUR/kg"]


def test_multi_quantity_item_has_detail_line(receipt_with_multi_quantity: str) -> None:
    items = parse_receipt(receipt_with_multi_quantity)["items"]
    boerek = next(i for i in items if i["name"] == "BOEREKST. ASIA")
    assert boerek["details"] == ["2 Stk x 0,89"]


def test_pfand_item_tax_is_A(receipt_with_bon_nr_format: str) -> None:
    items = parse_receipt(receipt_with_bon_nr_format)["items"]
    pfand = next(i for i in items if "PFAND" in i["name"])
    assert pfand["tax"] == "A"


def test_regular_item_tax_is_B(receipt_with_datum_format: str) -> None:
    items = parse_receipt(receipt_with_datum_format)["items"]
    assert items[0]["tax"] == "B"


def test_simple_item_has_empty_details(receipt_with_datum_format: str) -> None:
    items = parse_receipt(receipt_with_datum_format)["items"]
    simple = next(i for i in items if i["name"] == "BAUERNKRUSTE")
    assert simple["details"] == []
