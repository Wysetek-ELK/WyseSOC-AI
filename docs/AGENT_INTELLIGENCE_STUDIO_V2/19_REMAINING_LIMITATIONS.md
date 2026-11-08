# 19. REMAINING LIMITATIONS AND FUTURE ROADMAP

## Honest Technical Boundaries

In alignment with the platform's core tenet of **Honest Observability and Factual Integrity**, this document articulates the current boundaries, trade-offs, and future enhancements of Agent Intelligence Studio 2.0:

---

## 1. Current System Boundaries

1. **No Infallible Verdict Accuracy:**
   - Quality scores (0–100) measure adherence to policy drafting standards and evidentiary completeness. They do **not** guarantee 100% verdict accuracy during live incident triage. Sensor blindspots, encrypted traffic payloads, and novel zero-day tradecraft remain external variables.
2. **SIEM Query Language Dialect Variance:**
   - While `RuleIntelligenceAnalyzer` natively parses FortiSIEM XML/JSON, Splunk SPL fragments, and Sigma YAML structures, esoteric proprietary SIEM query dialects may require fallback parsing to Tiers 3–5 (name and event-type semantics), resulting in an `INCOMPLETE` definition status until verified.
3. **Regex & AST Heuristic Boundaries in G2/G7:**
   - Contradiction and relevance checks rely on deterministic regex patterns, semantic token trees, and negation parsers. Extremely nuanced natural language phrasing in manually authored policies could theoretically evade contradiction detection if synonyms are omitted from the registry dictionary.
4. **Historical Simulation Cold-Start Waiver:**
   - For novel detection rules with fewer than 5 historical incidents ($N < 5$), Gate G8 waives the regression check with an `INSUFFICIENT_DATA` warning. While this prevents blocking new rules, it means new rules rely primarily on static quality gates (G1–G7) rather than empirical backtesting until incident volume accumulates.

---

## 2. Planned Roadmap (AIS 2.1+)

1. **Automated Sigma & Yara-L Ingestion Pipeline:**
   - Direct bi-directional synchronization with open-source Sigma rules and Google Chronicle Yara-L repositories.
2. **LLM-Assisted Red-Teaming for Gate G7:**
   - Incorporating an isolated, offline LLM adversarial critic to probe draft policies for edge-case logical paradoxes before SOC Lead review.
3. **Adaptive Threshold Baselining:**
   - Connecting `PolicyLifecycleMonitor` directly to telemetry streams to compute dynamic, statistical 95th-percentile host transfer baselines for threshold comparison.
4. **Automated Draft Synthesis from Verified Analyst Reversals:**
   - When an analyst overturns a verdict with documented rationale, automatically generate a proposed v2 policy draft incorporating the specific exception.
