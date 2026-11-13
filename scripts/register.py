#!/usr/bin/env python3
"""The register of CRA obligations for one product and release, as an Excel workbook.

    python3 scripts/register.py register/partner-portal-2016.4.json

Writes the .xlsx next to the input: one sheet with a row per obligation (state,
evidence, next step, effort in days) and a summary on top. Needs openpyxl.
"""

import json
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

COLUMNS = [("Pflicht", "pflicht", 38), ("Fundstelle", "fundstelle", 30), ("Stand", "stand", 12),
           ("Beleg", "beleg", 38), ("Nächster Schritt", "schritt", 36), ("Aufwand (Tage)", "aufwand", 15)]
FILL = {"belegt": "C6EFCE", "teilweise": "FFEB9C", "offen": "FFC7CE"}
INK = {"belegt": "006100", "teilweise": "7F6000", "offen": "9C0006"}


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    rows = data["rows"]
    count = {s: sum(r["stand"] == s for r in rows) for s in FILL}
    days = sum(r["aufwand"] or 0 for r in rows)
    undecided = sum(r["aufwand"] is None for r in rows)

    wb = Workbook()
    ws = wb.active
    ws.title = "CRA-Pflichten"
    ws["A1"] = f"Register der CRA-Pflichten: {data['product']} {data['release']}"
    ws["A1"].font = Font(size=16, bold=True)
    ws["A2"] = f"Stand {'.'.join(reversed(data['date'].split('-')))} · {data['note']}"
    ws["A2"].font = Font(italic=True, color="595959")
    summary = [("Pflichten", len(rows)), ("belegt", count["belegt"]), ("teilweise", count["teilweise"]),
               ("offen", count["offen"]), ("Aufwand (Tage)", days), ("Entscheidungen der Leitung", undecided)]
    for i, (label, value) in enumerate(summary):
        cell = ws.cell(row=4, column=i + 1, value=label)
        cell.font = Font(bold=True, color="595959", size=9)
        cell = ws.cell(row=5, column=i + 1, value=value)
        cell.font = Font(size=18, bold=True)
        cell.alignment = Alignment(horizontal="left")

    head = 7
    for c, (title, _, width) in enumerate(COLUMNS, start=1):
        ws.cell(row=head, column=c, value=title)
        ws.column_dimensions[get_column_letter(c)].width = width
    thin = Side(style="thin", color="D9D9D9")
    for r, row in enumerate(rows, start=head + 1):
        for c, (_, key, _) in enumerate(COLUMNS, start=1):
            value = row[key]
            cell = ws.cell(row=r, column=c, value="–" if value in ("", None) else value)
            cell.alignment = Alignment(vertical="top", wrap_text=True, horizontal="left")
            cell.border = Border(bottom=thin)
        state = ws.cell(row=r, column=3)
        state.fill = PatternFill("solid", start_color=FILL[row["stand"]])
        state.font = Font(bold=True, color=INK[row["stand"]])
        ws.cell(row=r, column=1).font = Font(bold=True)
        ws.row_dimensions[r].height = 32
    table = Table(displayName="Pflichten", ref=f"A{head}:{get_column_letter(len(COLUMNS))}{head + len(rows)}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
    ws.add_table(table)
    ws.freeze_panes = ws.cell(row=head + 1, column=1)
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    out = path.rsplit(".", 1)[0] + ".xlsx"
    wb.save(out)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
