# ISMS Functionality Specification

> **STATUS**: 📋 Future State Specification (Not Yet Implemented)
> **LAST UPDATED**: 2025-10-27
> **IMPLEMENTATION TARGET**: Q2 2026
> **ARCHITECTURE**: Aligned with OpenAMI 4-Layer Architecture

## Purpose

Define the built-in Information Security Management System (ISMS) capabilities the AMI Orchestrator platform must provide so organisations can operate and evidence an ISO/IEC 27001-aligned ISMS without relying on external tooling.

**Current Implementation Status**: The compliance module is in specification phase with no backend implementation yet. See [compliance/docs/research/CURRENT_IMPLEMENTATION_STATUS.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/CURRENT_IMPLEMENTATION_STATUS.md) for detailed progress tracking.

## Scope

The specification applies to the platform core services, admin console and compliance workspaces. It covers functionality for policy governance, risk management, control operations, evidence collection and audit support. The spec assumes integration with existing compliance content (EU AI Act, ISO/IEC 42001, NIST AI RMF) and avoids duplicating specialist tooling such as SIEM or ticketing systems.

### Architectural Context

This ISMS functionality will be implemented as part of **Layer 4: Governance** in the OpenAMI architecture:

- **Layer 0 Axioms**: Immutable safety constraints encoding ISO/IEC 27001 Annex A controls
- **Compliance Manifest ($\mathcal{CM}$)**: Authoritative policy and control specification
- **SPN Integration**: Secure Process Nodes enforce controls at execution boundaries
- **CST Provenance**: Cryptographic State Tokens provide immutable evidence chains
- **Matrix Protocol**: Secure communications backbone for incident response and human oversight (see [compliance/docs/research/ISMS-MATRIX-INTEGRATION-PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/ISMS-MATRIX-INTEGRATION-PLAN.md))

Traditional ISMS capabilities described below map to these OpenAMI primitives.

## Stakeholders and Roles

* ISMS Owner / Chief Information Security Officer (CISO)
* Control Owners and Delegates
* Compliance and Audit Teams
* Engineering and Operations leads
* External auditors or assessors (read-only access)

## Functional Requirements

1. **ISMS Dashboard**
   * Surface current certification scope, statement of applicability (SoA) status, pending tasks and risk posture metrics.
   * Provide drill-down cards for policy updates, overdue controls, corrective action plans and upcoming audits.

2. **Policy and Document Governance**
   * Version-controlled policy repository with approval workflows, change history and publication state.
   * Link policies to relevant ISO/IEC 27001 clauses, Annex A controls and EU AI Act obligations.
   * Support acknowledgement tracking for workforce sign-off.

3. **Risk Register and Assessment Engine**
   * Capture assets, threats, vulnerabilities, existing controls and risk owners.
   * Allow configurable risk methodologies (qualitative and semi-quantitative) with scoring matrices aligned to Clause 6.1.2.
   * Maintain assessment history, review cadence, residual risk justification and acceptance approvals.

4. **Control Library and Statement of Applicability**
   * Model ISO/IEC 27001 Annex A controls plus organisation-defined controls.
   * For each control store implementation narrative, evidence artefacts, effectiveness status, owners and review logs.
   * Auto-generate the SoA, highlighting inclusions, exclusions with rationale, implementation state and linked evidence.

5. **Evidence and Task Management**
   * Provide structured data store for uploading, tagging and expiring evidence packages (documents, screenshots, system exports).
   * Schedule recurring evidence collection tasks with reminders and escalation paths.
   * Support segregation between confidential evidence and auditor-visible material.

6. **Corrective and Preventive Actions (CAPA)**
   * Log nonconformities, audit findings, incidents and risk treatment plans with root-cause analysis fields.
   * Track remediation tasks, owners, due dates, verification results and closure approvals.

7. **Audit Workspace**
   * Generate read-only auditor portals scoped to selected controls, risks and evidence.
   * Provide conversation threads for clarifications and maintain immutable audit trail of disclosures.

8. **Integration Hooks**
   * Expose APIs/webhooks to ingest alerts from vulnerability management, SIEM or ticketing systems to create risks or CAPA items.
   * Publish events for task assignments and status changes to external workflow tools (e.g. Jira, Slack).

9. **Reporting and Analytics**
   * Deliver exportable reports for management review (Clause 9.3), board updates and regulatory submissions.
   * Provide trend charts for risk levels, control maturity, evidence freshness and incident closure metrics.

## Non-Functional Requirements

* **Security:** Apply platform RBAC with least privilege, MFA enforcement and detailed access logging for all ISMS actions.
* **Data Retention:** Configurable retention policies per evidence class; default minimum 10 years for records supporting Article 18/EU AI Act and ISO/IEC documentation.
* **Auditability:** Immutable change history for policies, risks, controls and evidence, with cryptographic signing or hash receipts for supporting artefacts.
* **Availability:** Target 99.5% monthly uptime for ISMS services; graceful degradation must preserve read-only access to policies and evidence.
* **Performance:** Dashboards and registry views respond within 2 seconds for standard dataset sizes (up to 5k controls/evidence links).

## Integration with Compliance Modules

* Link risk register entries to EU AI Act Article 9 requirements and ISO/IEC 42001 risk treatments to avoid duplicate reviews.
* Synchronise provider/deployer obligations from EU AI Act documentation so that control owners can track Article 16/26 duties directly inside the ISMS.
* Allow mapping of ISMS controls to blueprint modules in `/compliance/docs/consolidated/blueprint` for unified governance reporting.

## Implementation Considerations

* **Phased Delivery Timeline**:
  - **Q4 2025**: Layer 0 Axioms formalization, Compliance Manifest schema, SPN abstraction
  - **Q1 2026**: Compliance backend scaffolding, risk register, evidence management
  - **Q2 2026**: Dashboard, SoA automation, auditor workspace, Matrix integration complete
* **Architecture Alignment**: Implement on OpenAMI primitives rather than traditional standalone systems:
  - Policies stored as Compliance Manifest constraints (versioned, signed)
  - Controls enforced through SPN pre/post checks
  - Evidence collected via CST provenance chains
  - Risk register integrated with Layer 0 Axiom violation tracking
* **Matrix Protocol Integration**: Incident response, human oversight approvals, and audit communications via end-to-end encrypted Matrix rooms (see [compliance/docs/research/ISMS-MATRIX-INTEGRATION-PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/ISMS-MATRIX-INTEGRATION-PLAN.md))
* **DataOps Foundation**: Reuse base module's UnifiedCRUD with 9 storage backend options (Postgres, Dgraph, MongoDB, Redis, Vault, Prometheus, pgvector, File, REST)
* **Migration Tooling**: Import legacy risk registers and policies (CSV/JSON) and bulk-link evidence files during Q2 2026 implementation

## Acceptance Criteria

* Demonstrate end-to-end creation of a risk assessment, control update and evidence upload with full audit history (CST provenance chain).
* Generate an SoA export that aligns with ISO/IEC 27001 Annex A controls and flags unmet controls.
* Show management-review report covering risk trends, control status and CAPA progress, ready for Clause 9.3 meetings.
* Provide an auditor workspace with restricted scope and logging of access/retrieval actions.
* **OpenAMI-Specific Criteria**:
  - Layer 0 Axioms encode all applicable ISO/IEC 27001 Annex A controls
  - SPN compliance checks successfully block operations violating controls
  - CST chains provide complete provenance for all ISMS activities
  - Matrix integration delivers <30 minute incident response time
  - Never-Jettison Guarantee verified: evolved system maintains original ISMS controls

---

## Related Documentation

- [Compliance Backend Specification](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/COMPLIANCE_BACKEND_SPEC.md) - Technical architecture
- [ISMS-Matrix Integration Plan](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/ISMS-MATRIX-INTEGRATION-PLAN.md) - Communications backbone
- [Current Implementation Status](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/CURRENT_IMPLEMENTATION_STATUS.md) - Progress tracking (0% complete as of 2025-10-27)
- OpenAMI System Architecture - 4-layer architecture
- [Executive Action Plan](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md) - Implementation roadmap

---

**Document Metadata**:
- **Created**: Prior to 2025-10-27
- **Updated**: 2025-10-27 (Aligned with OpenAMI architecture and current implementation status)
- **Next Review**: Q1 2026 (During compliance backend implementation)
- **Implementation Status**: 0% (Specification phase - no compliance backend code exists yet)
