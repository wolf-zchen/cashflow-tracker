# Cashflow Tracker

A personal finance desktop app for macOS built with Python + Tkinter.

Import your bank CSVs, auto-categorize transactions, and analyze spending with the **Conscious Spending Plan** framework.

---

## Features

- **Import** bank CSVs from Chase, Amex, Bank of America, Discover, and Monarch Money
- **Auto-categorize** transactions using keyword rules you can customize
- **Expense / Income / Transfer** detection — credit card payments excluded from totals
- **Dashboard** with monthly trends and top spending categories
- **Spending Plan tab** — tracks against [Ramit Sethi's Conscious Spending Plan](https://www.iwillteachyoutoberich.com/conscious-spending-basics/) (Fixed / Investments / Savings / Guilt-Free)
- **Rules** — keyword → category rules that learn over time
- **Tags** on transactions for custom labeling
- **Export CSV** of any filtered view
- **Package as a .app** for macOS (PyInstaller)

---

## Supported Banks

| Bank | Format | Notes |
|---|---|---|
| Chase Credit Card | CSV | Categories included |
| Chase Checking | CSV | |
| American Express | CSV or Excel (.xlsx) | |
| Bank of America | CSV | |
| Discover | CSV | Same format as Chase Checking |
| **Monarch Money** | CSV export | All accounts in one file |

---

## Setup

**Requirements:** Python 3.10+, macOS (Windows/Linux should work but untested)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python cashflow_app.py
```

---

## How to Use

### Step 1 — Import your transactions

Go to the **Import** tab and click **Browse** to select a file. The app auto-detects the bank format.

#### Importing from your bank directly

Download the CSV export from your bank's website:

- **Chase**: Accounts → Download Account Activity → CSV
- **Amex**: Statements & Activity → Export → CSV or Excel
- **Bank of America**: Transaction History → Download → CSV
- **Discover**: Manage → Download Transactions → CSV

Select the file in the Import tab and click **Import**.

#### Importing from Monarch Money (recommended)

If you use Monarch Money to aggregate all your accounts, you can import everything at once:

1. In Monarch: **Settings → Data → Export Transactions**
2. Download the CSV
3. Import it — all accounts are automatically detected and named (e.g., `Chase Credit *4459`, `Amex Blue Cash *2003`)

Monarch is the easiest path if you have multiple accounts.

#### What happens on import

- Duplicate transactions are skipped automatically (safe to re-import the same file)
- Each transaction is auto-categorized based on keyword rules
- Transaction type is detected: **expense**, **income**, or **transfer**
  - Credit card payments, bank transfers, and loan repayments are marked as **transfer** and excluded from expense/income totals
- Account names are extracted from the file (not the filename)

---

### Step 2 — Review in the Transactions tab

The **Transactions** tab shows all imported data with filters at the top.

**Filters:**
- **Date range** — pick start/end dates or use the quick buttons (This Month, Last Month, This Year, All Time)
- **Account** — filter to one account or view all
- **Category** — filter to one category
- **Search** — keyword search across description

**Columns:** Date · Description · Amount · Category · Type · Account · Tags

**Editing a transaction:**
- Double-click any row to open the edit dialog
- Change category, type, tags, or notes
- Your edit is saved immediately

**Adding a transaction manually:**
- Click **Add Transaction** to enter one that's missing from your CSV

**Exporting:**
- Click **Export CSV** to save the current filtered view as a spreadsheet

---

### Step 3 — Check the Dashboard

The **Dashboard** tab gives you a quick financial overview.

- **Top spending categories** for the selected period
- **Monthly trend** chart showing income vs. expenses over time
- **Status bar** (bottom of window) always shows total income, expenses, and transaction count for the current filter

Use the same date range controls as the Transactions tab to adjust what's shown.

---

### Step 4 — Manage categorization

#### Auto-categorization

When you import, every transaction is automatically categorized by matching keywords in the description against your rules.

Examples of built-in rules:
- `WHOLE FOODS` → Groceries
- `NETFLIX` → Subscription
- `LYFT` / `UBER` → Transportation
- `AMAZON` → Shopping

#### Rules tab

The **Rules** tab shows all your keyword → category mappings.

- **Add a rule**: type a keyword and choose a category, then click Add
- **Delete a rule**: select a row and click Delete
- **Re-run categorization**: after adding rules, click **Categorize All** to re-process all transactions

Rules are saved in `data/learned_rules.json` and persist between sessions.

#### Categories tab

The **Categories** tab lets you rename or remap categories. If a bank exports a category name that doesn't match the app's names (e.g., `Merchandise & Supplies-Wholesale Stores`), you can map it here to something like `Groceries`.

Mappings are saved in `data/category_mappings.json`.

---

### Step 5 — Spending Plan tab

The **Spending Plan** tab implements [Ramit Sethi's Conscious Spending Plan](https://www.iwillteachyoutoberich.com/conscious-spending-basics/), which divides your spending into four buckets:

| Bucket | Target | Examples |
|---|---|---|
| **Fixed Costs** | 50–60% | Rent, utilities, insurance, subscriptions |
| **Investments** | 10% | 401k, brokerage, IRA |
| **Savings** | 5–10% | Emergency fund, vacation fund |
| **Guilt-Free** | 20–35% | Restaurants, shopping, entertainment |

#### Setting up

1. Select a date range (e.g., This Month)
2. Enter your **monthly take-home income** in the income field
3. Click **Refresh** — the four buckets fill with your actual spending

Each bucket shows:
- Actual spend vs. target %
- A color-coded progress bar (green = on track, yellow = close, red = over)

#### Assigning categories to buckets

At the bottom of the Spending Plan tab is a table of all your spending categories with their current bucket assignment.

To reassign a category:
- Right-click a row → choose the new bucket from the menu

Changes take effect immediately on the next Refresh.

Default assignments:
- **Fixed**: Housing, Bills & Utilities, Healthcare, Transportation, Education
- **Investments**: Investment
- **Guilt-Free**: Restaurants, Groceries, Shopping, Entertainment, Travel, Personal
- **Untracked**: Credit Card Payment, Transfer (these don't count toward any bucket)

---

### Tags

Tags let you label transactions with freeform text beyond categories.

Examples: `tax-deductible`, `reimbursable`, `business`, `vacation-hawaii`

- Add tags when editing a transaction (comma-separated)
- Tags are stored per-transaction and visible in the Transactions tab
- Use the search filter to find transactions by tag

---

### Tools menu

The **Tools** menu has two utilities:

#### Categorize All

Re-runs auto-categorization on every transaction in the database. Use this after adding new rules to apply them retroactively.

#### Fix Account Names

If you imported files before account name detection was added, this tool renames existing records using the same regex logic. It shows a preview of what will change before updating.

---

## Tips

- **Start with Monarch Money** if you have multiple accounts — one import covers everything
- **Import monthly** — duplicates are skipped, so there's no harm in re-importing overlapping date ranges
- **Build up your rules** over time — the more keywords you add, the less you'll need to edit categories manually
- **Use the Spending Plan** at the end of each month to see which buckets you overspent
- **Tag reimbursable expenses** so you can filter and total them at tax time or when submitting expenses
- **Export CSV** before doing any bulk analysis in Excel or Google Sheets

---

## Project structure

```
cashflow_tracker/
├── cashflow_app.py          # Main GUI application (Tkinter)
├── requirements.txt
├── CashflowTracker.spec     # PyInstaller build config
├── build_app.sh             # One-command macOS .app builder
├── src/
│   ├── parsers/             # Bank-specific CSV parsers
│   │   ├── monarch_parser.py        # Monarch Money export
│   │   ├── chase_credit_parser.py
│   │   ├── chase_checking_parser.py
│   │   ├── amex_csv_parser.py
│   │   ├── amex_parser.py           # Excel format
│   │   └── bofa_parser.py
│   ├── database/
│   │   └── db_manager.py    # SQLite schema + auto-migrations
│   ├── categorization.py    # Keyword-based auto-categorizer
│   ├── category_mapper.py   # Fuzzy category name matching
│   ├── learned_rules.py     # Persistent user-defined rules
│   └── models.py            # Transaction dataclass
├── scripts/
│   └── classify_transaction_types.py
└── data/                    # Created on first run (gitignored)
    ├── transactions.db
    ├── learned_rules.json
    └── category_mappings.json
```

---

## Building a macOS .app

```bash
pip install pyinstaller
./build_app.sh
# Output: dist/Cashflow Tracker.app
```

If macOS blocks it ("unidentified developer"):
```bash
xattr -cr "dist/Cashflow Tracker.app"
```

When running as a bundled .app, user data lives in:
`~/Library/Application Support/CashflowTracker/`

---

## Adding a new bank parser

1. Create `src/parsers/your_bank_parser.py` inheriting from `BaseParser`
2. Implement `detect()`, `parse()`, and `get_account_name()`
3. Register it in `ALL_PARSERS` in `src/parsers/__init__.py`

---

## License

MIT
