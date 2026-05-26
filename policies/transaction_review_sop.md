# Transaction Review Standard Operating Procedure
**Classification: Internal Use Only**
**Document Owner: Operations Risk & Compliance**
**Effective Date: January 1, 2025 | Review Cycle: Semi-Annual**

---

## 1. Purpose

This SOP governs how Heartland Community Bank analysts triage, investigate, and resolve flagged transactions routed through the Fraud Case Management System (FCMS). Adherence ensures consistent customer outcomes, regulatory compliance, and accurate loss reporting.

---

## 2. Review Tier Structure

### 2.1 Level 1 — Frontline Fraud Analyst
Handles all incoming flagged items with a system-assigned risk score below 70. Responsible for:
- Reviewing transaction metadata and cardholder history
- Approving or declining the transaction hold
- Documenting rationale in FCMS within the SLA window

### 2.2 Level 2 — Senior Fraud Investigator
Handles items with risk score ≥ 70 or any case escalated from Level 1. Responsible for:
- Full account audit (last 90 days of activity)
- Cross-referencing against internal watchlists and FinCEN advisories
- Recommending SAR filing if warranted
- Coordinating with Law Enforcement Liaison when required

---

## 3. SLA Requirements

| Risk Tier | Maximum Review Window | Clock Start |
|---|---|---|
| High (score 71–100) | 4 hours | Time of flag |
| Medium (score 41–70) | 24 hours | Time of flag |
| Low (score 0–40) | 72 hours | Time of flag |

Missed SLAs must be reported to the Fraud Operations Manager by end of business on the day of breach. Three SLA breaches by the same analyst within a 30-day period trigger a performance review.

---

## 4. Customer Contact Procedures

### 4.1 Outbound Contact
For transactions on hold pending review, the analyst must attempt contact using the following sequence:
1. SMS/push notification to registered mobile number (immediate)
2. Outbound call to primary phone number on file (within 1 hour of flag)
3. Email to registered address (within 2 hours if call unanswered)

Customers have **2 hours** from first contact to respond before the transaction is automatically declined and a temporary block is placed on the payment method.

### 4.2 Cardholder Verification
Identity must be confirmed via Knowledge-Based Authentication (KBA) — minimum 3 of 5 challenge questions — before any hold is lifted over the phone.

---

## 5. Temporary Hold Procedures

- Maximum hold duration before mandatory escalation or release: **48 hours**
- Holds on amounts ≥ $25,000 require Level 2 sign-off before release regardless of risk score
- Any hold exceeding 48 hours without resolution must be escalated to the Fraud Operations Manager and documented with reason codes in FCMS

---

## 6. Transaction Disposition Outcomes

| Outcome Code | Description | Action Required |
|---|---|---|
| FR-01 | Confirmed Fraud | Decline, block instrument, open case |
| FR-02 | Suspected Fraud | Hold pending additional verification |
| FR-03 | False Positive | Release, document in FCMS, update risk model feedback |
| FR-04 | Customer Authorized | Release immediately, close case |

---

## 7. Documentation Standards

Every reviewed case must include: analyst ID, review timestamp, evidence summary (minimum 2 sentences), disposition code, and any customer contact log. Incomplete records are subject to QA audit and may result in case re-opening.
