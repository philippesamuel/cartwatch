import re

# ---------------------------------------------------------------------------
# Netto receipts come in two structurally different formats:
#   - "email": text extracted from the Netto-App receipt e-mail body
#   - "ebon":  raw text extracted from the eBon PDF
# We detect the format first, then run a format-specific parser.
# ---------------------------------------------------------------------------


def detect_format(text: str) -> str:
    if text.lstrip().startswith("*** eBon"):
        return "ebon"
    return "email"


def parse_receipt(text: str) -> dict:
    fmt = detect_format(text)
    result = parse_netto_ebon(text) if fmt == "ebon" else parse_netto_email(text)
    result["format"] = fmt
    return result


# ---------------------------------------------------------------------------
# email format
# ---------------------------------------------------------------------------

_EMAIL_ITEM = re.compile(r'^(\S.*?)\s{2,}(-?\d{1,3},\d{2})\s*$')


def parse_netto_email(text: str) -> dict:
    dt = re.search(r'(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})', text)
    address = re.search(r'Filiale:\s*\n(.+)\n(\d{5}\s+.+)', text)
    total = re.search(r'^SUMME\s+(\d{1,3},\d{2})', text, re.MULTILINE)

    items = []
    block = re.search(r'^\s*EUR\s*\n(.*?)^={6,}', text, re.MULTILINE | re.DOTALL)
    if block:
        for line in block.group(1).splitlines():
            stripped = line.strip()
            if not stripped or set(stripped) <= {'-'}:
                continue
            m = _EMAIL_ITEM.match(line)
            if m:
                items.append({
                    "name": m.group(1).strip(),
                    "price": m.group(2),
                    "tax": None,
                    "details": [],
                })
            elif items:
                items[-1]["details"].append(stripped)

    return {
        "date": dt.group(1) if dt else None,
        "time": dt.group(2) if dt else None,
        "address": f"{address.group(1).strip()}, {address.group(2).strip()}" if address else None,
        "total": total.group(1) if total else None,
        "items": items,
    }


# ---------------------------------------------------------------------------
# ebon format
# ---------------------------------------------------------------------------

_EBON_ITEM = re.compile(r'^(.+?)\s+(-?\d{1,3},\d{2})(\*?)\s+([AB])²?$')
_EBON_QTY = re.compile(r'^\d+\s+x\s+\d+,\d{2}$')
_EBON_WEIGHT = re.compile(r'^\d+,\d+\s*kg\s*(?:x\s+)?\d+,\d{2}\s*EUR/kg$')
_EBON_DISCOUNT = re.compile(r'^(?:Rabatt|Netto-App Coupon|Preisaenderung).*\s-\d+,\d{2}$')
_EBON_PAGE = re.compile(r'^Seite \d+ von \d+$')


def parse_netto_ebon(text: str) -> dict:
    dt = re.search(r'Datum\s+(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})\s+Uhr', text)
    date_str = None
    if dt:
        # Expand 2-digit year (DD.MM.YY) to 4-digit (DD.MM.YYYY) for consistency
        # with the email format.
        date_str = f"{dt.group(1)[:6]}20{dt.group(1)[6:]}"

    address = re.search(r'Filiale \d+\n(.+)\n(\d{5}\s+.+)', text)

    total = re.search(r'SUMME €\s+(-?\d{1,3},\d{2})', text)
    if not total:
        total = re.search(r'SUMME \[\d+\]\s+(-?\d{1,3},\d{2})', text)

    items = []
    pending: list[str] = []
    block = re.search(r'^EUR\n(.*?)^SUMME \[', text, re.MULTILINE | re.DOTALL)
    if block:
        for line in block.group(1).splitlines():
            stripped = line.strip()
            if not stripped or _EBON_PAGE.match(stripped):
                continue

            m = _EBON_ITEM.match(stripped)
            if m:
                items.append({
                    "name": m.group(1).strip(),
                    "price": m.group(2),
                    "tax": m.group(4),
                    "details": pending,
                })
                pending = []
            elif _EBON_QTY.match(stripped):
                # Quantity multiplier precedes the item it applies to.
                pending.append(stripped)
            elif _EBON_WEIGHT.match(stripped) or _EBON_DISCOUNT.match(stripped):
                # Weight and discount lines follow the item they apply to.
                (items[-1]["details"] if items else pending).append(stripped)

    return {
        "date": date_str,
        "time": dt.group(2) if dt else None,
        "address": f"{address.group(1).strip()}, {address.group(2).strip()}" if address else None,
        "total": total.group(1) if total else None,
        "items": items,
    }
