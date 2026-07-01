import re

DATUM_REGEX = r'Datum:\s*(\d{2}\.\d{2}\.\d{4})'
UHRZEIT_REGEX = r'Uhrzeit:\s*(\d{2}:\d{2}:\d{2})\s*Uhr'
FALLBACK_DATETIME_REGEX = r'^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+Bon-Nr\.'

DATUM_PATTERN = re.compile(DATUM_REGEX)
UHRZEIT_PATTERN = re.compile(UHRZEIT_REGEX)
FALLBACK_DATETIME_PATTERN = re.compile(FALLBACK_DATETIME_REGEX, re.MULTILINE)

ADDRESS_REGEX = r'^(.+\d+)\n(\d{5}\s+.+)$'
ITEMS_BLOCK_REGEX = r'^EUR\n(.*?)^-{6,}'
TOTAL_REGEX = r'SUMME\s+EUR\s+(\d{1,3},\d{2})'
ADDRESS_PATTERN = re.compile(ADDRESS_REGEX, re.MULTILINE)
ITEMS_BLOCK_PATTERN = re.compile(ITEMS_BLOCK_REGEX, re.MULTILINE | re.DOTALL)
TOTAL_PATTERN = re.compile(TOTAL_REGEX)

PRICE_REGEX = r'^(.+?)\s+(\d{1,3},\d{2})\s+([A-Z])\s*\*?$'
PRICE_PATTERN = re.compile(PRICE_REGEX)

def parse_receipt(text: str) -> dict:
    date_str = None
    time_str = None

    m = DATUM_PATTERN.search(text)
    if m:
        date_str = m.group(1)
        t = UHRZEIT_PATTERN.search(text)
        time_str = t.group(1) if t else None

    if not date_str:
        m = FALLBACK_DATETIME_PATTERN.search(text)
        if m:
            date_str = m.group(1)
            time_str = m.group(2)

    address = ADDRESS_PATTERN.search(text)
    items_block = ITEMS_BLOCK_PATTERN.search(text)
    total = TOTAL_PATTERN.search(text)

    items = []
    if items_block:
        items = parse_items(items_block.group(1).strip())
    
    return {
        "date": date_str,
        "time": time_str,
        "address": f"{address.group(1)}, {address.group(2)}" if address else None,
        "items": items,
        "total": total.group(1) if total else None,
    }


def parse_items(items_block: str) -> list[dict]:
    lines = items_block.splitlines()
    items = []
    current = []
    for line in lines:
        if line.startswith('-') or line.startswith('SUMME'):
            break
        m = PRICE_PATTERN.match(line)
        if m:
            items.append(
                {
                    "name": m.group(1),
                    "price": m.group(2),
                    "tax": m.group(3),
                    "details": current,
                }
            )
            current = []
        else:
            current.append(line)
    return items
