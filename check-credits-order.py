#!/usr/bin/env python3
"""
Verifies that the credit list on /credits/ is sorted newest first.

Usage:  python check-credits-order.py           report, exit 1 if out of order
        python check-credits-order.py --fix     reorder the rows in place

Every row in the .credits list carries data-date, an ISO date at whatever
precision the source gives: a full date where the release has one, a bare year
where the platform only shows a year. Both sort correctly as plain strings, so
no date parsing is needed and a bare year never has to be faked into a day.

Rows with equal data-date keep their existing order, so where two releases only
resolve to the same year, whatever order you put them in is what stays.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TARGET = ROOT / "credits" / "index.html"

LIST_RE = re.compile(r'(<div class="credits">)(.*?)(\n    </div>)', re.S)
ROW_RE = re.compile(r'\n        <(a|div) class="credit".*?</\1>', re.S)
DATE_RE = re.compile(r'data-date="([^"]+)"')
TITLE_RE = re.compile(r'<div class="credit-title">(.*?)</div>', re.S)


def parse():
    text = TARGET.read_text(encoding="utf-8")
    block = LIST_RE.search(text)
    if not block:
        raise SystemExit(f"{TARGET}: could not find the .credits list")

    rows = list(ROW_RE.finditer(block.group(2)))
    if not rows:
        raise SystemExit(f"{TARGET}: the .credits list has no rows")

    entries = []
    for i, m in enumerate(rows):
        row = m.group(0)
        date = DATE_RE.search(row)
        if not date:
            title = TITLE_RE.search(row)
            name = title.group(1).strip() if title else f"row {i}"
            raise SystemExit(f"{TARGET}: credit '{name}' has no data-date")
        title = TITLE_RE.search(row)
        entries.append({
            "date": date.group(1),
            "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else f"row {i}",
            "html": row,
        })

    # Splice against the first and last row rather than the whole list body, so
    # anything around the rows survives a --fix untouched.
    span = (block.start(2) + rows[0].start(), block.start(2) + rows[-1].end())
    return text, span, entries


def main():
    fix = "--fix" in sys.argv[1:]
    text, span, entries = parse()

    for e in entries:
        if not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", e["date"]):
            raise SystemExit(
                f"{TARGET}: credit '{e['title']}' has data-date '{e['date']}', "
                "expected YYYY, YYYY-MM or YYYY-MM-DD"
            )

    # Stable sort, so equal dates keep the order they were written in.
    wanted = sorted(entries, key=lambda e: e["date"], reverse=True)

    if [e["title"] for e in wanted] == [e["title"] for e in entries]:
        print(f"credits: {len(entries)} rows, newest first, ok")
        return 0

    if not fix:
        print("credits: out of order. Current, then expected:\n")
        for label, rows in (("current ", entries), ("expected", wanted)):
            for e in rows:
                print(f"  {label}  {e['date']:<10}  {e['title']}")
            print()
        print("Run with --fix to reorder.")
        return 1

    # Each row match begins with its own newline, so joining on one more
    # newline keeps the blank line the rows are written with.
    rebuilt = "\n".join(e["html"] for e in wanted)
    TARGET.write_text(
        text[: span[0]] + rebuilt + text[span[1]:],
        encoding="utf-8",
    )
    print(f"credits: reordered {len(entries)} rows, newest first")
    return 0


if __name__ == "__main__":
    sys.exit(main())
