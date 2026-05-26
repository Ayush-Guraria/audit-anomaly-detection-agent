# Escalation Thresholds and Authority Matrix
**Classification: Internal Use Only**
**Document Owner: BSA/AML Compliance Officer**
**Effective Date: January 1, 2025 | Review Cycle: Annual**

---

## 1. Purpose

This document defines the quantitative thresholds and authority levels governing when a fraud or AML case must be escalated beyond the Level 1 analyst tier. Escalation decisions must be timely and well-documented; failure to escalate in accordance with this matrix may constitute a BSA compliance violation.

---

## 2. Risk Score Escalation Bands

The automated anomaly detection system assigns each flagged transaction a risk score from 0–100. Actions by band:

| Score Band | Risk Tier | Required Action |
|---|---|---|
| 0 – 40 | Routine | Analyst review within 72 hours; no hold required |
| 41 – 70 | Elevated | Hold transaction; Level 1 review within 24 hours |
| 71 – 85 | High | Hold transaction; Level 2 review within 4 hours |
| 86 – 100 | Critical | Immediate hold; Level 2 + BSA Officer notification within 1 hour |

A score of 86 or above on any single transaction triggers an automatic FCMS page to the on-call Senior Fraud Investigator regardless of time of day.

---

## 3. Dollar-Amount Authority Matrix

Escalation requirements based on transaction value, independent of risk score:

| Transaction Amount | Escalation Level | Required Approver |
|---|---|---|
| < $10,000 | Level 1 | Frontline Fraud Analyst |
| $10,000 – $49,999 | Level 2 | Senior Fraud Investigator or Fraud Operations Supervisor |
| $50,000 – $99,999 | BSA Review | BSA Compliance Officer must be notified within 2 hours |
| ≥ $100,000 | SAR Threshold | BSA Officer initiates SAR filing evaluation; General Counsel notified |

Wire transfers ≥ $10,000 trigger automatic CTR (Currency Transaction Report) generation per 31 CFR § 1010.311, separate from any fraud escalation workflow.

---

## 4. Time-Based Auto-Escalation

Cases that remain unresolved beyond their SLA window are automatically re-tiered:

- **High-risk case unresolved > 2 hours**: escalates from Level 1 to Level 2 queue automatically
- **Any case unresolved > 48 hours**: Fraud Operations Manager receives automated alert; case locked to Level 2
- **Critical-score case unresolved > 1 hour**: BSA Officer and Chief Risk Officer receive automated email notification

Time-based escalation cannot be waived by the analyst. Only the Fraud Operations Manager may pause the escalation clock, and only with documented justification in FCMS.

---

## 5. Cross-Border and High-Risk Jurisdiction Rules

Transactions involving countries on the FATF High-Risk Jurisdictions list receive a mandatory +30 risk score uplift and require Level 2 review regardless of amount. Current monitored jurisdictions are reviewed quarterly by the BSA team.

### 5.1 Crypto-Adjacent Transactions
Transactions to or from known cryptocurrency exchange merchant IDs (maintained on the internal MCC watchlist) require:
- Level 2 review for amounts ≥ $1,000
- BSA Officer notification for amounts ≥ $5,000
- SAR filing evaluation for any pattern of three or more such transactions totaling ≥ $10,000 within a 30-day window (structuring indicator)

---

## 6. Escalation Communication Standards

All escalations must be logged in FCMS with:
1. The triggering threshold (score band, dollar amount, or time-based)
2. The notified party and method of notification (system alert, phone, email)
3. Timestamp of notification
4. Acknowledging response from the escalation recipient (required within 30 minutes for Critical cases)

Undocumented escalations are treated as non-escalations for audit and regulatory examination purposes.
