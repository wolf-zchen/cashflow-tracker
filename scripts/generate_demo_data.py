"""
Generate fake demo CSV files for Cashflow Tracker.

Produces one file per bank in the exact format each parser expects,
so you can demo the Import tab with realistic data.

Run from the project root:
    python scripts/generate_demo_data.py

Output: demo_data/
    Chase4591_Activity.csv          → Chase Credit Card parser
    Chase7823_Activity.csv          → Chase Checking parser
    amex_activity.csv               → Amex CSV parser
    stmt3901_activity.csv           → Bank of America parser
    monarch_export.csv              → Monarch Money parser
"""
import csv
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

OUT_DIR = Path(__file__).parent.parent / "demo_data"
MONTHS  = 3   # months of history per file
SEED    = 42

random.seed(SEED)

# ── Date helpers ──────────────────────────────────────────────────────────────

def months_back(n: int):
    """Return (year, month) for n months before today."""
    today = date.today()
    month = today.month - n
    year  = today.year
    while month <= 0:
        month += 12
        year  -= 1
    return year, month


def rand_date(year: int, month: int) -> date:
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    first = date(year, month, 1)
    return first + timedelta(days=random.randint(0, (last - first).days))


def fmt(d: date, style: str = "mm/dd/yyyy") -> str:
    if style == "mm/dd/yyyy":
        return d.strftime("%m/%d/%Y")
    if style == "yyyy-mm-dd":
        return d.strftime("%Y-%m-%d")
    return str(d)


def rnd(lo: float, hi: float) -> float:
    return round(random.uniform(lo, hi), 2)


def poisson_count(freq: float) -> int:
    """Draw a count ≈ Poisson(freq) using simple Bernoulli trials."""
    count = 0
    remaining = freq
    while remaining > 0:
        if random.random() < min(remaining, 1.0):
            count += 1
        remaining -= 1.0
    return count


# ── Transaction templates per account ─────────────────────────────────────────
# Each entry: (description, (lo, hi) expense amount, chase_category, freq/month)
# Amounts here are always POSITIVE expense values; sign handling is per-format.

CHASE_CREDIT_TXNS = [
    # description                        amount range    chase_category           freq
    ("AMAZON.COM",                        (15, 180),     "Shopping",              5),
    ("DOORDASH",                          (20, 55),      "Food & Drink",          4),
    ("STARBUCKS",                         (5, 12),       "Food & Drink",          8),
    ("CHIPOTLE MEXICAN GRILL",            (12, 18),      "Food & Drink",          3),
    ("SWEETGREEN",                        (14, 20),      "Food & Drink",          3),
    ("UBER",                              (9, 32),       "Travel",                5),
    ("LYFT",                              (8, 28),       "Travel",                3),
    ("NETFLIX.COM",                       (15, 15),      "Entertainment",         1),
    ("SPOTIFY USA",                       (11, 11),      "Entertainment",         1),
    ("APPLE.COM/BILL",                    (3, 30),       "Shopping",              2),
    ("STEAM PURCHASE",                    (10, 60),      "Entertainment",         1),
    ("AMC THEATERS",                      (18, 35),      "Entertainment",         2),
    ("ZARA USA",                          (40, 120),     "Shopping",              1),
    ("NIKE.COM",                          (60, 150),     "Shopping",              1),
    ("CVS PHARMACY",                      (8, 55),       "Health & Wellness",     2),
    ("ELECTRIC BILL PAYMENT",             (80, 140),     "Bills & Utilities",     1),
    ("SOUTHWEST AIRLINES",                (180, 420),    "Travel",                0.3),
    ("AIRBNB",                            (150, 550),    "Travel",                0.3),
    ("INTEREST CHARGE",                   (3, 18),       "Fees & Adjustments",    1),
    # Credit/refund (will appear as negative in Chase format = credit)
]

CHASE_CREDIT_PAYMENTS = [
    # CC payment from checking (shows as negative = credit on the CC statement)
    ("AUTOMATIC PAYMENT - THANK YOU",  (1200, 2800), 1),
]

CHASE_CHECKING_TXNS = [
    # (description, amount_signed, details_type, freq)
    # Positive = credit (income), negative = debit (expense)
    ("Zelle payment from EMPLOYER",         (5200, 5200),  "ACH_CREDIT",   2),   # biweekly payroll
    ("Venmo cashout",                        (30, 150),     "ACH_CREDIT",   1),
    ("RENT - CITYVIEW APARTMENTS",          (-1850, -1850), "ACH_DEBIT",    1),
    ("COMCAST INTERNET 8005COMCAST",        (-75, -75),     "ACH_DEBIT",    1),
    ("GEICO PAYMENT",                       (-148, -148),   "ACH_DEBIT",    1),
    ("CHASE CREDIT CARD AUTOPAY",          (-1500, -2500), "ACH_DEBIT",    1),
    ("AMEX AUTOPAY PAYMENT",               (-600, -1100),  "ACH_DEBIT",    1),
    ("BOFA CREDIT CARD PAYMENT",           (-400, -800),   "ACH_DEBIT",    1),
    ("DISCOVER AUTOPAY PAYMENT",           (-300, -600),   "ACH_DEBIT",    1),
    ("TRANSFER TO SAVINGS",               (-500, -1000),  "ACH_DEBIT",    1),
    ("FIDELITY INVESTMENTS",              (-500, -500),   "ACH_DEBIT",    1),
    ("ROBINHOOD CRYPTO",                  (-200, -200),   "ACH_DEBIT",    1),
    ("CLIPPER CARD BART",                 (-30, -50),     "ACH_DEBIT",    2),
    ("ATM WITHDRAWAL",                    (-60, -200),    "ATM",          1),
    ("VENMO PAYMENT TO ALEX",            (-20, -80),     "ACH_DEBIT",    1),
    ("ZELLE TO SAM",                     (-50, -200),    "ACH_DEBIT",    1),
]

AMEX_TXNS = [
    # (description, amount, freq)   — Amex: positive=expense, negative=payment
    ("WHOLE FOODS MARKET",          (50, 160),  4),
    ("TRADER JOES #243",            (30, 120),  3),
    ("SAFEWAY STORE",               (20, 85),   2),
    ("COSTCO WHOLESALE",            (80, 240),  2),
    ("SHELL OIL",                   (48, 72),   2),
    ("CHEVRON",                     (42, 68),   1),
    ("VERIZON WIRELESS",            (95, 95),   1),
    ("ADOBE SYSTEMS INC",           (55, 55),   1),
    ("GYM MEMBERSHIP PLANET FITNESS",(25, 25),  1),
    ("WALGREENS",                   (5, 40),    1),
    ("TARGET STORE",                (30, 100),  2),
    ("SUSHI RESTAURANT",            (40, 90),   2),
    ("MARRIOTT HOTELS",             (180, 320), 0.2),
]

AMEX_PAYMENTS = [
    # Payment credit (negative in Amex format)
    ("ONLINE PAYMENT THANK YOU", (-700, -1200), 1),
]

BOFA_TXNS = [
    # (payee, address, amount_signed)   BofA: negative=expense, positive=refund
    # amount range, freq
    ("SHELL OIL 57444226800",        "SAN FRANCISCO CA",  (-45, -70),   2),
    ("TARGET 00014450",              "SAN FRANCISCO CA",  (-35, -110),  2),
    ("MCDONALDS F24319",             "SAN FRANCISCO CA",  (-8, -14),    2),
    ("PANERA BREAD #601998",         "SAN FRANCISCO CA",  (-11, -18),   2),
    ("WALGREENS #4501",              "SAN FRANCISCO CA",  (-5, -38),    1),
    ("USPS PO 0547120306",           "SAN FRANCISCO CA",  (-6, -22),    1),
    ("PLANET FITNESS",               "DALY CITY CA",      (-25, -25),   1),
    ("BOOKSHOP ORG",                 "",                  (-14, -38),   1),
    ("ONLINE PAYMENT THANK YOU",     "",                  (400, 800),   1),  # positive = payment
]

# ── Monarch Money categories & accounts ───────────────────────────────────────

MONARCH_ACCOUNTS = [
    "CREDIT CARD (...4591)",          # Chase Credit
    "CHASE COLLEGE (...7823)",        # Chase Checking
    "Blue Cash Preferred® (...2847)", # Amex
    "Customized Cash Rewards World Mastercard Card (...3901)",  # BofA
    "Discover it Card (...6124)",     # Discover
]

MONARCH_TXNS = [
    # (merchant, original_statement, category, account_index, amount_range, freq)
    ("Whole Foods",    "WHOLE FOODS MARKET",          "Groceries",              2, (-55, -160),  4),
    ("Trader Joe's",   "TRADER JOES #421",             "Groceries",              2, (-30, -120),  3),
    ("Costco",         "COSTCO WHOLESALE",             "Groceries",              2, (-90, -240),  2),
    ("Chipotle",       "CHIPOTLE MEXICAN GRILL",       "Restaurants & Bars",     0, (-12, -18),   3),
    ("Starbucks",      "STARBUCKS STORE #12749",       "Restaurants & Bars",     0, (-5, -12),    8),
    ("DoorDash",       "DOORDASH*MCDONALDS",           "Restaurants & Bars",     0, (-20, -55),   4),
    ("Uber Eats",      "UBER* EATS",                   "Restaurants & Bars",     0, (-18, -60),   3),
    ("Amazon",         "AMAZON.COM*2K8LQ9012",         "Shopping",               0, (-15, -200),  5),
    ("Nike",           "NIKE.COM",                     "Shopping",               0, (-60, -150),  1),
    ("Netflix",        "NETFLIX.COM",                  "Subscription",           0, (-15, -15),   1),
    ("Spotify",        "SPOTIFY USA",                  "Subscription",           0, (-11, -11),   1),
    ("Uber",           "UBER *TRIP",                   "Taxi & Ride Shares",     0, (-9, -32),    5),
    ("Lyft",           "LYFT *RIDE",                   "Taxi & Ride Shares",     0, (-8, -28),    3),
    ("Shell",          "SHELL OIL",                    "Gas",                    3, (-45, -72),   3),
    ("Chevron",        "CHEVRON",                      "Gas",                    3, (-42, -68),   1),
    ("AMC Theaters",   "AMC THEATERS",                 "Entertainment & Recreation", 4, (-18, -35), 2),
    ("Planet Fitness", "PLANET FITNESS",               "Fitness",                2, (-25, -25),   1),
    ("CVS Pharmacy",   "CVS PHARMACY",                 "Medical",                0, (-8, -55),    2),
    ("Verizon",        "VERIZON WIRELESS",             "Phone",                  2, (-95, -95),   1),
    ("Comcast",        "COMCAST INTERNET",             "Internet & Cable",       1, (-75, -75),   1),
    ("Rent",           "CITYVIEW APARTMENTS RENT",     "Rent",                   1, (-1850, -1850),1),
    ("Geico",          "GEICO PAYMENT",                "Insurance",              1, (-148, -148), 1),
    ("Paycheck",       "ACME CORP DIRECT DEPOSIT",     "Paychecks",              1, (5200, 5200), 2),
    ("Fidelity",       "FIDELITY INVESTMENTS",         "Transfer",               1, (-500, -500), 1),
    ("Southwest Airlines","SOUTHWEST AIRLINES",        "Travel & Vacation",      0, (-200, -420), 0.3),
    ("Airbnb",         "AIRBNB * HMXX4923",            "Travel & Vacation",      0, (-150, -550), 0.3),
    ("Chase CC Payment","CHASE CREDIT CARD PAYMENT - THANK YOU","Credit Card Payment",1,(-1500,-2500),1),
    ("Amex Payment",   "AMEX PAYMENT - THANK YOU",    "Credit Card Payment",     1, (-700, -1100),1),
    ("BofA Payment",   "BOFA PAYMENT THANK YOU",      "Credit Card Payment",     1, (-400, -800), 1),
    ("Transfer",       "TRANSFER TO SAVINGS",          "Transfer",               1, (-500, -1000),1),
]

# ── Writers ───────────────────────────────────────────────────────────────────

def write_chase_credit(path: Path, months: int):
    """
    Chase Credit Card CSV format:
    Transaction Date, Post Date, Description, Category, Type, Amount, Memo
    Amount: positive = expense, negative = payment/credit
    """
    rows = []
    for m in range(months):
        year, month = months_back(m)
        for desc, (lo, hi), cat, freq in CHASE_CREDIT_TXNS:
            for _ in range(poisson_count(freq)):
                d = rand_date(year, month)
                post = d + timedelta(days=random.randint(1, 3))
                amount = rnd(lo, hi)   # positive = expense
                rows.append([fmt(d), fmt(post), desc, cat, "Sale", amount, ""])

        # One payment per month (negative on CC statement)
        for desc, (lo, hi), freq in CHASE_CREDIT_PAYMENTS:
            d = rand_date(year, month)
            post = d + timedelta(days=1)
            amount = -rnd(lo, hi)  # negative = credit
            rows.append([fmt(d), fmt(post), desc, "Payment", "Payment", amount, ""])

    rows.sort(key=lambda r: r[0])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"])
        w.writerows(rows)
    print(f"  {path.name}: {len(rows)} rows")


def write_chase_checking(path: Path, months: int):
    """
    Chase Checking CSV format:
    Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
    Amount: negative = debit, positive = credit (already signed)
    """
    rows = []
    balance = 8500.00
    for m in range(months - 1, -1, -1):   # oldest first for running balance
        year, month = months_back(m)
        month_rows = []
        for desc, (lo, hi), txn_type, freq in CHASE_CHECKING_TXNS:
            for _ in range(poisson_count(freq)):
                d = rand_date(year, month)
                amount = rnd(lo, hi)   # already signed
                detail = "CREDIT" if amount > 0 else "DEBIT"
                month_rows.append([d, detail, desc, amount, txn_type, None, ""])

        month_rows.sort(key=lambda r: r[0])
        for r in month_rows:
            balance += r[3]
            r[5] = round(balance, 2)
            r[0] = fmt(r[0])
            rows.append(r)

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Details", "Posting Date", "Description", "Amount", "Type", "Balance", "Check or Slip #"])
        w.writerows(rows)
    print(f"  {path.name}: {len(rows)} rows")


def write_amex(path: Path, months: int):
    """
    Amex CSV format:
    Date, Description, Card Member, Account #, Amount
    Amount: positive = expense (parser flips sign), negative = payment
    """
    rows = []
    acct = "-72004-28047"    # last 5 digits → 28047 → account name "Amex *28047"
    member = "DEMO USER"

    for m in range(months):
        year, month = months_back(m)
        for desc, (lo, hi), freq in AMEX_TXNS:
            for _ in range(poisson_count(freq)):
                d = rand_date(year, month)
                amount = rnd(lo, hi)   # positive = expense (parser flips to negative)
                rows.append([fmt(d), desc, member, acct, amount])

        for desc, (lo, hi), freq in AMEX_PAYMENTS:
            for _ in range(poisson_count(freq)):
                d = rand_date(year, month)
                amount = rnd(lo, hi)   # negative = payment
                rows.append([fmt(d), desc, member, acct, amount])

    rows.sort(key=lambda r: r[0])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Card Member", "Account #", "Amount"])
        w.writerows(rows)
    print(f"  {path.name}: {len(rows)} rows")


def write_bofa(path: Path, months: int):
    """
    Bank of America CSV format:
    Posted Date, Reference Number, Payee, Address, Amount
    Amount: negative = expense, positive = payment/credit
    """
    rows = []
    for m in range(months):
        year, month = months_back(m)
        for payee, address, (lo, hi), freq in BOFA_TXNS:
            for _ in range(poisson_count(freq)):
                d = rand_date(year, month)
                amount = rnd(lo, hi)   # already signed correctly
                ref = uuid.uuid4().hex[:12].upper()
                rows.append([fmt(d), ref, payee, address, amount])

    rows.sort(key=lambda r: r[0])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Posted Date", "Reference Number", "Payee", "Address", "Amount"])
        w.writerows(rows)
    print(f"  {path.name}: {len(rows)} rows")


def write_monarch(path: Path, months: int):
    """
    Monarch Money CSV format:
    Date, Merchant, Category, Account, Original Statement, Notes, Amount, Tags, Owner, Business Entity
    Amount: negative = expense, positive = income
    """
    rows = []
    for m in range(months):
        year, month = months_back(m)
        for merchant, orig, category, acct_idx, (lo, hi), freq in MONARCH_TXNS:
            for _ in range(poisson_count(freq)):
                d = rand_date(year, month)
                amount = rnd(lo, hi)   # already signed
                acct = MONARCH_ACCOUNTS[acct_idx]
                rows.append([
                    fmt(d, "yyyy-mm-dd"),
                    merchant,
                    category,
                    acct,
                    orig,
                    "",        # Notes
                    amount,
                    "",        # Tags
                    "Demo User",
                    "",        # Business Entity
                ])

    rows.sort(key=lambda r: r[0])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Merchant", "Category", "Account", "Original Statement",
                    "Notes", "Amount", "Tags", "Owner", "Business Entity"])
        w.writerows(rows)
    print(f"  {path.name}: {len(rows)} rows")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing demo CSVs to {OUT_DIR}/\n")

    write_chase_credit(OUT_DIR / "Chase4591_Activity.csv",   MONTHS)
    write_chase_checking(OUT_DIR / "Chase7823_Activity.csv", MONTHS)
    write_amex(OUT_DIR / "amex_activity.csv",                MONTHS)
    write_bofa(OUT_DIR / "stmt3901_activity.csv",            MONTHS)
    write_monarch(OUT_DIR / "monarch_export.csv",            MONTHS)

    print(f"\nDone. Import these files from the app's Import tab.")
    print("The Monarch file covers all 5 accounts in one import.")
