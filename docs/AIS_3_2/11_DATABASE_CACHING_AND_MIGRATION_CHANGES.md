# AIS 3.2 — 11: Database, Caching & Migration Changes

Added Alembic revision `018_ais32_rule_intelligence_and_context` (revising `017_ais31_holdout_benchmark`) creating three additive tables:
1. `ais32_rule_contracts` (versioned rule contracts, unique `(rule_id, contract_version)`, SHA-256 hashes, approval metadata).
2. `ais32_organizational_contexts` (tenant-scoped organizational context records with `(customer, context_type, dedup_hash)` uniqueness and validity window).
3. `ais32_execution_records` (full provenance per execution mode, prompt/contract hashes, raw vs validated vs effective verdicts, validator diagnostics, token/evidence audit JSON).
Tested upgrade (`016->017->018`), downgrade (`018->017`), and upgrade locally, and executed `alembic upgrade head` cleanly on Server 1 PostgreSQL.
