# Automated Profits Calculator

A Python tool for Syntaxis (Etsy shop) that pulls order and fee data directly from the Etsy API, calculates GST/HST owed by province, parses business expenses from a credit card CSV export, and produces a clean yearly profit report.

## What It Does

- Fetches all paid Etsy orders for a given year via the Etsy Open API v3
- Pulls itemized Etsy fees from the payment ledger (transaction fees, processing fees, shipping labels, offsite ads, etc.)
- Calculates GST/HST owed per province using current Canadian tax rates (you remit this yourself once GST-registered — Etsy does not)
- Parses a CC CSV statement and categorizes transactions as business expenses
- Outputs a profit report to `outputs/` as a `.txt` file and a raw order export as `.csv`

**Profit formula:**
```
Net Profit = Gross Revenue − GST/HST Owed − Total Etsy Fees − Total Business Expenses
```

## Setup

### Prerequisites

- Python 3.10+
- An Etsy Developer account with an app created at [etsy.com/developers](https://www.etsy.com/developers)
- Your Etsy shop's GST/HST number added to your Etsy account

### Install

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install requests pandas python-dotenv
```

### Configure

Create a `.env` file in the project root (never commit this):

```
ETSY_API_KEY=your_api_key
ETSY_SHARED_SECRET=your_shared_secret
ETSY_SHOP_ID=your_shop_id
ETSY_REDIRECT_URI=http://localhost:3003/callback
ETSY_ACCESS_TOKEN=
ETSY_REFRESH_TOKEN=
```

## Authentication

Etsy uses OAuth 2.0 with PKCE. Run this once per session (or whenever your refresh token expires after ~90 days of inactivity):

```powershell
cd src
python auth.py        # opens browser for Etsy login
python get_token.py   # paste the auth code when prompted
```

Tokens are written to `.env` automatically. After the first run, access tokens refresh automatically — you won't need to re-authenticate unless the refresh token expires.

## Usage

```powershell
cd src

# Yearly report with credit card expenses
python calculator.py 2026 "C:\path\to\your\CC Statement.csv"

# Yearly report without credit card expenses
python calculator.py 2026

# All-time report
python calculator.py
```

Reports are saved to `outputs/profit_report_YEAR.txt` and `outputs/orders_YEAR.csv`.

## Credit Card CSV

Export your RBC Visa statement as CSV from RBC Online Banking (Download Transactions → CSV format). The parser expects the standard RBC format:

```
Account Type,Account Number,Transaction Date,Cheque Number,Description 1,Description 2,CAD$,USD$
```

Business expenses are categorized automatically by merchant keyword. To add or adjust categories, edit `BUSINESS_KEYWORDS` and `EXCLUDED_KEYWORDS` in `src/expenses.py`. Any unrecognized transactions are flagged as `UNCATEGORIZED` in the report for manual review.

## GST/HST Rates

Rates are defined in `PROVINCE_TAX_RATES` in `src/calculator.py`. Only federal GST/HST is calculated — provincial PST (BC, MB, SK) and QST (QC) are out of scope as they require separate provincial registrations.

| Province | Rate | Type |
|---|---|---|
| ON | 13% | HST |
| NB, NL, NS, PE | 15% | HST |
| NS | 14% | HST |
| AB, BC, MB, QC, SK, NT, NU, YT | 5% | GST only |

## Project Structure

```
automated-profits-calculator/
├── src/
│   ├── auth.py          # OAuth PKCE flow — opens browser for Etsy login
│   ├── get_token.py     # Exchanges auth code for tokens, saves to .env
│   ├── etsy_client.py   # Etsy API calls + auto token refresh
│   ├── calculator.py    # Main script — fetches, calculates, and reports
│   └── expenses.py      # RBC CSV parser and expense categorizer
├── outputs/             # Generated reports (gitignored)
├── .env                 # API credentials (gitignored)
└── .gitignore
```

## Notes

- Etsy access tokens expire every hour but refresh automatically
- The ledger entries endpoint has a 31-day window limit — the tool handles this by fetching month-by-month automatically
- `outputs/` is gitignored — reports are never committed
