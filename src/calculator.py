import os
import sys
from datetime import datetime, timezone
import pandas as pd
from etsy_client import get_shop_receipts

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

def calculate_profit(df):
    summary = {
        "Total Orders": len(df),
        "Gross Revenue": df["grandtotal"].sum(),
        "Tax Collected (remit to CRA)": df["tax_collected"].sum(),
        "Discounts Given": df["discount"].sum(),
        "Net Revenue": df["grandtotal"].sum() - df["tax_collected"].sum(),
    }
    return summary

if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else None
    label = str(year) if year else "all time"

    print(f"Fetching receipts ({label})...")
    receipts = fetch_all_receipts(year=year)
    print(f"Fetched {len(receipts)} receipts")

    df = parse_receipts(receipts)
    print(f"Processing {len(df)} non-cancelled orders\n")

    summary = calculate_profit(df)
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"{k}: ${v:,.2f} CAD")
        else:
            print(f"{k}: {v}")
