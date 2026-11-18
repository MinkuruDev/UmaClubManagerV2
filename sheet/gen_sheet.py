import os

import gspread
import requests

from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://localhost:3636"
SPREADSHEET_URL = os.environ["SPREADSHEET_URL"]
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

AQUA = {"red": 0.0, "green": 1.0, "blue": 1.0}     # #00FFFF
YELLOW = {"red": 1.0, "green": 1.0, "blue": 0.0}   # #FFFF00

FAN_FORMAT = {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}        # shows 1.234 with vi locale
MONEY_FORMAT = {"numberFormat": {"type": "NUMBER", "pattern": '#,##0"đ"'}}   # shows 36.000đ with vi locale


def get_latest_month_year() -> tuple[int, int]:
    r = requests.get(f"{BASE_URL}/latest_date", timeout=30)
    r.raise_for_status()
    d = r.json()  # {"year": y, "month": m, "day": d}
    return int(d["month"]), int(d["year"])


def get_members() -> list[dict]:
    r = requests.get(f"{BASE_URL}/fan_data/processed", timeout=60)
    r.raise_for_status()
    members = r.json()[2]

    def sort_key(m):
        try:
            return (0, int(m["ingame_id"]))
        except (ValueError, TypeError):
            return (1, str(m["ingame_id"]))

    return sorted(members, key=sort_key)


def formulas_for_row(r: int) -> list[str]:
    # Columns D..I (Sheets API takes comma-separated, English-style formulas)
    return [
        f"=FLOOR(B{r}/C{r}*100)",                              # D
        f"=IF(D{r}<100,C{r}-B{r},0)",                          # E
        f"=CEILING(E{r}/C{r}*100)",                            # F
        f"=E{r}*2",                                            # G
        f"=IF(AND(F{r}>0,F{r}<=18),36000,F{r}*2000)",          # H
        f"=IF(D{r}>=200,FLOOR((D{r}-100)/100),0)",             # I
    ]


def apply_formatting(sh, ws, last_row: int):
    """Number formats + conditional-format rules (rules are rebuilt every run)."""
    sheet_id = ws.id
    end = max(ws.row_count, last_row)

    def grid(col_start, col_end):
        return {
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "endRowIndex": end,
            "startColumnIndex": col_start,
            "endColumnIndex": col_end,
        }

    requests_body = []

    # Remove existing conditional format rules on this sheet so they don't pile up
    meta = sh.fetch_sheet_metadata()
    for s in meta["sheets"]:
        if s["properties"]["sheetId"] == sheet_id:
            n_rules = len(s.get("conditionalFormats", []))
            requests_body += [
                {"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": 0}}
                for _ in range(n_rules)
            ]

    # Number formats: fan -> B, C, E, G ; money -> H
    for c0, c1, fmt in [(1, 3, FAN_FORMAT), (4, 5, FAN_FORMAT), (6, 7, FAN_FORMAT), (7, 8, MONEY_FORMAT)]:
        requests_body.append({
            "repeatCell": {
                "range": grid(c0, c1),
                "cell": {"userEnteredFormat": fmt},
                "fields": "userEnteredFormat.numberFormat",
            }
        })

    # Conditional formatting over A:I (locale-independent: no commas/semicolons).
    # Added yellow first, then aqua, both at index 0, so aqua ends up with the higher priority.
    full_range = grid(0, 9)
    for formula, color in [
        ('=($A2<>"")*($B2<$C2)', YELLOW),   # fan below expected
        ('=($A2<>"")*($I2>0)', AQUA),       # Nhận quỹ > 0
    ]:
        requests_body.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [full_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": formula}],
                        },
                        "format": {"backgroundColor": color},
                    },
                },
                "index": 0,
            }
        })
        
    # addConditionalFormatRule with index 0 inserts at the top, so the second one added would
    # outrank the first. Swap them so aqua stays on top:
    requests_body[-2], requests_body[-1] = requests_body[-1], requests_body[-2]

    sh.batch_update({"requests": requests_body})


def main():
    month, year = get_latest_month_year()
    sheet_name = f"{month:02d}/{year} Auto Generated"
    next_month = month % 12 + 1  # December -> T1

    header = [
        "Thành viên", "Fan đạt được", "Yêu cầu", "Đạt được (%)", "Thiếu",
        "Tỉ lệ thiếu (%)", f"Cày bù T{next_month}", "Đóng họ", "Nhận quỹ (phần)",
    ]

    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_url(SPREADSHEET_URL)

    try:
        ws = sh.worksheet(sheet_name)
        existed = True
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=100, cols=len(header))
        existed = False

    members = get_members()
    n = len(members)
    last_row = n + 1  # header is row 1

    old_formula_rows = max(len(ws.col_values(4)) - 1, 0) if existed else 0
    old_row_count = ws.row_count

    if ws.row_count < last_row:
        ws.resize(rows=last_row)

    # Header
    ws.update(range_name="A1:I1", values=[header], value_input_option="USER_ENTERED")

    # Override A:C
    if n:
        abc = [[m["name"], m["fan"], m["expected"]] for m in members]
        ws.update(range_name=f"A2:C{last_row}", values=abc, value_input_option="USER_ENTERED")

    # Formulas D:I: new sheet -> all rows; existing sheet -> only rows that don't have them yet
    first_formula_row = 2 if not existed else old_formula_rows + 2
    if n and first_formula_row <= last_row:
        rows = [formulas_for_row(r) for r in range(first_formula_row, last_row + 1)]
        ws.update(
            range_name=f"D{first_formula_row}:I{last_row}",
            values=rows,
            value_input_option="USER_ENTERED",
        )

    # Remove leftover rows when new data has fewer rows
    if existed:
        stale_end = max(old_formula_rows + 1, old_row_count)
        if stale_end > last_row:
            ws.batch_clear([f"A{last_row + 1}:I{stale_end}"])
        ws.batch_clear(["J:J"])  # drop the old "Ghi chú" column if it was there

    apply_formatting(sh, ws, last_row)
    print(f"Done: '{sheet_name}', {n} members.")


if __name__ == "__main__":
    main()
