# AIS 3.2 — 01: Existing Architecture & Code Audit

Audited backend services, schemas, SQLAlchemy models, routers, migrations (`017`), and frontend components across `SOC-AI-Agent`:
- **Duplicated Pipelines Found:** 3 distinct prompt/evidence paths (`verdict_pipeline.py`, `ais27_benchmark_runner.py`, `ais31_benchmark_service.py`) independently assembling prompts and sanitization.
- **Hardcoded Endpoint Bias Found:** `IndependentVerdictValidator` Check 5 enforced endpoint forensic/CrowdStrike/Prisma rules across 30 unrelated FortiSIEM firewall/scan/IPS/operational rules.
- **Archetype Gaps Found:** `DetectionArchetypeRegistry` lacked dedicated `FIREWALL_SECURITY`, `DNS_SECURITY`, `IPS_IDS`, `CONFIGURATION_MONITORING`, `OPERATIONAL_MONITORING`, and `THREAT_INTELLIGENCE` definitions.
- **Dependency Preservation Verified:** `test_agent_intelligence_studio_v2.py`, `test_empirical_benchmark_harness.py`, `test_independent_verdict_validator.py`, and CrowdStrike/Prisma validation contracts remain preserved.
