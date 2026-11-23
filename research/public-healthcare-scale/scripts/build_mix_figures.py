#!/usr/bin/env python3
"""Render the payer mix as responsive SVGs and standalone PNGs."""
import argparse
import csv
import subprocess
from dataclasses import dataclass
from html import escape
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
# Listed in stack order, bottom to top.
PAYERS = (
    ("private", "Private health insurance", "#244c83"),
    ("medicare", "Medicare", "#167e88"),
    ("medicaid", "Medicaid (Title XIX)", "#7eb964"),
    ("out_of_pocket", "Out-of-pocket", "#b5d5ec"),
    ("other", "Other NHE", "#a6a6b2"),
)
INK, MUTED, PAPER, GRID = "#203b31", "#465d54", "#fffdf8", "#d9dfd8"


@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    left: int
    right: int
    top: int
    bottom: int
    font: int


class Figure:
    def __init__(self, layout, title, description):
        self.layout = layout
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{layout.width}" height="{layout.height}" '
            f'viewBox="0 0 {layout.width} {layout.height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            f'<path fill="{PAPER}" d="M0 0H{layout.width}V{layout.height}H0Z"/>',
        ]

    def text(self, x, y, value, *, size=None, color=INK, bold=False, anchor="start", serif=False):
        font = "Georgia, DejaVu Serif, serif" if serif else "Arial, DejaVu Sans, sans-serif"
        weight = 700 if bold else 400
        self.parts.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="{font}" font-size="{size or self.layout.font}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>'
        )

    def path(self, points, *, fill="none", stroke="none", width=1, close=False):
        coords = "L".join(f"{x:.2f} {y:.2f}" for x, y in points)
        self.parts.append(f'<path d="M{coords}{"Z" if close else ""}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def save(self, assets, name, png=False):
        path = assets / f"{name}.svg"
        path.write_text("\n".join([*self.parts, "</svg>", ""]), encoding="utf-8")
        if png:
            subprocess.run(["rsvg-convert", "-z", "2", "-o", str(path.with_suffix(".png")), str(path)], check=True)


def grid(fig, marks, maximum, years):
    layout = fig.layout

    def x(year):
        return layout.left + (year - 1996) / 28 * (layout.right - layout.left)

    def y(value):
        return layout.bottom - value / maximum * (layout.bottom - layout.top)

    for value, label in marks:
        fig.path([(layout.left, y(value)), (layout.right, y(value))], stroke=GRID)
        fig.text(layout.left - 8, y(value) + 5, label, color=MUTED, anchor="end")
    for year in years:
        fig.text(x(year), layout.bottom + 25, str(year), color=MUTED, anchor="middle")
    return x, y


def stacked(records, assets, variant, share=False):
    desktop = variant == "desktop"
    social = variant == "linkedin"
    if share:
        layout = Layout(1000, 344, 61, 927, 20, 303, 15) if desktop else Layout(360, 300, 50, 296, 17, 261, 14)
    elif desktop:
        layout = Layout(1000, 574, 62, 740, 158, 508, 15)
    elif social:
        layout = Layout(600, 750, 66, 548, 292, 645, 18)
    else:
        layout = Layout(360, 503, 47, 328, 221, 436, 14)

    title = "How the payer mix changed" if share else "Who pays for U.S. healthcare?"
    desc = ("Each band shows a share of national health spending, 1996 to 2024."
            if share else "U.S. national health spending rose from $1.98 trillion in 1996 to $5.28 trillion in 2024, in 2024 dollars.")
    fig = Figure(layout, title, desc)
    latest = records[-1]
    if not share:
        margin = 34 if social else 22 if desktop else 14
        fig.text(margin, 34 if social else 25, "WHITE OAK RESEARCH  /  UNITED STATES", size=15 if social else 12, bold=True)
        fig.text(margin, 83 if social else 68 if desktop else 55,
                 "Who pays for U.S." if social else title,
                 size=46 if social else 39 if desktop else 23, serif=True)
        if social:
            fig.text(margin, 131, "healthcare?", size=46, serif=True)
        subtitle = "National spending, 1996–2024 · trillions of 2024 dollars"
        if not desktop and not social:
            subtitle = "1996–2024 · trillions of 2024 dollars"
        fig.text(margin, 165 if social else 95 if desktop else 79, subtitle, color=MUTED)
        if desktop:
            fig.text(layout.right + 20, 160, "2024 spending", bold=True, size=13, color=MUTED)
        else:
            fig.text(547 if social else 341, 187 if social else 99,
                     "2024 spending", anchor="end", size=13 if social else 12, color=MUTED)
        positions = ([22, 255, 395, 585, 778] if desktop else
                     [34, 331, 34, 331, 34] if social else [14, 14, 14, 14, 14])
        for i, ((key, label, color), left) in enumerate(zip(PAYERS, positions, strict=True)):
            y = 123 if desktop else 207 + 28 * (i // 2) if social else 119 + 18 * i
            fig.path([(left, y - 11), (left + 14, y - 11), (left + 14, y + 3), (left, y + 3)],
                     fill=color, stroke=MUTED, width=.65, close=True)
            legend_label = "Other health spending" if social and key == "other" else label
            fig.text(left + 21, y, legend_label, bold=True, size=16 if social else None)
            amount = latest[f"{key}_nominal_usd_millions"] / 1e6
            if not desktop:
                if social:
                    fig.text(left + (280 if i % 2 == 0 else 216), y, f"${amount:.2f}T", anchor="end")
                else:
                    fig.text(341, y, f"${amount:.2f}T", anchor="end")

    max_value = 100 if share else 6
    marks = [(p, f"{p}%") for p in (0, 25, 50, 75, 100)] if share else [(p, f"${p}T") for p in (0, 2, 4, 6)]
    x, y = grid(fig, marks, max_value, (1996, 2003, 2010, 2017, 2024) if desktop or social else (1996, 2005, 2015, 2024))
    years = [int(row["year"]) for row in records]
    lower = [0.0] * len(records)
    for key, label, color in PAYERS:
        series = [row[f"{key}_pct_nhe"] if share else row[f"{key}_real_2024_usd_millions"] / 1e6 for row in records]
        upper = [base + value for base, value in zip(lower, series, strict=True)]
        top = [(x(year), y(value)) for year, value in zip(years, upper, strict=True)]
        bottom = [(x(year), y(value)) for year, value in zip(years, lower, strict=True)]
        fig.path(top + list(reversed(bottom)), fill=color, stroke=PAPER, width=1.1, close=True)
        if desktop and not share:
            middle = y((upper[-1] + lower[-1]) / 2)
            fig.path([(layout.right, middle), (layout.right + 13, middle)], stroke=MUTED)
            fig.text(layout.right + 20, middle + 5, f"{label}  ${series[-1]:.2f}T", bold=True, size=14)
        if share:
            middle = y((upper[-1] + lower[-1]) / 2)
            fig.path([(layout.right, middle), (layout.right + 5, middle)], stroke=MUTED)
            fig.text(layout.right + 8, middle + 5, f"{series[-1]:.1f}%", bold=True)
        lower = upper
    if not share:
        center = 0 if desktop else 8
        fig.text(layout.right - center, y(lower[-1]) - 10, f"${lower[-1]:.2f}T total",
                 bold=True, anchor="end", size=20 if desktop or social else 14)
        source = "CMS National Health Expenditure Accounts · BEA GDP deflator"
        if not desktop:
            fig.text(margin, layout.height - (55 if social else 23), "Source: CMS National Health Expenditure Accounts", size=15 if social else 12, color=MUTED)
            source = "Prices adjusted using the BEA GDP deflator."
        fig.text(margin, layout.height - (35 if social else 8 if not desktop else 13),
                 source, size=15 if social else 12, color=MUTED)
        if social:
            fig.text(margin, 735, "Other includes other programs, public health and investment.",
                     size=15, color=MUTED)
    name = "payer-share" if share else "health-spending"
    suffix = "" if desktop else f"-{variant}"
    fig.save(assets, name + suffix, png=not share)


def gdp(records, assets, mobile):
    layout = Layout(360, 288, 50, 330, 23, 249, 14) if mobile else Layout(1000, 319, 61, 946, 25, 278, 15)
    fig = Figure(layout, "National health spending as a share of GDP",
                 "The share rose from 13.3% in 1996 to a high of 19.7% in 2020 and was 18.0% in 2024.")
    x, y = grid(fig, [(p, f"{p}%") for p in (0, 5, 10, 15, 20)], 20,
                (1996, 2005, 2015, 2024) if mobile else (1996, 2003, 2010, 2017, 2024))
    points = {int(row["year"]): row["nhe_pct_gdp"] for row in records}
    fig.path([(x(year), y(value)) for year, value in points.items()], stroke=INK, width=3)
    for year in (1996, 2020, 2024):
        px, py = x(year), y(points[year])
        fig.parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="{INK}"/>')
        offset = 17 if year == 2024 else -11
        anchor = "end" if year == 2024 or (mobile and year == 2020) else "start"
        label = f"{points[year]:.1f}%" if year != 2020 else f"2020 · {points[year]:.1f}%"
        fig.text(px - 4 if anchor == "end" else px + 2, py + offset, label, bold=True, anchor=anchor)
    fig.save(assets, "health-gdp-mobile" if mobile else "health-gdp")


def build(site):
    assets = site / "assets"
    with (site / "data/payer-mix.csv").open(newline="") as file:
        records = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(file)]
    assets.mkdir(exist_ok=True)
    for variant in ("desktop", "mobile", "linkedin"):
        stacked(records, assets, variant)
    for variant in ("desktop", "mobile"):
        stacked(records, assets, variant, share=True)
        gdp(records, assets, mobile=variant == "mobile")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=SITE)
    build(parser.parse_args().site)
