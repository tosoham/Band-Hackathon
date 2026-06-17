---
source: FedRAMP — Federal Risk and Authorization Management Program
license: Paraphrased baseline summary for RFP evidence. Not a substitute for the canonical FedRAMP documentation.
url_reference: https://www.fedramp.gov/
summary: Moderate impact level baseline overview, used by BandGate as evidence on federal questions.
---

# FedRAMP Status (Current)
Approved Wording: SentinelAI is FedRAMP Moderate "in process," not authorized. We do not claim FedRAMP authorization in any buyer-facing document until the agency Authority To Operate is signed.

# FedRAMP Moderate Baseline — Scope
Approved Wording: The FedRAMP Moderate baseline applies to systems with moderate impact for Confidentiality, Integrity, and Availability. SentinelAI's Government Cloud is engineered to that baseline.

# FedRAMP Boundary
Approved Wording: The authorization boundary covers the SentinelAI control plane, detection engines, and the GovCloud data plane. Customer integrations outside the boundary are not part of the package.

# FedRAMP Continuous Monitoring
Approved Wording: Continuous Monitoring includes monthly vulnerability scans, monthly POA&M updates, and annual assessments by an accredited 3PAO.

# FedRAMP Personnel Screening
Approved Wording: All personnel with logical access to GovCloud are U.S. persons screened to NIST SP 800-53 PS-3 standards. Background checks are renewed every 5 years.

# FedRAMP Data Residency
Approved Wording: GovCloud workloads remain within continental U.S. AWS regions. Support engineering follows the same residency boundary.

# FedRAMP Boundary — Non-Federal Use
Approved Wording: Commercial customers are served from commercial regions and are not subject to GovCloud controls. Statements of FedRAMP coverage apply only to GovCloud workloads.

# FedRAMP Incident Reporting
Approved Wording: US-CERT reporting timelines (1, 4, 8 hours by severity) are honored for confirmed incidents within the authorization boundary.

# FedRAMP Cryptographic Modules
Approved Wording: All cryptography in GovCloud uses FIPS 140-2 validated modules. Non-FIPS modules are not permitted in the boundary.

# FedRAMP Reciprocity
Approved Wording: Other agency ATOs are honored through the FedRAMP reciprocity model where the package is in the marketplace and the customer issues the corresponding ATO letter.
