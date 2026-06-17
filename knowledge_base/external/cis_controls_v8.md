---
source: Center for Internet Security — Critical Security Controls v8
license: Paraphrased control summaries for RFP evidence.
url_reference: https://www.cisecurity.org/controls
summary: First ten Critical Security Controls mapped to BandGate vendor evidence.
---

# Control 1 Inventory and Control of Enterprise Assets
Approved Wording: SentinelAI maintains a continuously updated asset inventory across cloud, container, and endpoint estates. Unauthorized assets are quarantined within 60 minutes.

# Control 2 Inventory and Control of Software Assets
Approved Wording: Allow-listed software is enforced at the endpoint. Containers are built from a hardened base image with SBOM verification.

# Control 3 Data Protection
Approved Wording: Data is classified at ingestion. Tenant data is encrypted at rest and in transit. DLP policies block known exfiltration channels.

# Control 4 Secure Configuration of Enterprise Assets and Software
Approved Wording: CIS Benchmarks are the baseline for production hosts and containers. Deviations require a documented exception with compensating controls.

# Control 5 Account Management
Approved Wording: All accounts are provisioned through IDP. Privileged accounts are vaulted and require time-boxed activation.

# Control 6 Access Control Management
Approved Wording: Role definitions follow least privilege and are reviewed quarterly. Just-in-time elevation is logged.

# Control 7 Continuous Vulnerability Management
Approved Wording: Authenticated scans run weekly. SLAs: critical 7 days, high 30 days, medium 90 days. Exceptions require security approval.

# Control 8 Audit Log Management
Approved Wording: Logs are centralized in an immutable store with tenant separation. Default retention 365 days; customer-configurable.

# Control 9 Email and Web Browser Protections
Approved Wording: Inbound mail is filtered for phishing, malware, and impersonation. Browser endpoints are MDM-enrolled with allow-listed extensions.

# Control 10 Malware Defenses
Approved Wording: EDR is deployed on all endpoints and production hosts with behavior-based detection mapped to MITRE ATT&CK.
