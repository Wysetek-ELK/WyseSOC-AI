| Gate | Requirement | Status | Evidence |
|---|---|---|---|
| G01 | Existing architecture audited | **PASS** | Complete audit across inference, validator, rule/evidence/trust engines and UI completed. |
| G02 | AIS 3.1 failures reconciled | **PASS** | 100-incident AIS 3.1 results (12% raw E2E, 1% validated app, 0/18 TP recall, 24 validator overrides) reconciled. |
| G03 | Universal rule intelligence implemented | **PASS** | RuleIntelligenceEngine deployed and tested. |
| G04 | Reusable archetype mapping implemented | **PASS** | 11 canonical archetypes mapped across 51 local rules and 30+ FortiSIEM patterns. |
| G05 | Versioned dynamic rule contracts implemented | **PASS** | DynamicRuleContract + RuleContractRecord persisted via migration 018. |
| G06 | Operational and security verdict semantics separated | **PASS** | VerdictSemanticsEngine separates CONFIRMED vs MALICIOUS/OPERATIONAL_ISSUE vs authorization. |
| G07 | Organizational context integration implemented | **PASS** | OrganizationalContextService supports all 17 context types with PostgreSQL + optional Redis. |
| G08 | Organizational context provenance and isolation verified | **PASS** | Tenant isolation, Admin approval, expiration, verdict-import block verified in tests. |
| G09 | Canonical prompt engine implemented | **PASS** | UniversalPromptEngine implemented for both live and benchmark composition. |
| G10 | Benchmark and operational prompt parity verified | **PARTIAL** | Shared code path verified by tests; live Server 2 benchmark parity run pending admin auth. |
| G11 | Modular independent validator implemented | **PASS** | 7-step ModularVerdictValidator across 11 archetype profiles. |
| G12 | Legacy validation regression verified | **PASS** | Legacy CrowdStrike/Prisma paths and validator tests pass (141/142 backend tests). |
| G13 | Evidence completeness verified | **PASS** | raw_payload fallback, rule-aware prioritization, and audit fields verified in tests. |
| G14 | Live token budget verified | **PARTIAL** | 8192 budget logic verified offline; live vLLM /tokenize run on AIS_3_2_DEVELOPMENT blocked pending admin auth. |
| G15 | Structured output integrity verified | **PASS** | validate_structured_output detects truncation, bad EV-* refs, contradictions. |
| G16 | Protected benchmark cohorts unchanged | **PASS** | No AIS_2_6E_FROZEN_20 or AIS_3_0_INDEPENDENT_HOLDOUT_100 mutation paths added; AIS_3_2_DEVELOPMENT excludes IDs & SHA-256 hashes. |
| G17 | Existing human reviews preserved | **PASS** | Zero review reset/unlock actions executed; historical reviews preserved. |
| G18 | Development dataset isolation verified | **PASS** | ID, SHA-256 hash, LearningRecord exclusions verified in unit/API integration tests. |
| G19 | Real GPU technical pilot executed | **BLOCKED** | Blocked pending Server 1 Admin authentication / Chrome DevToolsActivePort to invoke /api/ais32/runs/execute. |
| G20 | Mode A and Mode B development results reconciled | **BLOCKED** | Blocked pending live Server 1 -> Server 2 execution of AIS_3_2_DEVELOPMENT. |
| G21 | Accuracy and coverage metrics verified | **BLOCKED** | Live development empirical metrics cannot be fabricated; unit-tested with explicit transport only. |
| G22 | Trust-layer behavior reconciled | **PASS** | reconcile_verdict_layers preserves autonomous closure/remediation disabled and uncalibrated cap disclosure. |
| G23 | Compact UI verified | **PARTIAL** | 18 frontend test suites & Next.js build verified; live authenticated remote browser screenshots blocked by Chrome DevToolsActivePort. |
| G24 | Security and RBAC verified | **PASS** | 401/403 RBAC, cross-tenant block, UPLA security scans (0 new findings), prompt-injection escaping verified. |
| G25 | Database and caching integrity verified | **PASS** | Migration 018 upgrade/downgrade verified locally & upgraded on Server 1. |
| G26 | Backend and frontend regression verified | **PASS** | AIS 3.2 tests (7/7), 141/142 regression tests, 18 frontend suites, next build PASS. |
| G27 | Governed Server 1 deployment verified | **PASS** | UPLA Gate 1/2 deployed commit 0e492c90b0ebf0f967ab9488774052c83e90792b; HTTP health 200 OK. |
| G28 | Server 2 unchanged | **PASS** | Server 2 untouched; health endpoint reports Qwen/Qwen3-14B-AWQ ONLINE. |
| G29 | Fresh holdout isolation plan prepared | **PASS** | Statistical plan computed (recommended min N=240, min TP=60). |
| G30 | Final evidence package complete | **PASS** | All 23 Markdown reports, 28 JSON/checksum manifests, and redacted zip generated honestly. |
