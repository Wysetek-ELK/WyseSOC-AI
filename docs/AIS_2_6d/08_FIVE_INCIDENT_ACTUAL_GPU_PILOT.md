# AIS 2.6d — Workstream 8: Five-Incident Actual GPU Live Pilot Report

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T16:20:00Z  
**Document Identity:** `docs/AIS_2_6d/08_FIVE_INCIDENT_ACTUAL_GPU_PILOT.md`  
**Execution State:** `BLOCKED_GPU_UNAVAILABLE` (Pending Checkpoint B)  
**Referenced Manifests:**  
- [PILOT_EXECUTION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/PILOT_EXECUTION_LEDGER.jsonl)
- [PILOT_GO_NO_GO.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/PILOT_GO_NO_GO.json)
- [GPU_RUNTIME_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/GPU_RUNTIME_MANIFEST.json)

---

## 1. Pilot Mission and Scope

The objective of the 5-Incident Live Pilot is to establish real-world GPU inference baseline metrics on Server 2 (`http://13.204.214.64:8000/v1`) prior to committing to the full 20-incident Three-Mode benchmark.

The pilot targets 5 high-priority representative incidents:
1. `132474210` (CrowdStrike - `PC-TSI-DC` - `net.exe` reconnaissance)
2. `132596403` (Prisma SASE - `172.25.6.101` - `review.es.system.js` travel script)
3. `132599145` (Prisma SASE - `172.25.14.157` - `21447_610850.xlsx` spreadsheet)
4. `132438483` (CrowdStrike - `DESKTOP-E0G2R49` - `whoami.exe` admin query)
5. `132591888` (Prisma SASE - `172.25.6.208` - `update.exe` remote PE binary)

---

## 2. Infrastructure Preflight & Blocker Statement

In accordance with Non-Negotiable Requirements 1, 2, and 18:
- **No Simulation Substitution:** Under no circumstances will offline deterministic simulation be substituted for live GPU inference.
- **No Autonomous Billing Mutation:** Antigravity and automated test harnesses must never automatically start, stop, resize, or replace billable cloud GPU infrastructure (AWS EC2 GPU Server 2).

During preflight connectivity verification on 2026-11-24:
- Target Endpoint: `http://13.204.214.64:8000/v1/models`
- Network Status: TCP connection timed out after 5000 ms.
- Host State: AWS EC2 instance is stopped / deallocated.

**Operational Decision:**  
The 5-incident live pilot execution is marked **BLOCKED_GPU_UNAVAILABLE**. Execution will commence immediately once the operator authorizes and starts Server 2 (Checkpoint B).

---

## 3. Pilot Execution Ledger Specification

The schema for `PILOT_EXECUTION_LEDGER.jsonl` requires strict capture of live inference telemetry:
- `request_id`: UUIDv4
- `incident_id`: Target incident
- `live_endpoint`: `http://13.204.214.64:8000/v1/chat/completions`
- `actual_model_id`: Server-returned model ID
- `prompt_tokens`: Actual prompt token count from vLLM usage object
- `completion_tokens`: Actual completion token count from vLLM usage object
- `latency_ms`: Measured round-trip latency in milliseconds
- `verdict`: Model-parsed verdict (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `INCONCLUSIVE`)
- `confidence`: Model-asserted confidence (0.0 to 1.0)
- `execution_provenance`: `LIVE_GPU_INFERENCE` (Simulation strictly barred)

Because the GPU endpoint is unreachable, zero synthetic or simulated rows have been inserted into `PILOT_EXECUTION_LEDGER.jsonl`.

---

## 4. Go / No-Go Gate Conditions for Full Benchmark

When Server 2 is activated, the pilot must meet the following criteria before the 20-incident benchmark is unlocked:
1. **Connectivity:** 5 of 5 HTTP 200 responses.
2. **Schema Compliance:** 5 of 5 responses return valid JSON adhering to Verdictum AI verdict schema.
3. **Context Length:** Zero token truncation errors; prompt tokens strictly within 7424 input budget.
4. **Latency:** Median latency under 15,000 ms per inference call.
5. **No Hallucinated Tool Calls:** Model strictly adheres to text-generation format.

Current Status: **NO_GO (Awaiting Server 2 Power-On)**.
