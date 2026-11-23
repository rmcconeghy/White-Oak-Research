#!/usr/bin/env python3
"""Build the 1996–2024 source-of-funds series from pinned official inputs."""
import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
YEARS = range(1996, 2025)
PAYER_ROWS = {
    "private": (6, "Private Health Insurance"),
    "medicare": (7, "Medicare"),
    "medicaid": (8, "Medicaid (Title XIX)"),
    "out_of_pocket": (4, "Out of pocket"),
}
OTHER_ROWS = {
    "chip": (11, "CHIP (Title XIX and Title XXI)"),
    "defense": (14, "Department of Defense"),
    "va": (15, "Department of Veterans Affairs"),
    "other_third_party": (16, "Other Third Party Payers and Programs"),
    "public_health": (32, "Public Health Activity"),
    "investment": (35, "Investment"),
}


def read_csv(archive, filename):
    with ZipFile(RAW / archive) as source:
        content = source.read(filename).decode("cp1252")
    return list(csv.reader(io.StringIO(content)))


def read_value(table, row, label, year, *, pre_chip=False):
    cells = table[row - 1]
    assert cells[0].strip() == label, (row, cells[0])
    raw = cells[year - 1959].strip()
    if pre_chip and year <= 1997:
        # CMS explicitly prints a dash for the two pre-expenditure years.
        assert raw == "-", raw
        return Decimal(0)
    value = Decimal(raw.replace(",", ""))
    assert value.is_finite() and value >= 0, (year, label, value)
    return value


def build(site):
    output = site / "data"
    detail = read_csv("cms-detail.zip", "NHE2024.csv")
    summary = read_csv("cms-summary.zip", "NHE24_Summary.csv")
    for table, heading in ((detail, "Expenditure Amount (Millions)"),
                           (summary, "Expenditure Amount")):
        assert table[1] == [heading, *map(str, range(1960, 2025))]
    with (RAW / "bea-gdp-deflator-2026-10-29.csv").open(newline="") as file:
        price_rows = list(csv.DictReader(file))
    prices = {int(row["year"]): Decimal(row["gdp_deflator_2017_100"]) for row in price_rows}
    assert len(price_rows) == len(YEARS) and set(prices) == set(YEARS)
    assert all(p.is_finite() and p > 0 for p in prices.values())
    assert prices[2017] == 100 and prices[2024] == Decimal("125.587")

    records = []
    for year in YEARS:
        total = read_value(detail, 3, "Total National Health Expenditures", year)
        rounded_total = read_value(summary, 3, "National Health Expenditures (Amount in Billions)", year)
        assert abs(total - rounded_total * 1000) <= 50, year
        payers = {key: read_value(detail, *spec, year) for key, spec in PAYER_ROWS.items()}
        other_components = {key: read_value(detail, *spec, year, pre_chip=key == "chip")
                            for key, spec in OTHER_ROWS.items()}
        payers["other"] = total - sum(payers.values())
        rounding = payers["other"] - sum(other_components.values())
        # Total and ten component rows each round independently to the nearest million.
        assert payers["other"] >= 0 and abs(rounding) <= Decimal("5.5"), (year, rounding)
        assert sum(payers.values()) == total
        gdp = read_value(summary, 10, "Gross Domestic Product2  (Amount in Billions)", year)
        gdp_pct = total / 10 / gdp
        official_pct = read_value(summary, 31, "National Health Expenditures as a Percent of Gross Domestic Product (Percent)", year)
        assert abs(gdp_pct - official_pct) <= Decimal("0.051"), (year, gdp_pct, official_pct)
        factor = prices[2024] / prices[year]
        record = {"year": year, "nhe_nominal_usd_millions": total,
                  "nhe_real_2024_usd_millions": round(total * factor, 6),
                  "cms_gdp_nominal_usd_billions": gdp, "nhe_pct_gdp": round(gdp_pct, 6),
                  "bea_gdp_deflator_2017_100": prices[year]}
        for key, value in payers.items():
            record[f"{key}_nominal_usd_millions"] = value
            record[f"{key}_real_2024_usd_millions"] = round(value * factor, 6)
            record[f"{key}_pct_nhe"] = round(100 * value / total, 6)
        share_sum = sum(record[f"{key}_pct_nhe"] for key in payers)
        real_sum = sum(record[f"{key}_real_2024_usd_millions"] for key in payers)
        assert abs(share_sum - 100) <= Decimal("0.000003"), year
        assert abs(real_sum - record["nhe_real_2024_usd_millions"]) <= Decimal("0.000003"), year
        record.update({f"other_{key}_nominal_usd_millions": value for key, value in other_components.items()})
        record["other_rounding_usd_millions"] = rounding
        records.append(record)

    latest = records[-1]
    assert latest["nhe_nominal_usd_millions"] == 5278588
    assert [latest[f"{key}_nominal_usd_millions"] for key in (*PAYER_ROWS, "other")] == [
        1644592, 1118000, 931692, 556554, 1027750]
    assert [round(latest[f"{key}_pct_nhe"], 1) for key in (*PAYER_ROWS, "other")] == [
        Decimal(value) for value in ("31.2", "21.2", "17.7", "10.5", "19.5")]
    output.mkdir(parents=True, exist_ok=True)
    with (output / "payer-mix.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=latest)
        writer.writeheader()
        writer.writerows(records)
    report = {
        "years": [1996, 2024],
        "years_validated": len(records),
        "cms_vintage": "NHE historical release through 2024, 2024 comprehensive revision",
        "bea_price_vintage": "2026-10-29",
        "payer_rows_1_indexed": PAYER_ROWS,
        "other_validation_rows_1_indexed": OTHER_ROWS,
        "nominal_reconciliation_max_usd_millions": 0,
        "other_row_sum_tolerance_usd_millions": 5.5,
        "other_row_sum_max_difference_usd_millions": int(max(abs(r["other_rounding_usd_millions"]) for r in records)),
        "2024": latest,
        "bea_original_workbook_sha256": "a920921a004910f973021dc89236f11fca5120fadefcaba4a8e1ff55f7625e2d",
        "sha256": {name: hashlib.sha256((RAW / name).read_bytes()).hexdigest()
                   for name in ("cms-detail.zip", "cms-summary.zip", "bea-gdp-deflator-2026-10-29.csv")},
    }
    (output / "payer-mix-validation.json").write_text(json.dumps(report, indent=2, default=float) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "site")
    build(parser.parse_args().site)
