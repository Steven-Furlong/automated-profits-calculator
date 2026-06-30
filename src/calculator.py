import os
import sys
from datetime import datetime, timezone
import pandas as pd
from etsy_client import get_shop_receipts, get_ledger_entries

def year_to_timestamps(year):
    start = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp()) - 1
    return start, end

def fetch_all_receipts(year=None):
    all_receipts = []
    offset = 0
    limit = 100

    min_ts, max_ts = year_to_timestamps(year) if year else (None, None)

    while True:
        data = get_shop_receipts(limit=limit, offset=offset, min_created=min_ts, max_created=max_ts)
        results = data.get("results", [])
        all_receipts.extend(results)
        if len(results) < limit:
            break
        offset += limit

    return all_receipts

MAX_WINDOW_SECONDS = 2678400  # 31 days, Etsy's ledger-entries limit

def month_windows(start_ts, end_ts):
    windows = []
    window_start = start_ts
    while window_start <= end_ts:
        window_end = min(window_start + MAX_WINDOW_SECONDS - 1, end_ts)
        windows.append((window_start, window_end))
        window_start = window_end + 1
    return windows

def fetch_all_ledger_entries(year=None):
    all_entries = []
    if year:
        min_ts, max_ts = year_to_timestamps(year)
    else:
        min_ts = int(datetime(2015, 1, 1, tzinfo=timezone.utc).timestamp())
        max_ts = int(datetime.now(timezone.utc).timestamp())

    for window_start, window_end in month_windows(min_ts, max_ts):
        offset = 0
        limit = 100
        while True:
            data = get_ledger_entries(limit=limit, offset=offset, min_created=window_start, max_created=window_end)
            results = data.get("results", [])
            all_entries.extend(results)
            if len(results) < limit:
                break
            offset += limit

    return all_entries

NON_FEE_TYPES = {
    "DISBURSE2",      # payout to your bank account, not a fee
    "REFUND_GROSS",   # refunds issued to customers, not a fee
    "sales_tax",      # tax collected from buyers, already in tax_collected
}

def calculate_fees(entries):
    fees_by_type = {}
    for e in entries:
        ledger_type = e.get("ledger_type", "")
        if ledger_type in NON_FEE_TYPES:
            continue
        amount = e["amount"] / 100
        if amount >= 0:
            continue  # only count charges (negative amounts), not deposits/refunds
        fees_by_type[ledger_type] = fees_by_type.get(ledger_type, 0) + abs(amount)
    return fees_by_type

def parse_receipts(receipts):
    rows = []
    for r in receipts:
        if r["status"] == "Canceled":
            continue

        rows.append({
            "receipt_id": r["receipt_id"],
            "date": pd.to_datetime(r["created_timestamp"], unit="s"),
            "status": r["status"],
            "country": r["country_iso"],
            "province": r["state"] if r["country_iso"] == "CA" else None,
            "subtotal": r["subtotal"]["amount"] / r["subtotal"]["divisor"],
            "total_price": r["total_price"]["amount"] / r["total_price"]["divisor"],
            "shipping": r["total_shipping_cost"]["amount"] / r["total_shipping_cost"]["divisor"],
            "tax_collected": r["total_tax_cost"]["amount"] / r["total_tax_cost"]["divisor"],
            "discount": r["discount_amt"]["amount"] / r["discount_amt"]["divisor"],
            "grandtotal": r["grandtotal"]["amount"] / r["grandtotal"]["divisor"],
            "currency": r["grandtotal"]["currency_code"],
        })

    return pd.DataFrame(rows)

# GST/HST/PST rates by province (as of 2026). Etsy does NOT remit this once
# a GST/HST number is added to the shop -- the seller is responsible for
# calculating and remitting it themselves.
PROVINCE_TAX_RATES = {
    "AB": 0.05,    # GST only
    "BC": 0.05,    # GST only (PST not collected by Etsy/marketplace, out of scope)
    "MB": 0.05,    # GST only (PST not collected by Etsy/marketplace, out of scope)
    "NB": 0.15,    # HST
    "NL": 0.15,    # HST
    "NS": 0.14,    # HST
    "NT": 0.05,    # GST only
    "NU": 0.05,    # GST only
    "ON": 0.13,    # HST
    "PE": 0.15,    # HST
    "QC": 0.05,    # GST only (QST not collected by Etsy/marketplace, out of scope)
    "SK": 0.05,    # GST only (PST not collected by Etsy/marketplace, out of scope)
    "YT": 0.05,    # GST only
}

def calculate_gst_hst_by_province(df):
    ca_orders = df[df["country"] == "CA"]
    if ca_orders.empty:
        return pd.DataFrame(columns=["orders", "taxable_sales", "tax_rate", "tax_owed"])

    grouped = ca_orders.groupby("province").agg(
        orders=("receipt_id", "count"),
        taxable_sales=("subtotal", "sum"),
    )
    grouped["tax_rate"] = grouped.index.map(lambda p: PROVINCE_TAX_RATES.get(p, 0))
    grouped["tax_owed"] = grouped["taxable_sales"] * grouped["tax_rate"]
    return grouped.sort_values("tax_owed", ascending=False)

def calculate_profit(df, fees_by_type, gst_hst_owed):
    gross = df["grandtotal"].sum()
    total_fees = sum(fees_by_type.values())
    net = gross - gst_hst_owed - total_fees

    summary = {
        "Total Orders": len(df),
        "Gross Revenue": gross,
        "GST/HST Owed (you remit to CRA)": gst_hst_owed,
        "Discounts Given": df["discount"].sum(),
        "--- Etsy Fees ---": None,
    }
    for ledger_type, amount in sorted(fees_by_type.items(), key=lambda x: -x[1]):
        summary[f"  {ledger_type}"] = amount
    summary["Total Etsy Fees"] = total_fees
    summary["--- Result ---"] = None
    summary["Net Profit"] = net
    return summary

def build_report_lines(label, df, summary, gst_hst, gst_hst_total):
    lines = []
    lines.append(f"Syntaxis Profit Report -- {label}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"\nProcessing {len(df)} non-cancelled orders")
    lines.append("=" * 40)

    for k, v in summary.items():
        if v is None:
            lines.append(f"\n{k}")
        elif isinstance(v, float):
            lines.append(f"{k}: ${v:,.2f} CAD")
        else:
            lines.append(f"{k}: {v}")
    lines.append("=" * 40)

    lines.append("\nGST/HST Owed by Province (you must remit to CRA)")
    lines.append("-" * 40)
    if gst_hst.empty:
        lines.append("No Canadian orders in this period.")
    else:
        for province, row in gst_hst.iterrows():
            lines.append(f"{province}: {int(row['orders'])} orders, "
                          f"taxable sales ${row['taxable_sales']:,.2f}, "
                          f"rate {row['tax_rate']*100:.0f}%, "
                          f"tax owed ${row['tax_owed']:,.2f} CAD")
        lines.append(f"\nTotal GST/HST owed: ${gst_hst_total:,.2f} CAD")
    lines.append("=" * 40)
    return lines

def save_report(label, df, lines):
    outputs_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    safe_label = label.replace(" ", "_")
    report_path = os.path.join(outputs_dir, f"profit_report_{safe_label}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    csv_path = os.path.join(outputs_dir, f"orders_{safe_label}.csv")
    df.to_csv(csv_path, index=False)

    return report_path, csv_path

if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else None
    label = str(year) if year else "all_time"

    print(f"Fetching receipts ({label})...")
    receipts = fetch_all_receipts(year=year)
    print(f"Fetched {len(receipts)} receipts")

    print(f"Fetching ledger entries ({label})...")
    entries = fetch_all_ledger_entries(year=year)
    print(f"Fetched {len(entries)} ledger entries")

    df = parse_receipts(receipts)
    fees_by_type = calculate_fees(entries)
    gst_hst = calculate_gst_hst_by_province(df)
    gst_hst_total = gst_hst["tax_owed"].sum() if not gst_hst.empty else 0

    summary = calculate_profit(df, fees_by_type, gst_hst_total)
    lines = build_report_lines(label, df, summary, gst_hst, gst_hst_total)

    print()
    for line in lines:
        print(line)

    report_path, csv_path = save_report(label, df, lines)
    print(f"\nSaved report to {report_path}")
    print(f"Saved order data to {csv_path}")
