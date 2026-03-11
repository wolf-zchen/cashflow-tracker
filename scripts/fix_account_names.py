"""
Fix account names in the database to use the clean "Bank *XXXX" format.

Run from the project root:
    python scripts/fix_account_names.py [path/to/transactions.db]
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/transactions.db")

RENAMES = [
    # ── Chase credit cards: old "CC" format → "Credit" ──────────────────────
    ("Chase CC *2966",   "Chase Credit *2966"),
    ("Chase CC *4370",   "Chase Credit *4370"),
    ("Chase CC *4459",   "Chase Credit *4459"),
    ("Chase CC *6699",   "Chase Credit *6699"),
    ("Chase CC *1129",   "Chase Credit *1129"),
    ("Chase CC *9707",   "Chase Credit *9707"),

    # ── Chase: raw filenames left over from before parser fix ────────────────
    ("Chase4370_Activity20260201_20260228_20260310", "Chase Credit *4370"),
    ("Chase4459_Activity20260201_20260228_20260310", "Chase Credit *4459"),
    ("Chase6699_Activity20260201_20260228_20260310", "Chase Credit *6699"),
    ("Chase9707_Activity20260201_20260228_20260310", "Chase Credit *9707"),
    ("Chase9506_Activity_20260309",                  "Chase Checking *9506"),

    # ── BofA: year was extracted instead of account number ───────────────────
    ("Bank of America CC *2025",  "BofA *0424"),
    ("Bank of America CC *2026",  "BofA *0424"),
    ("Bank of America *2025",     "BofA *0424"),
    ("Bank of America *2026",     "BofA *0424"),
    ("February2026_0424",         "BofA *0424"),
    ("February2025_0424",         "BofA *0424"),

    # ── Amex: old format and raw filenames ───────────────────────────────────
    ("American Express credit_card", "Amex *52003"),
    ("activity",                     "Amex *52003"),
    ("activity (1)",                 "Amex *52003"),
    ("American Express",             "Amex *52003"),
]

def fix(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    total = 0
    for old, new in RENAMES:
        cur.execute("SELECT COUNT(*) FROM transactions WHERE account_name = ?", (old,))
        n = cur.fetchone()[0]
        if n > 0:
            cur.execute("UPDATE transactions SET account_name = ? WHERE account_name = ?", (new, old))
            # If target already exists in accounts table, just delete the old row;
            # otherwise rename it.
            cur.execute("SELECT COUNT(*) FROM accounts WHERE name = ?", (new,))
            if cur.fetchone()[0] > 0:
                cur.execute("DELETE FROM accounts WHERE name = ?", (old,))
            else:
                cur.execute("UPDATE accounts SET name = ? WHERE name = ?", (new, old))
            print(f"  {old!r:55s} → {new!r}  ({n} txns)")
            total += n

    conn.commit()
    conn.close()
    print(f"\nDone. Updated {total} transactions.")

if __name__ == "__main__":
    print(f"Fixing account names in: {DB_PATH}\n")
    fix(DB_PATH)
