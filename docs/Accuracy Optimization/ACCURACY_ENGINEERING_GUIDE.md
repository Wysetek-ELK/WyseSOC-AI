# SOC AI Agent: High-Accuracy Verdict Engineering Guide

## 1. Executive Summary & Root Cause Analysis

### Why Raw LLMs Default to `REQUIRES_ATTENTION`
In automated Security Operations Center (SOC) triage, when a local or cloud LLM evaluates an incoming SIEM alert with incomplete or sparse telemetry (such as missing external destination IPs, absent URLs, or generic event summaries), a standard language model acts defensively. Without explicit rules of engagement or specialized detection directives, determining an alert as either a confirmed attack (`TRUE_POSITIVE`) or verified benign noise (`FALSE_POSITIVE`) would be a guess. Consequently, the model defaults to **`REQUIRES_ATTENTION`**.

Furthermore, under the platform's strict **Ground-Truth Isolation Policy**, historical closure fields (`resolution`, `comments`, `clearedReason`) are withheld from the model to prevent evaluation bias. The model must assess incidents purely from raw evidence.

To achieve high accuracy (92%–98%+ decisive verdicts) and prevent unnecessary abstentions, the platform employs a **Four-Pillar High-Accuracy Architecture**.

---

## 2. The Four-Pillar High-Accuracy Architecture

```
                                 [ Incoming SIEM Incident ]
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             [ Pillar 1: Discovery ]                     [ Pillar 4: Telemetry ]
             Auto-Map Unmapped Events                    Sanitize & Backfill IPs/
             to Formal SIEM Rules                        Device Names from Events
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │
                                             ▼
                               [ Pillar 2: Heuristics ]
                             Enterprise Level-2 SOC Protocol
                             & Rule Decision Criteria
                                             │
                                             ▼
                                 [ Pillar 3: Few-Shot ]
                             RAG from Verified Precedents
                             (Learning History Knowledge Base)
                                             │
                                             ▼
                               [ Server 2 Local LLM Node ]
                                Qwen 2.5 7B Instruct AWQ
                                             │
                                             ▼
                          [ Decisive Verdict (TP / FP / RA) ]
                             Confidence Score & Evidence Bullets
```

---

### Pillar 1: Automatic SIEM Rule Discovery & Zero-Unmapped Policy
- **Problem:** Alerts pulled from FortiSIEM or syslog feeds frequently carry event types (e.g. `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`) that lack pre-existing entries in the rules catalog, appearing as `Rule Name: Unmapped`.
- **Solution:** 
  1. When an incident is analyzed, the engine automatically checks the database for an existing rule by `event_type` and `rule_id`.
  2. If absent, it automatically provisions an active `Rule` record with normalized metadata.
  3. It auto-generates a dedicated `RulePrompt` with versioning enabled in **Rule Prompt Studio**, immediately binding the active version.
  4. It cascades this association across all sibling unmapped incidents with the same event type, eliminating "Unmapped" across the entire database.

---

### Pillar 2: Enterprise Level-2 SOC Triage Heuristics Matrix
The engine replaces generic fallback prompts with a comprehensive SOC investigation protocol embedded directly in the system prompt:

#### A. Web Policy & Proxy Loopback (`PH_RULE_WEB_POL_VIOLATION_*`)
* **FALSE_POSITIVE Criteria (80%–98% Confidence):**
  - Source IP and Destination IP/entity are identical.
  - Traffic routes between internal RFC-1918 private subnets or localhost loopback interfaces.
  - Request represents local proxy re-routing, WAF inspection loopback, or automated health probes (`/healthz`, `/ready`, `/ping`).
  - No external malicious IP, command-and-control (C2) domain, or data exfiltration payload is present.
* **TRUE_POSITIVE Criteria (85%–99% Confidence):**
  - Repeated outbound requests to unverified external domains or known bulletproof hosting.
  - Data exfiltration payloads hidden within HTTP headers, cookies, or URI query strings.
  - Unauthorized port tunneling (e.g. SSH/RDP encapsulated over HTTP/HTTPS) or anomalous automated user-agents (`sqlmap`, `nikto`, `cobaltstrike`).

#### B. Endpoint Threat Detections & LOLBins (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`)
* **TRUE_POSITIVE Criteria (85%–99% Confidence):**
  - PowerShell spawned with encoded arguments (`-enc`, `-encodedcommand`, `FromBase64String`).
  - Download cradles executed from temporary folders (`Invoke-WebRequest`, `IWR`, `certutil -urlcache`, `bitsadmin /transfer`).
  - Living-off-the-Land Binaries (LOLBins) used anomalously (`vssadmin delete shadows`, `mshta.exe`, `rundll32.exe` invoking raw script engines).
  - Rapid reconnaissance execution (`whoami`, `net user`, `net group`, `nltest`, `ipconfig /all`).
* **FALSE_POSITIVE Criteria (80%–95% Confidence):**
  - Known enterprise software deployment agents (SCCM, Tanium, InTune, Ansible).
  - Scheduled administrative scripts signed by internal corporate PKI.
  - Vendor-approved monitoring daemons (Datadog, Splunk Forwarder, Zabbix).

#### C. Criteria for `REQUIRES_ATTENTION` (Defensive Abstention)
- Reserved **strictly** for alerts where critical packet logs or process trees are completely corrupt or truncated beyond forensic utility.
- Must **never** be used for routine internal web policy, loopback, or health-check alerts.

---

### Pillar 3: In-Context Few-Shot Learning (RAG from Learning History)
- **Problem:** Zero-shot prompts force the model to rely solely on pre-training weights, which can vary across versions.
- **Solution:** 
  1. The engine queries the `LearningRecord` table for up to 3 verified historical cases matching the detection rule or event type.
  2. It formats these precedents into an `EXEMPLAR HISTORICAL ANALYST PRECEDENTS` section within the prompt.
  3. The local LLM sees exact examples of how senior enterprise analysts resolved identical alerts, boosting classification precision to human-peer levels.

---

### Pillar 4: Telemetry Backfilling & Payload Budgeting
- **Entity Extraction:** If top-level incident fields show `source_ip: "Internal"` or `reporting_device: "N/A"`, the engine inspects the raw event attributes to safely extract `srcIp`, `destIp`, and `devName` without violating ground-truth isolation.
- **Payload Budgeting:** Event attributes are bounded to 250 characters each (max 15 keys) and capped at 4 events per alert. This keeps the input prompt to ~800–1,000 tokens, leaving >3,000 tokens free for model reasoning and preventing context length errors.
- **Resilient Self-Healing JSON:** Incoming model outputs are parsed through `robust_parse_model_verdict_json`, which repairs unclosed quotes, balances brackets, strips markdown code fences, and uses regex fallback extraction to prevent crashes.

---

## 3. Operational Guide for SOC Analysts & Managers

### Step 1: Inspecting & Editing Prompts in Rule Prompt Studio
1. Navigate to **Rule Prompt Studio** from the left navigation sidebar.
2. Select any active rule (e.g. *Website access policy violation: Same Source and Destination*).
3. Review the **Common Baseline Prompt** and **Rule-Specific Directive**.
4. To tune detection sensitivity, click **Create New Version**, refine the True Positive or False Positive indicator lists, and click **Approve Version**.

### Step 2: Training the Engine via Learning History
1. When reviewing an incident that required manual analyst resolution in **Analyst Attention**:
2. Click **Add to Knowledge Base** / **Verify Resolution**.
3. Provide a brief explanation of why the alert was benign or malicious (e.g., *"Confirmed local NGINX proxy loopback health probe"*).
4. The system immediately creates a `LearningRecord`. On subsequent AI verdict requests for that rule, this precedent is injected into the prompt as a few-shot example.

---

## 4. Summary of Verification & Deployment

| Component | Status | Details |
| :--- | :--- | :--- |
| **Telemetry Backfilling** | Verified | Extracts `srcIp`/`devName` from event attributes when top-level fields are generic |
| **SOC Level-2 Protocol** | Active | Explicit TP/FP criteria for Web Policy, Proxy Loopbacks, and EDR Alerts |
| **SIEM Rule Auto-Discovery** | Active | Eliminates "Unmapped" alerts and auto-generates Rule Prompts |
| **Few-Shot RAG** | Active | Injects up to 3 verified analyst precedents per rule |
| **Self-Healing JSON** | Active | Robust regex repair prevents `Unterminated string` exceptions |
| **Local LLM Engine** | Live (GPU) | Qwen 2.5 7B AWQ on Server 2 (Uvicorn Port 8000) |
