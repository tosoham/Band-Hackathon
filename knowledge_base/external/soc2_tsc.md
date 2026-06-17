---
source: AICPA Trust Services Criteria (SOC 2)
license: Paraphrased control summaries for RFP evidence. Not a substitute for the canonical TSC text.
url_reference: https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2
summary: Common Criteria CC1-CC9, mapped to BandGate vendor evidence.
---

# CC1.1 Control Environment — Commitment to Integrity and Ethical Values
Approved Wording: SentinelAI's Code of Conduct is signed by every employee at hire and re-affirmed annually. Ethics violations route through the independent compliance hotline.

# CC1.2 Board Oversight
Approved Wording: The Board's Risk and Audit Committee receives quarterly security and compliance reports.

# CC1.3 Organizational Structure
Approved Wording: Security, Privacy, and Compliance functions report to the CISO and Chief Privacy Officer with independent escalation paths.

# CC2.1 Communication and Information — Internal
Approved Wording: Security policies are published internally and version-controlled. Material updates trigger mandatory training.

# CC2.2 Communication and Information — External
Approved Wording: Customer-facing security disclosures live in the trust center and are updated within 5 business days of material changes.

# CC3.1 Risk Assessment
Approved Wording: A formal risk assessment is conducted annually and updated when systems materially change. Risks are tracked to closure with named owners.

# CC4.1 Monitoring Activities
Approved Wording: Control effectiveness is monitored continuously via automated control checks plus quarterly internal audit reviews.

# CC5.1 Control Activities — Selection and Development
Approved Wording: Controls are selected against the SOC 2 TSC and mapped to NIST 800-53 r5 and ISO 27001 Annex A.

# CC6.1 Logical and Physical Access — Restrict Logical Access
Approved Wording: All access requires MFA. Administrative access requires hardware-backed MFA, vaulted credentials, and recorded sessions.

# CC6.2 Logical and Physical Access — Authentication
Approved Wording: Customer SSO is supported via SAML 2.0 and OIDC. Local accounts require 14+ character passwords with breach-list screening.

# CC6.3 Authorization
Approved Wording: Role assignments require approver authorization and are logged. Privileged role activation is time-boxed and reviewed monthly.

# CC6.6 External Access
Approved Wording: External access is brokered through the API gateway with mTLS for partner integrations.

# CC6.7 Restrict Transmission of Information
Approved Wording: Data in transit uses TLS 1.2 or higher with HSTS preload. Internal service traffic uses mTLS.

# CC6.8 Configuration Management — Prevent or Detect Unauthorized Software
Approved Wording: Endpoint compliance is enforced via MDM. Unsigned binaries are blocked from execution.

# CC7.1 Detection of Configuration Changes
Approved Wording: Configuration drift is detected within 5 minutes via continuous attestation; deviations trigger ticketed remediation.

# CC7.2 Monitoring for Anomalies
Approved Wording: Anomaly detection covers identity, data exfiltration, and supply-chain telemetry. Detections feed the SOC queue with a 15-minute SLA.

# CC7.3 Evaluation of Security Events
Approved Wording: Confirmed security events follow the incident response runbook. Customer notification timelines are governed by the DPA.

# CC7.4 Incident Response Plan
Approved Wording: The IR plan is exercised in two tabletop exercises and one full simulation per year.

# CC8.1 Change Management
Approved Wording: All production changes pass automated tests, peer review, and CAB sign-off where required.

# CC9.1 Risk Mitigation
Approved Wording: Residual risks above the board-approved tolerance trigger executive review and customer disclosure when material.

# CC9.2 Vendor Risk Management
Approved Wording: Subprocessors are reviewed annually with documented security questionnaires and contractual flow-down obligations.
