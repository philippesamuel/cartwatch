import re


def parse_receipt(text: str) -> dict:
    date_str = None
    time_str = None

    m = re.search(r'Datum:\s*(\d{2}\.\d{2}\.\d{4})', text)
    if m:
        date_str = m.group(1)
        t = re.search(r'Uhrzeit:\s*(\d{2}:\d{2}:\d{2})\s*Uhr', text)
        time_str = t.group(1) if t else None

    if not date_str:
        m = re.search(r'^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+Bon-Nr\.', text, re.MULTILINE)
        if m:
            date_str = m.group(1)
            time_str = m.group(2)

    address = re.search(r'^(.+\d+)\n(\d{5}\s+.+)$', text, re.MULTILINE)
    items_block = re.search(r'^EUR\n(.*?)^-{6,}', text, re.MULTILINE | re.DOTALL)
    total = re.search(r'SUMME\s+EUR\s+(\d{1,3},\d{2})', text)

    return {
        "date": date_str,
        "time": time_str,
        "address": f"{address.group(1)}, {address.group(2)}" if address else None,
        "items_block": items_block.group(1).strip() if items_block else None,
        "total": total.group(1) if total else None,
    }

def parse_items(items_block: str) -> list[dict]:
    lines = items_block.splitlines()
    items = []
    current = []
    price_re = re.compile(r'^(.+?)\s+(\d{1,3},\d{2})\s+([A-Z])\s*\*?$')
    for line in lines:
        if line.startswith('-') or line.startswith('SUMME'):
            break
        m = price_re.match(line)
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

