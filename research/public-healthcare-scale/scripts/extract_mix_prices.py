#!/usr/bin/env python3
"""Extract the pinned BEA annual GDP deflator from the archived workbook."""
import csv
from decimal import Decimal
from pathlib import Path

from xlsx_read import sheets

ROOT = Path(__file__).resolve().parents[1]
YEARS = range(1996, 2025)


def extract():
    sheet = sheets(ROOT / "data/raw/bea-section1.xlsx")["T10109-A"]
    assert "Index numbers, 2017=100" in sheet[2]["A"]
    price_row, = (r for r in sheet.values() if r.get("C") == "A191RD"
                  and r.get("B", "").strip() == "Gross domestic product")
    prices = {int(year): Decimal(price_row[col]) for col, year in sheet[8].items()
              if year.isdigit() and int(year) in YEARS}
    assert set(prices) == set(YEARS) and all(p.is_finite() and p > 0 for p in prices.values())
    with (ROOT / "data/raw/bea-gdp-deflator-2026-10-29.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["year", "gdp_deflator_2017_100"])
        writer.writerows(sorted(prices.items()))


if __name__ == "__main__":
    extract()
