"""Synthetic AR demo-data generator.

Run once before ``streamlit run app.py`` to produce a sample accounts-receivable
CSV and to seed the ChromaDB policy index with AR-specific policy language, so
the AR Automation tab has realistic data and grounded RAG context to demo
against.

Usage:
    python generate_ar_data.py
"""

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.rag_index import build_index

_PROJECT_ROOT = Path(__file__).resolve().parent
_CSV_PATH = _PROJECT_ROOT / "sample_ar_invoices.csv"
_POLICY_PATH = _PROJECT_ROOT / "policies" / "ar_receivables_policy.md"

# (tier label, min days overdue, max days overdue)
_TIERS = [
    ("Current", 0, 30),
    ("At Risk", 31, 60),
    ("Overdue", 61, 90),
    ("Critical", 91, 180),
]
_INVOICES_PER_TIER = 4  # 4 tiers x 4 = 16 invoices, within the 15-20 target

_FICTIONAL_CLIENTS = [
    "Bluewater Logistics Co.", "Northfield Office Supply", "Cascade Ridge Builders",
    "Ironvale Manufacturing", "Solstice Retail Group", "Amberton Consulting LLC",
    "Prairie Bell Foods", "Copperline Industrial", "Wrenhollow Media",
    "Granite Creek Distributors", "Vantage Point Analytics", "Marlowe & Finch Design",
    "Silverbrook Textiles", "Eastgate Hardware", "Fernway Dental Partners",
    "Oakmoor Freight Systems",
]

_POLICY_MARKDOWN = """# Accounts Receivable Payment Terms & Collections Policy
**Classification: Internal Use Only**
**Document Owner: Accounts Receivable / Collections**
**Effective Date: January 1, 2025 | Review Cycle: Annual**

---

## 1. Purpose

This policy defines standard payment terms, late-payment consequences, and the
required collections follow-up cadence for all outstanding customer invoices.

---

## 2. Payment Terms

- Standard payment terms are net 30 from the invoice date unless a signed
  contract specifies otherwise.
- Invoices are considered current from 0 to 30 days past the due date and
  require no collections action beyond the standard payment reminder.

## 3. Late Fees

- Invoices unpaid beyond 60 days from the due date are subject to a 1.5%
  monthly late fee applied to the outstanding balance.
- Late fees continue to accrue monthly until the invoice is paid in full or a
  payment plan is formally agreed to in writing.

## 4. Collections Escalation

- Accounts unpaid beyond 90 days are escalated to senior management for
  review and direct outreach.
- Accounts in the 31-60 day range should receive a firm written reminder
  referencing the original invoice terms and any applicable late fee.
- Accounts in the 61-90 day range require an urgent follow-up email and a
  documented phone contact attempt within 5 business days.
- Any account exceeding 90 days overdue must include the account's manager
  or director as a CC on all further correspondence.

## 5. Dispute Handling

- Clients disputing an invoice must submit the dispute in writing within 15
  days of the invoice due date; disputed amounts are held from late-fee
  accrual pending resolution.

## 6. Payment Plans

- Payment plans may be offered for accounts in the Overdue or Critical tiers
  at the discretion of the Collections Manager, and must be documented with
  a signed installment schedule.
"""


def _random_due_date(days_overdue: int, today: date) -> date:
    return today - timedelta(days=days_overdue)


def _generate_invoices() -> pd.DataFrame:
    today = date.today()
    clients = _FICTIONAL_CLIENTS.copy()
    random.shuffle(clients)

    rows = []
    invoice_num = 1001
    client_idx = 0
    for tier_label, lo, hi in _TIERS:
        for _ in range(_INVOICES_PER_TIER):
            days_overdue = random.randint(lo, hi)
            due_date = _random_due_date(days_overdue, today)
            amount_due = round(random.uniform(500, 50000), 2)
            client_name = clients[client_idx % len(clients)]
            client_idx += 1
            rows.append({
                "invoice_number": f"INV-{invoice_num}",
                "client_name": client_name,
                "amount_due": amount_due,
                "due_date": due_date.isoformat(),
                "days_overdue": days_overdue,
            })
            invoice_num += 1

    df = pd.DataFrame(rows)
    return df.sample(frac=1, random_state=None).reset_index(drop=True)


def main() -> None:
    df = _generate_invoices()
    df.to_csv(_CSV_PATH, index=False)
    print(f"Wrote {len(df)} synthetic invoices to {_CSV_PATH}")

    _POLICY_PATH.write_text(_POLICY_MARKDOWN, encoding="utf-8")
    build_index()
    print(f"Seeded ChromaDB policy index with {_POLICY_PATH.name} (AR payment-terms language).")


if __name__ == "__main__":
    main()
