# Anti-Fraud Guidelines
**Classification: Internal Use Only**
**Document Owner: Fraud Risk Management**
**Effective Date: January 1, 2025 | Review Cycle: Annual**

---

## 1. Purpose

These guidelines establish the minimum detection and response standards for fraudulent transaction activity across all payment channels operated by Heartland Community Bank. All fraud analysts, operations staff, and automated systems must adhere to these thresholds.

---

## 2. Automatic Flagging Thresholds

### 2.1 Single-Transaction Dollar Limits
Any card or ACH transaction meeting or exceeding the following amounts must be automatically queued for analyst review before settlement:

| Channel | Auto-Flag Threshold |
|---|---|
| Card-Present (in-branch/ATM) | $5,000 |
| Card-Not-Present (e-commerce) | $2,500 |
| ACH Debit | $3,000 |
| Wire Transfer (domestic) | $10,000 |
| Wire Transfer (international) | $5,000 |

### 2.2 Aggregate Velocity Limits
Transactions are evaluated in rolling windows. Breach of any single threshold triggers a hold:

- **24-hour window**: aggregate spend ≥ $15,000 across any combination of channels
- **7-day window**: aggregate spend ≥ $40,000 from a single account or device fingerprint
- **30-day window**: more than 3 flagged transactions from the same account, regardless of dollar amount

---

## 3. Card-Not-Present (CNP) Controls

CNP transactions carry elevated fraud risk and are subject to additional scrutiny:

- Any CNP transaction to a merchant category not previously used by the cardholder within the prior 90 days must pass a step-up authentication challenge.
- Transactions shipping to an address not matching the cardholder's billing address on file for more than 180 days require manual review if the amount exceeds $500.
- Three or more CNP declines within a 1-hour window automatically suspend the card pending cardholder confirmation.

---

## 4. Device and Identity Mismatch Rules

Mismatches between transaction metadata and cardholder profile trigger escalation:

- **Device fingerprint mismatch**: new device + transaction > $1,000 within first 24 hours of device registration → hold for review.
- **Geolocation anomaly**: transaction IP geolocates to a country not visited in the prior 12 months → automatic flag regardless of amount.
- **Billing/shipping address mismatch**: shipping state differs from billing state on orders > $750 → Level 1 review required.

---

## 5. High-Risk Merchant Categories

Transactions at the following MCCs receive a +20-point risk score uplift regardless of amount:

- MCC 6051 (Non-Financial Institutions — Foreign Currency)
- MCC 7995 (Betting/Casino Gambling)
- MCC 5912 (Drug Stores — selected jurisdictions)
- MCC 4829 (Money Transfer)

---

## 6. Recordkeeping

All flagged transactions and analyst decisions must be logged in the Fraud Case Management System (FCMS) within 2 hours of resolution. Logs are retained for a minimum of 7 years per BSA requirements.
