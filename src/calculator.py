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

FEE_TYPES = {"listing", "transaction", "payment_processing", "offsite_ads"}

def fetch_all_ledger_entries(year=None):
    all_entries = []
    offset = 0
    limit = 100
    min_ts, max_ts = year_to_timestamps(year) if year else (None, None)

    while True:
        data = get_ledger_entries(limit=limit, offset=offset, min_created=min_ts, max_created=max_ts)
        results = data.get("results", [])
        all_entries.extend(results)
        if len(results) < limit:
            break
        offset += limit

    return all_entries

def calculate_fees(entries):
    fees_by_type = {}
    for e in entries:
        entry_type = e.get("entry_type", "")
        if entry_type not in FEE_TYPES:
            continue
        amount = abs(e["amount"]) / e["divisor"]
        fees_by_type[entry_type] = fees_by_type.get(entry_type, 0) + amount
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

def calculate_profit(df, fees_by_type):
    gross = df["grandtotal"].sum()
    tax = df["tax_collected"].sum()
    total_fees = sum(fees_by_type.values())
    net = gross - tax - total_fees

    summary = {
        "Total Orders": len(df),
        "Gross Revenue": gross,
        "Tax Collected (remit to CRA)": tax,
        "Discounts Given": df["discount"].sum(),
        "--- Etsy Fees ---": None,
        "  Listing Fees": fees_by_type.get("listing", 0),
        "  Transaction Fees (6.5%)": fees_by_type.get("transaction", 0),
        "  Payment Processing Fees": fees_by_type.get("payment_processing", 0),
        "  Offsite Ads Fees": fees_by_type.get("offsite_ads", 0),
        "Total Etsy Fees": total_fees,
        "--- Result ---": None,
        "Net Profit": net,
    }
    return summary

if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else None
    label = str(year) if year else "all time"

    print(f"Fetching receipts ({label})...")
    receipts = fetch_all_receipts(year=year)
    print(f"Fetched {len(receipts)} receipts")

    print(f"Fetching ledger entries ({label})...")
    entries = fetch_all_ledger_entries(year=year)
    print(f"Fetched {len(entries)} ledger entries")

    df = parse_receipts(receipts)
    fees_by_type = calculate_fees(entries)
    print(f"\nProcessing {len(df)} non-cancelled orders\n")
    print("=" * 40)

    summary = calculate_profit(df, fees_by_type)
    for k, v in summary.items():
        if v is None:
            print(f"\n{k}")
        elif isinstance(v, float):
            print(f"{k}: ${v:,.2f} CAD")
        else:
            print(f"{k}: {v}")
    print("=" * 40)
