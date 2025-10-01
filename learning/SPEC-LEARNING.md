# AMI Learning Module Specification

## 1. Mission & Scope
- Establish a first-class `learning/` module that delivers shared infrastructure for building, training, evaluating, and serving PyTorch models across AMI domains.
- Provide Model Context Protocol (MCP) tooling so orchestration layers, agents, and external clients can schedule training runs, manage datasets, and retrieve model artefacts through consistent contracts.
- Replace ad-hoc research stacks (e.g. `domains/predict`) with a production-grade platform that respects Base DataOps patterns, compliance checkpoints, and compute guardrails (`AMI_COMPUTE_PROFILE`).

## 2. Design Principles
- **Base-Native**: All metadata persists via `StorageModel` + `UnifiedCRUD` across graph/document/timeseries/vector stores; no bespoke ORM layers.
- **PyTorch-First, Extension-Friendly**: Core runtime assumes PyTorch but exposes interfaces so domains can plug in Lightning, Hugging Face, or custom trainers while reusing orchestration primitives.
- **Composable Pipelines**: Training, evaluation, deployment, and monitoring are BPMN-managed processes coordinated by the shared scheduler (see `backend/scheduling/SPEC-SCHEDULING.md`).
- **Infrastructure as MCP**: Expose every major action (dataset registration, experiment launch, inference job, model promotion) as MCP tools with strict RBAC and audit logging.
- **Reproducibility & Observability**: Standardise experiment configs, seed control, artefact hashing, and metrics capture to satisfy compliance documentation and post-market monitoring.
- **Secure-by-Default**: Reuse Base security models for ACLs, encrypt artefacts where required, and enforce classification policies on datasets and models.

## 3. Functional Pillars
1. **Dataset Management** – Versioned ingestion, validation, schema tracking, and storage placement using Base DataOps storages plus optional object storage connectors.
2. **Experiment & Training Orchestration** – Declarative job specs executed on configurable compute profiles, with BPMN workflows coordinating preprocessing, training, evaluation, and registration.
3. **Model Registry & Artefacts** – Central registry for checkpoints, signatures, lineage, compliance documents, and deployment readiness states.
4. **Inference & Serving Hooks** – Utilities and MCP tools to package models into torchscript/ONNX or LiveService wrappers consumed by domain-specific runtimes.
5. **Monitoring & Drift Detection** – Timeseries capture of metrics, post-deployment evaluation loops, and alert hooks for compliance/risk modules.
6. **Domain Adapters** – Lightweight SDK so domains (`domains/risk`, `domains/predict`, future modules) can declare tasks, datasets, and evaluation templates without reimplementing infrastructure.

## 4. Architecture Overview
1. **Learning API Layer** – Pydantic service modules (`learning/services/`) exposing dataset, experiment, model, and monitoring APIs reused by MCP and BPMN flows.
2. **Data Plane** – Connectors to document/graph storage for metadata, optional object storage for artefacts, vector store for embeddings, and Redis for feature caches.
3. **Training Orchestrator** – BPMN templates + scheduler integration to manage job lifecycle, including preprocessing tasks, trainer launch, evaluation, and promotion gates.
4. **Compute Adapter** – Abstract execution layer that dispatches workloads to local runners, dockerised workers, or remote nodes based on `AMI_COMPUTE_PROFILE` (`cpu`, `nvidia`, `intel`, `amd`).
5. **Artefact Registry** – Managed storage of model binaries, configuration manifests, generated docs (model cards), and lineage metadata with checksum validation.
6. **Monitoring Stack** – Metrics ingestion into timeseries storage, drift detectors, and hooks to risk/compliance modules for reporting.
7. **MCP Server** – `learning/mcp/learning_server.py` implementing FastMCP tooling for datasets, experiments, inference, and monitoring.

## 5. Data Model Blueprint
| Model | Purpose | Key Fields | Storage Targets |
| --- | --- | --- | --- |
| `Dataset` | Versioned dataset manifest. | `dataset_id`, `name`, `description`, `source_uri`, `schema_hash`, `validation_status`, `tags`, `classification` | `document`, `graph` |
| `DatasetVersion` | Concrete dataset snapshot. | `dataset_id`, `version`, `storage_location`, `row_count`, `feature_stats`, `created_at`, `checksum`, `lineage_refs` | `document` |
| `Experiment` | Training/evaluation run metadata. | `experiment_id`, `task_name`, `dataset_version`, `config`, `compute_profile`, `status`, `owner`, `metrics_summary` | `document`, `timeseries` |
| `TrainingRun` | Detailed runtime info for multi-stage jobs. | `run_id`, `experiment_id`, `stage` (`preprocess`, `train`, `eval`, `deploy`), `start_time`, `end_time`, `artifacts`, `logs_uri`, `exit_code` | `document`, `timeseries` |
| `ModelArtifact` | Registered model/checkpoint. | `model_id`, `version`, `framework` (PyTorch, Lightning), `artifact_uri`, `signature`, `target_runtime`, `status`, `metrics`, `linked_experiment`, `compliance_docs` | `document`, `graph`, `file` |
| `ServingEndpoint` | Deployment metadata. | `endpoint_id`, `model_id`, `runtime`, `uri`, `scaling_policy`, `health_state`, `last_validation` | `graph`, `document` |
| `MetricSnapshot` | Aggregated metrics for monitoring. | `entity_id` (model/endpoint), `timestamp`, `metric_name`, `value`, `threshold`, `breach_state`, `source` | `timeseries` |
| `DriftReport` | Drift/anomaly detection results. | `report_id`, `model_id`, `dataset_version`, `method`, `severity`, `details`, `recommended_action`, `evidence_refs` | `document`, `graph` |
| `ProcessObservation` | Normalised event emitted from Base DataOps CRUD hooks. | `observation_id`, `model_type`, `entity_uid`, `security_context`, `feature_vector`, `graph_context`, `ingested_at` | `document`, `timeseries` |
| `SOMNeuron` | Prototype state for the Growing Self-Organising Map. | `neuron_id`, `layer_id`, `prototype_vector`, `quantisation_error`, `hit_count`, `growth_epoch`, `adjacent_neuron_ids`, `status` | `vector`, `graph` |
| `ActivationModelState` | Online predictor weights that act on GSOM outputs. | `activation_id`, `target_signal`, `model_payload`, `learning_rate`, `regularisation_meta`, `last_update`, `performance_summary`, `linked_neuron_ids` | `document`, `file` |

### Model Conventions
- Extend `StorageModel` and reuse Base mixins for ACLs and timestamps. Register each model with `UnifiedCRUD` via `get_crud()` to ensure caching and multi-storage writes.
- Use shared enums for status fields (e.g. `ComplianceStatus`, risk severity) and introduce new enums only when not covered by Base/Compliance modules.
- Maintain lineage edges between datasets, experiments, models, and deployments for auditability and reproducibility.
- Reuse Base DataOps graph annotations (see `base/backend/dataops/models/bpmn_relational.py`) so GSOM neurons and activation states can live alongside BPMN flow nodes, security principals, and storage configs.

## 6. Pipeline & BPMN Alignment
- **Training Workflow Templates**: Provide BPMN definitions for supervised training, evaluation-only runs, hyperparameter search, and fine-tuning. Each template includes tasks for data validation, training launch, metric aggregation, model registration, and compliance review.
- **Event Triggers**: Scheduler event gateway listens for dataset updates, drift alerts, or manual requests to start workflows. Correlation keys use `experiment_id` or `model_id`.
- **Approval Gates**: Exclusive gateways enforce compliance/QA approval before promotion to production endpoints, integrating with `domains/risk` and `compliance` MCPs.
- **Rollback Handling**: BPMN compensation tasks tear down endpoints or revert model registry status when monitoring detects breaches.

## 7. Learning MCP Contract
- **Server:** `learning/mcp/learning_server.py`, derived from `FastMCPServerBase`, namespace `learning`.
- **Auth & RBAC:** Mutating tools require roles with `Permission.WRITE` or `Permission.ADMIN`; dataset/model artefacts marked `DataClassification.RESTRICTED` demand explicit access grants.

### Tool Catalogue
| Tool | Purpose | Inputs | Outputs |
| --- | --- | --- | --- |
| `learning.create_dataset` | Register dataset metadata and optionally upload artefacts. | `dataset_payload`, optional `upload_manifest`. | Dataset snapshot, version IDs, audit ref. |
| `learning.launch_experiment` | Start a BPMN-managed experiment. | `experiment_payload` (task type, dataset version, config, compute profile, schedule options). | `experiment_id`, BPMN `process_instance_id`, tracking URIs. |
| `learning.get_experiment_status` | Fetch status, metrics, and stage logs. | `experiment_id`, optional `include_runs`. | Experiment summary, stage breakdown, metrics, audit refs. |
| `learning.register_model` | Persist artefact produced outside the orchestrated flow. | `model_payload` (experiment link, artefact URI, signature). | Registered model record, validation checklist. |
| `learning.deploy_model` | Provision or update a serving endpoint. | `model_id`, deployment config, scaling policy. | Endpoint metadata, health check token, scheduler job ID. |
| `learning.run_inference` | Execute ad-hoc inference or batch scoring via managed runtime. | `model_id` or `endpoint_id`, `input_payload`, optional `batch_ref`. | Predictions, latency metrics, audit ref. |
| `learning.get_metrics` | Retrieve monitoring metrics & drift reports. | Filter (`entity_id`, metric names, time range). | Timeseries payload, breach annotations. |
| `learning.stream_events` | Subscribe to experiment lifecycle events (training progress, drift alerts). | `experiment_id`/`model_id`, subscription token. | MCP event stream with structured payloads. |

### Transport Expectations
- Support synchronous HTTP/SSE transports; long-running tasks return tracking IDs and rely on event streams for progress.
- Clients set `AMI_COMPUTE_PROFILE` or request-specific overrides; server validates availability before scheduling jobs.
- Every response includes `audit_ref` (UUID v7) for compliance traceability.

### Implementation Notes
- MCP handlers delegate to service layer; no business logic inside the transport adapters.
- Provide integration tests that spin up the MCP server in module isolation and exercise dataset creation, experiment launch, and model registration.
- Document CLI usage and example payloads in `learning/README.md`.

## 8. Integrations & Dependencies
- **Base Module**: Storage, security, UnifiedCRUD, worker pools, audit trail, metrics utilities.
- **Backend Scheduling**: BPMN workflows registered and executed via scheduler MCP; worker dispatch maps compute profile to `nodes` managed resources.
- **Nodes Module**: Use `nodes/scripts/setup_service.py` for provisioning GPU/accelerator dependencies; define managed processes for training runtimes.
- **Compliance Module**: Attach model cards, assessment reports, and evidence to `compliance` risk workflows; align with learning lifecycle documentation (`compliance/docs/research/OpenAMI/architecture/learning_lifecycle.md`).
- **Domains**: Provide SDK entrypoints (`learning/domain_sdk/`) so domain-specific modules register tasks/datasets without reimplementing pipelines; share configuration templates and BPMN sub-processes.
- **Risk Module**: Surface training failures, drift alerts, or unsafe model detections to `domains/risk` via MCP hooks for residual risk assessment.
- **Agents**: Expose agent tools enabling interactive experimentation and inference while respecting RBAC.

## 9. Operational Considerations
- **Configuration**: `.env` keys (`LEARNING_ARTIFACT_ROOT`, `LEARNING_DEFAULT_COMPUTE`, `LEARNING_ALLOWED_PROFILES`) align with Base settings; honour `AMI_HOST` for service discovery.
- **Environment Management**: Rely on `uv` environments per module; provide `requirements.env.<profile>.txt` files for CPU/GPU variants. Avoid modifying global `PATH`/`PYTHONPATH`.
- **Artefact Storage**: Default to repository workspace for local dev, S3-compatible buckets or object stores in production; integrate checksum validation and retention policies.
- **Testing Discipline**: Ship module-level pytest suites covering services, MCP handlers, BPMN workflow stubs, and PyTorch training smoke tests (with synthetic datasets).
- **Observability**: Emit structured logs and Prometheus metrics (loss curves, throughput, error rates); integrate with alerting for SLA breaches.
- **Security & Compliance**: Enforce data classification, document model approvals, generate model cards/datasheets, and log all actions via audit trail.
- **Failure Handling**: Provide automated retries for transient training errors, checkpoint resumption, and clean shutdown of partially failed jobs.

## 10. Implementation Roadmap
1. **Phase 0 – Foundations**: Create module scaffolding, Pydantic models, storage configs, and dataset/experiment services. Implement minimal MCP endpoints for dataset registration and experiment launch.
2. **Phase 1 – Training Orchestration**: Deliver BPMN workflows, compute adapter, and PyTorch runner (local CPU/GPU). Integrate scheduler events and audit logging.
3. **Phase 2 – Model Registry & Deployment**: Implement artefact registry, model promotion flow, inference runtime wrappers, and deployment MCP tools.
4. **Phase 3 – Monitoring & Drift**: Add metrics ingestion, drift detection, dashboard MCP tooling, and hooks into risk/compliance modules.
5. **Phase 4 – Domain SDK & Automation**: Release domain integration SDK, add templated pipelines for common tasks (classification, time-series, RL), and refine agent tooling for interactive experimentation.

## 11. Online GSOM & Activation Learning
- **Event Ingestion Pipeline**: Extend `UnifiedCRUD` (see `base/backend/dataops/services/unified_crud.py`) with non-blocking emitters that publish `ProcessObservation` payloads whenever BPMN, security, or storage models mutate. Normalise features with the same adapters used by orchestration so online learners consume consistent vectors.
- **Feature Service**: Maintain a streaming transformer that fuses BPMN telemetry (durations, retries, lane membership from `base/backend/dataops/models/bpmn_relational.py`), security context (roles, classifications from `base/backend/dataops/models/security.py`), and infrastructure descriptors (`StorageConfig`, `SSHConfig`). Cache per-entity histories to compute rolling statistics without replaying entire timelines.
- **Growing Self-Organising Map**: Implement an always-on GSOM microservice that ingests `ProcessObservation` batches, updates neuron prototypes incrementally, grows the topology when quantisation error exceeds adaptive thresholds, and prunes stale neurons. Persist prototypes in vector storage while mirroring neuron adjacency into the graph layer for downstream traversal.
- **Activation Layer**: Train lightweight online predictors (logistic/Poisson or shallow NN) on top of GSOM assignments plus raw features to emit activation signals such as auto-approvals, anomaly flags, or prioritisation hints. Version activation weights alongside neuron snapshots so we can audit decision boundaries.
- **Governance & Monitoring**: Run GSOM and activation services under BPMN control; record lineage between observation windows, neuron states, and activation decisions. Track health KPIs (neuron count, mean quantisation error, activation precision/recall) and gate self-adjusting behaviour behind drift detectors and approval workflows before production rollout.

---

This specification is the authoritative blueprint for the `learning` module. Update it alongside significant architectural, compliance, or infrastructure changes to keep domain implementations aligned with the shared platform.
