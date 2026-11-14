export interface GuidePageDetail {
  id: string;
  slug: string;
  title: string;
  groupTitle: "SOC OPERATIONS" | "AGENT INTELLIGENCE" | "VALIDATION & TRUST" | "PLATFORM CONTROL";
  route: string;
  badge?: string;
  badgeColor?: string;
  implementationStatus: "FULLY_AVAILABLE" | "AVAILABLE_WITH_OFFLINE_MODE" | "PARTIALLY_IMPLEMENTED";
  statusDescription: string;
  whatIsThis: string;
  whyDoWeNeedIt: string;
  practicalUseCase: string;
  howToUse: string[];
  prerequisites: string[];
  expectedResult: string;
  relatedPages: Array<{ title: string; route: string }>;
}

export interface WorkflowStageDetail {
  stepNumber: number;
  title: string;
  shortDescription: string;
  detailedExplanation: string;
  targetUIPage: { title: string; route: string };
  offlineBehavior: string;
  exampleWalkthrough: string;
}

export const WORKFLOW_STAGES: WorkflowStageDetail[] = [
  {
    stepNumber: 1,
    title: "FortiSIEM Incident Ingestion",
    shortDescription: "Retrieval and intake of security incidents from FortiSIEM or offline files.",
    detailedExplanation:
      "Verdictum AI connects to the FortiSIEM REST API or accepts uploaded JSON/CSV archives to ingest security incidents. The system extracts raw security events, reporting device metadata, timestamps, and customer tenant associations.",
    targetUIPage: { title: "Telemetry Hub", route: "/telemetry-hub" },
    offlineBehavior:
      "When the FortiSIEM live instance is offline, the system seamlessly ingests offline JSON/CSV telemetry files or utilizes stored database records without disruption.",
    exampleWalkthrough:
      "Incident #176061 is pulled from FortiSIEM containing 45 raw events from firewall 'FortiGate-Core-01' indicating high outbound SSH traffic.",
  },
  {
    stepNumber: 2,
    title: "Telemetry Processing & Normalization",
    shortDescription: "Extraction of raw events into canonical evidence fields.",
    detailedExplanation:
      "Raw unstructured logs are parsed into standardized canonical fields (Source IP, Destination IP, Port, Protocol, Action, Process Name, User). Context compaction algorithms prune repetitive lines to fit within the AI context window.",
    targetUIPage: { title: "Telemetry Hub", route: "/telemetry-hub" },
    offlineBehavior:
      "Processing and normalization run completely on Verdictum Core (Server 1) CPU using deterministic regex and schema catalogs without external API requirements.",
    exampleWalkthrough:
      "Incident #176061 raw events are normalized into canonical fields: src_ip=192.0.2.45, dest_ip=203.0.113.88, dest_port=22, proto=TCP, action=PERMIT.",
  },
  {
    stepNumber: 3,
    title: "Detection Rule & Policy Evaluation",
    shortDescription: "Mapping incidents to specific detection rules and archetypes.",
    detailedExplanation:
      "The engine maps the incident's event type to its registered Detection Rule and archetype (e.g. Policy Violation, Brute Force, Scanning, Exfiltration). It loads the active 9-section prompt template from Agent Intelligence Studio.",
    targetUIPage: { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
    offlineBehavior:
      "Rule definitions, contracts, and prompt templates are stored locally in the PostgreSQL/SQLite database and operate 100% offline.",
    exampleWalkthrough:
      "Incident #176061 matches rule 'PH_RULE_CS_SUSPICIOUS_ACTIVITY' and archetype 'POLICY_VIOLATION'. Active Prompt Version 3 is loaded.",
  },
  {
    stepNumber: 4,
    title: "Local LLM Reasoning & Triage",
    shortDescription: "Private, on-premises AI inference evaluating TP vs. FP likelihood.",
    detailedExplanation:
      "The compiled prompt is dispatched to the locally hosted Qwen 2.5 7B model running on Verdictum Cortex (Server 2) (or local mock if offline). The LLM evaluates indicators, cross-references SOP rules, and returns a proposed verdict with a confidence score and factual claims.",
    targetUIPage: { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
    offlineBehavior:
      "If the Verdictum Cortex GPU LLM is offline or unreachable, the system automatically falls back to an advisory status: incidents remain open and are routed directly to the human analyst queue with an 'LLM Offline' tag.",
    exampleWalkthrough:
      "The Qwen model analyzes the SSH transfer and proposes 'FALSE_POSITIVE' (confidence 0.94), claiming the destination IP matches a scheduled nightly backup replication server.",
  },
  {
    stepNumber: 5,
    title: "Trust & Evidence Claim Validation",
    shortDescription: "Deterministic verification ensuring AI claims match source facts.",
    detailedExplanation:
      "Before an AI verdict is accepted, an independent non-LLM validation engine extracts all factual claims made by the model and cross-examines them against the raw evidence. If any hallucination or contradiction is found, the verdict is rejected.",
    targetUIPage: { title: "Verdict Intelligence", route: "/verdict-intelligence" },
    offlineBehavior:
      "Runs deterministically on Verdictum Core (Server 1); no external network or LLM connectivity required.",
    exampleWalkthrough:
      "The validator verifies that destination IP '203.0.113.88' exists in raw firewall events. Contradictions: 0. Trust Score calculated as 9/10 (Strong Support).",
  },
  {
    stepNumber: 6,
    title: "Human Analyst Review & Adjudication",
    shortDescription: "Double-blind analyst evaluation providing unbiased ground truth.",
    detailedExplanation:
      "The incident enters the Human Review Queue. In Double-Blind mode, the AI prediction is masked. The analyst independently evaluates the incident as True Positive, False Positive, or Inconclusive. Upon submission, the AI verdict is revealed and agreement is scored.",
    targetUIPage: { title: "Human Review Queue", route: "/human-review-queue" },
    offlineBehavior:
      "Fully operational offline. Analysts can review incidents, record notes, and attach evidence without external dependencies.",
    exampleWalkthrough:
      "Analyst Alice independently classifies Incident #176061 as 'FALSE_POSITIVE' referencing change order CHG-9921. System records 'AGREEMENT_FP'.",
  },
  {
    stepNumber: 7,
    title: "Rule Learning & Governance Recalculation",
    shortDescription: "Updating statistical accuracy, Wilson bounds, and production readiness.",
    detailedExplanation:
      "The verified analyst feedback updates the rule's learning profile. The system recalculates empirical accuracy, False Positive precision, and Wilson Score 95% confidence lower bounds. If a critical missed threat occurs, the rule is instantly suspended.",
    targetUIPage: { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
    offlineBehavior:
      "Mathematical evaluation executes locally. Continuous learning profiles are updated in the local database.",
    exampleWalkthrough:
      "Verified FP count increments to 26; Wilson lower bound recalculates to 96.4%. Rule status evaluated against the 12-barrier production eligibility checklist.",
  },
];

export const ALL_GUIDE_PAGES: GuidePageDetail[] = [
  // -------------------------------------------------------------
  // SOC OPERATIONS
  // -------------------------------------------------------------
  {
    id: "mission-control",
    slug: "agent-mission-control",
    title: "Agent Mission Control",
    groupTitle: "SOC OPERATIONS",
    route: "/agent-mission-control",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational executive dashboard with live telemetry and cluster health monitoring.",
    whatIsThis:
      "Agent Mission Control is the primary operational dashboard for Verdictum AI. It provides real-time visibility into overall security posture, automated triage throughput, and live cluster health across Verdictum Core and Verdictum Cortex.",
    whyDoWeNeedIt:
      "SOC managers and lead analysts need a single pane of glass to monitor incident inflow, automation status, and system capacity without digging through multiple queues.",
    practicalUseCase:
      "During a shift handover, the SOC Lead reviews the 24-hour True Positive vs. False Positive ratio and checks Verdictum Cortex cluster health before assigning escalations to Tier 1 analysts.",
    howToUse: [
      "Open Agent Mission Control from the top of the sidebar.",
      "Review the top KPI cards for Ingested Incidents, AI Triage Coverage, and TP/FP breakdown.",
      "Inspect the Server Infrastructure Monitor for Verdictum Core and Verdictum Cortex health status.",
      "Check the Recent Triage Activity stream for high-severity alerts.",
      "If new incidents are pending reconciliation, click 'Reconcile Pending' to trigger background processing.",
    ],
    prerequisites: [
      "Active user account (Administrator, SOC Analyst, or Read-Only Viewer).",
      "Telemetry data ingested via Telemetry Hub or FortiSIEM sync.",
      "Operational with or without active LLM (displays offline status gracefully).",
    ],
    expectedResult:
      "Instant situational awareness of SOC throughput, AI triage performance, and cluster availability.",
    relatedPages: [
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
      { title: "Telemetry Hub", route: "/telemetry-hub" },
      { title: "Human Review Queue", route: "/human-review-queue" },
      { title: "Inference Control", route: "/inference-control" },
    ],
  },
  {
    id: "ai-triage",
    slug: "ai-triage-workbench",
    title: "AI Triage Workbench",
    groupTitle: "SOC OPERATIONS",
    route: "/ai-triage-workbench",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational incident analysis table with AI verdict inspection and evidence grounding.",
    whatIsThis:
      "The AI Triage Workbench is the central investigation workspace where analysts inspect security alerts, review AI-generated verdicts, and examine underlying raw evidence.",
    whyDoWeNeedIt:
      "Automates the repetitive and time-consuming task of initial evidence gathering, allowing analysts to quickly validate whether an alert is a benign false alarm or an active attack.",
    practicalUseCase:
      "An analyst investigates Incident #176061 (SSH Tunneling alert), reviews the AI's proposed False Positive verdict, verifies the destination IP in the raw evidence table, and confirms authorized backup activity.",
    howToUse: [
      "Navigate to AI Triage Workbench from the sidebar.",
      "Filter incidents by Detection Rule, Severity, or search by IP/hostname.",
      "Toggle 'Blind Review Mode' if conducting unbiased independent evaluation.",
      "Click on an incident row to view its details or click 'Run AI Analysis' for un-triaged events.",
      "Inspect the AI Verdict modal: Confidence score, reasoning summary, and grounded evidence table.",
    ],
    prerequisites: [
      "SOC Analyst or Administrator role.",
      "Ingested incidents in the database.",
      "Local LLM connectivity for live triage, or mock fallback mode when offline.",
    ],
    expectedResult:
      "Rapid determination of incident veracity supported by grounded, hallucination-free evidence.",
    relatedPages: [
      { title: "Agent Mission Control", route: "/agent-mission-control" },
      { title: "Human Review Queue", route: "/human-review-queue" },
      { title: "Telemetry Hub", route: "/telemetry-hub" },
      { title: "Detection Intelligence", route: "/detection-intelligence" },
    ],
  },
  {
    id: "telemetry-hub",
    slug: "telemetry-hub",
    title: "Telemetry Hub",
    groupTitle: "SOC OPERATIONS",
    route: "/telemetry-hub",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational ingestion hub supporting FortiSIEM live API and offline file uploads.",
    whatIsThis:
      "Telemetry Hub is the data ingestion and synchronization center responsible for connecting to FortiSIEM, importing offline telemetry archives, and orchestrating continuous background polling.",
    whyDoWeNeedIt:
      "Ensures that the AI analysis engine always has fresh security events from firewalls, endpoints, and servers without manual file transfers.",
    practicalUseCase:
      "A SOC engineer configures the 5-minute automated FortiSIEM sync poller and manually pulls Incident #176061 to test immediate triage throughput.",
    howToUse: [
      "Navigate to Telemetry Hub from the sidebar.",
      "To pull a single incident: Enter the FortiSIEM Incident ID and click 'Pull & Ingest Incident'.",
      "To run a batch sync: Set batch size and click 'Pull Latest Incidents Batch'.",
      "To toggle continuous polling: Click 'Start Background Poller' (monitors next sync countdown).",
      "For offline testing: Drag and drop a JSON/CSV telemetry file into the upload dropzone.",
    ],
    prerequisites: [
      "Administrator or SOC Analyst permissions.",
      "Configured FortiSIEM API credentials in Agent Configuration (or local mock fallback mode enabled).",
    ],
    expectedResult:
      "Telemetry records ingested, normalized into canonical fields, and added to the triage queue.",
    relatedPages: [
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
      { title: "Agent Mission Control", route: "/agent-mission-control" },
      { title: "Agent Configuration", route: "/agent-configuration" },
    ],
  },
  {
    id: "human-review-queue",
    slug: "human-review-queue",
    title: "Human Review Queue",
    groupTitle: "SOC OPERATIONS",
    route: "/human-review-queue",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational human investigation workbench with collaborative Q&A and dispute handling.",
    whatIsThis:
      "The Human Review Queue is a collaborative human-in-the-loop escalation workbench where complex, disputed, or high-risk security incidents are thoroughly investigated, assigned, and resolved by SOC analysts.",
    whyDoWeNeedIt:
      "Prevents unchecked automated actions, provides a structured workspace for analyst questions and notes, and records verified ground truth for AI model learning.",
    practicalUseCase:
      "An L1 analyst encounters an ambiguous PowerShell execution alert, marks it as 'Awaiting Evidence', asks a question to the system owner, and records an approved change order as evidence.",
    howToUse: [
      "Open Human Review Queue from the sidebar.",
      "Filter by investigation status (ASSIGNED, IN_PROGRESS, PENDING_REVIEW, DISPUTED).",
      "Click an incident to open the Investigation Drawer.",
      "Add investigation notes, post questions, or attach additional telemetry files.",
      "Select the final determination (ACCEPTED, OVERRIDDEN, DISPUTED) and toggle 'Mark as Independently Verified'.",
      "Click 'Submit Final Determination'.",
    ],
    prerequisites: [
      "SOC Analyst or Administrator role.",
      "Assigned or unreviewed incidents in the database.",
    ],
    expectedResult:
      "Investigation updated, ticket resolution recorded, and verified ground-truth precedent stored in Agent Memory.",
    relatedPages: [
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
      { title: "Agent Memory", route: "/agent-memory" },
      { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
    ],
  },
  {
    id: "soc-chatbot",
    slug: "soc-chatbot",
    title: "Verdictum Sentinel",
    groupTitle: "SOC OPERATIONS",
    route: "/soc-chatbot",
    badge: "COPILOT",
    badgeColor: "bg-indigo-950 text-indigo-300 border border-indigo-800",
    implementationStatus: "AVAILABLE_WITH_OFFLINE_MODE",
    statusDescription: "Operational when Verdictum Cortex Qwen LLM is online; graceful advisory fallback when offline.",
    whatIsThis:
      "Verdictum Sentinel is an AI SOC Investigation Copilot that allows analysts to query security concepts, deobfuscate malicious scripts, map incidents to MITRE ATT&CK techniques, and draft containment playbooks using natural language powered by Verdictum Cortex.",
    whyDoWeNeedIt:
      "Accelerates tactical investigation by providing on-demand guidance, threat intelligence summaries, and script analysis directly within the analyst's workflow.",
    practicalUseCase:
      "An analyst pastes an obfuscated Base64 PowerShell one-liner from an alert, and Sentinel deobfuscates the script, extracts the malicious C2 domain, and recommends containment steps.",
    howToUse: [
      "Navigate to Verdictum Sentinel from the sidebar.",
      "(Optional) Select an active incident from the dropdown to attach its telemetry context.",
      "Click a Quick Prompt (e.g., 'MITRE ATT&CK Mapping' or 'Deobfuscate PowerShell') or type a custom query.",
      "Click 'Send' and inspect the streamed response with latency and token analytics.",
      "If Verdictum Cortex LLM is offline, review the offline fallback banner.",
    ],
    prerequisites: [
      "Active Verdictum Cortex Qwen LLM cluster for live inference (graceful advisory message when offline).",
      "User authenticated with SOC Analyst or Administrator role.",
    ],
    expectedResult:
      "Instant expert analysis, decoded payloads, and structured containment checklists.",
    relatedPages: [
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
      { title: "Inference Control", route: "/inference-control" },
      { title: "Agent Mission Control", route: "/agent-mission-control" },
    ],
  },

  // -------------------------------------------------------------
  // AGENT INTELLIGENCE
  // -------------------------------------------------------------
  {
    id: "intelligence-studio",
    slug: "agent-intelligence-studio",
    title: "Agent Intelligence Studio",
    groupTitle: "AGENT INTELLIGENCE",
    route: "/agent-intelligence-studio",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational 7-tab IDE for prompt engineering, quality gating, simulation, and governance.",
    whatIsThis:
      "Agent Intelligence Studio is a comprehensive engineering IDE for detection rules and AI prompts. It features 7 integrated tabs: Prompt Editor, Detection Intelligence, Evidence Contracts, Quality Gates, Simulation Lab, Drift & Monitoring, and Rule Learning & Governance.",
    whyDoWeNeedIt:
      "Bridges the gap between detection engineering and AI governance, ensuring that every AI prompt is grounded, schema-validated, statistically evaluated, and qualified before production automation.",
    practicalUseCase:
      "A detection engineer selects 'PH_RULE_CS_SUSPICIOUS_ACTIVITY', drafts version 3 of its prompt template, runs structural quality gates (G1–G8), benchmarks historical accuracy in the Simulation Lab, and monitors Wilson score confidence intervals.",
    howToUse: [
      "Open Agent Intelligence Studio and select a rule from the catalog.",
      "Tab 1 (Editor): Draft 9-section prompt templates with standard variables.",
      "Tab 2 & 3 (Intelligence & Contract): Review required fields and canonical schema mappings.",
      "Tab 4 (Quality Gates): Execute automated syntax, schema, and completeness tests.",
      "Tab 5 (Simulation): Replay historical incidents to measure empirical accuracy.",
      "Tab 6 (Drift): Monitor telemetry and verdict drift.",
      "Tab 7 (Rule Learning & Governance): Inspect Wilson score lower bounds, review confusion matrices, and manage production promotion.",
    ],
    prerequisites: [
      "Administrator or Senior Detection Engineer role.",
      "Configured detection rules in Detection Intelligence.",
    ],
    expectedResult:
      "Validated, production-ready AI prompt versions bound to specific detection rules.",
    relatedPages: [
      { title: "Detection Intelligence", route: "/detection-intelligence" },
      { title: "Agent Simulation Lab", route: "/agent-simulation-lab" },
      { title: "Verdict Intelligence", route: "/verdict-intelligence" },
      { title: "Agent Memory", route: "/agent-memory" },
    ],
  },
  {
    id: "detection-intelligence",
    slug: "detection-intelligence",
    title: "Detection Intelligence",
    groupTitle: "AGENT INTELLIGENCE",
    route: "/detection-intelligence",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational detection rule registry with FortiSIEM synchronization.",
    whatIsThis:
      "Detection Intelligence is the central catalog and registry for all security detection rules synchronized from FortiSIEM and custom correlation rules.",
    whyDoWeNeedIt:
      "Provides visibility into which rules are active, their severity, event types, telemetry signatures, and whether they have associated AI prompt versions.",
    practicalUseCase:
      "A SOC manager reviews the catalog to verify that all high-priority brute-force and ransomware detection rules have active AI prompt versions assigned.",
    howToUse: [
      "Open Detection Intelligence from the sidebar.",
      "Review aggregate statistics (Total Rules, Active, Rules with Prompts).",
      "Filter rules by Severity, Active Status, or search by name.",
      "Click 'Sync from FortiSIEM' to refresh rule definitions from the SIEM.",
      "Click any rule to view its conditions, field mappings, and linked prompt templates.",
    ],
    prerequisites: [
      "Read access for analysts; Administrator role to trigger SIEM rule sync.",
    ],
    expectedResult:
      "Complete synchronization of detection rules and clarity on AI coverage.",
    relatedPages: [
      { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
      { title: "Telemetry Hub", route: "/telemetry-hub" },
    ],
  },
  {
    id: "agent-memory",
    slug: "agent-memory",
    title: "Agent Memory",
    groupTitle: "AGENT INTELLIGENCE",
    route: "/agent-memory",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational precedent repository and semantic similar case search engine.",
    whatIsThis:
      "Agent Memory is an institutional knowledge base that stores verified human analyst determinations, resolution precedents, and rationale to guide future AI reasoning.",
    whyDoWeNeedIt:
      "Prevents repetitive investigations of known false positives and ensures the AI learns from past senior analyst decisions.",
    practicalUseCase:
      "An analyst investigating a new scheduled task uses the 'Find Similar Cases' tool to discover three identical incidents resolved as False Positives last month by another analyst with approved change orders.",
    howToUse: [
      "Open Agent Memory from the sidebar.",
      "Filter precedents by rule, verdict (TRUE_POSITIVE, FALSE_POSITIVE), or keyword.",
      "Use the 'Similar Cases Search' tool: Enter an IP, command line, or incident ID to find historical matches.",
      "Click on any record to inspect the original incident context and analyst explanation.",
      "Administrators can click 'Seed Initial Memory' to ingest baseline historical precedents.",
    ],
    prerequisites: [
      "Human analyst reviews completed in Human Review Queue or AI Triage Workbench.",
    ],
    expectedResult:
      "Instant discovery of past investigation precedents and continuous knowledge retention.",
    relatedPages: [
      { title: "Human Review Queue", route: "/human-review-queue" },
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
      { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
    ],
  },

  // -------------------------------------------------------------
  // VALIDATION & TRUST
  // -------------------------------------------------------------
  {
    id: "simulation-lab",
    slug: "agent-simulation-lab",
    title: "Agent Simulation Lab",
    groupTitle: "VALIDATION & TRUST",
    route: "/agent-simulation-lab",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational replay sandbox supporting offline heuristic and live LLM benchmarking.",
    whatIsThis:
      "The Agent Simulation Lab is an offline testing and historical replay laboratory that evaluates detection rules and AI prompts against captured datasets before production deployment.",
    whyDoWeNeedIt:
      "Allows engineers to measure accuracy, detect regressions, and identify missed threats without risking live security operations or incident closures.",
    practicalUseCase:
      "Before rolling out a prompt change for firewall port scans, an engineer creates a simulation job replaying 50 historical incidents to verify 100% agreement and zero critical false negatives.",
    howToUse: [
      "Navigate to Agent Simulation Lab from the sidebar.",
      "Review existing simulation replay jobs and their completion status.",
      "Click 'New Simulation Job': Select detection rule, provider type (SIMULATED heuristic or OPENAI_COMPATIBLE LLM), and sample limit.",
      "Click 'Launch Simulation Run'.",
      "Click on completed jobs to inspect per-incident agreement, trust scores, and latency.",
    ],
    prerequisites: [
      "SOC Analyst or Administrator role.",
      "Historical incident records in the database.",
    ],
    expectedResult:
      "Empirical validation report showing agreement rate, confusion breakdown, and regression safety.",
    relatedPages: [
      { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
      { title: "Verdict Intelligence", route: "/verdict-intelligence" },
      { title: "Detection Intelligence", route: "/detection-intelligence" },
    ],
  },
  {
    id: "verdict-intelligence",
    slug: "verdict-intelligence",
    title: "Verdict Intelligence",
    groupTitle: "VALIDATION & TRUST",
    route: "/verdict-intelligence",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational statistical trust dashboard with pilot supervision and Wilson CI gating.",
    whatIsThis:
      "Verdict Intelligence is a quantitative trustworthiness, statistical calibration, and autonomous pilot governance dashboard.",
    whyDoWeNeedIt:
      "Ensures that automated AI verdicts are backed by rigorous mathematical standards (Wilson Score 95% confidence intervals, sample size gating) and supervises controlled pilot deployments.",
    practicalUseCase:
      "A SOC Director examines the Trust Score distribution across 500 incidents and verifies that Rule 'PH_RULE_HEAVY_TCP_HOST_SCAN' has achieved a 97.2% Wilson lower bound before approving pilot automation.",
    howToUse: [
      "Open Verdict Intelligence from the sidebar.",
      "Tab 1 (Overview): Review average Trust Scores (1–10 scale) and automation readiness.",
      "Tab 2 (Accuracy & Calibration): Inspect empirical validation vs simulation runs.",
      "Tab 3 (Rule-wise Trustworthiness): Check per-rule calibration status and Wilson confidence bounds.",
      "Tab 4 (Explainability): Enter an incident ID to calculate its 5-factor Trust Assessment score.",
      "Tab 5 (Controlled Pilot): Configure shadow-mode pilots, supervisor verify thresholds, and emergency rollbacks.",
    ],
    prerequisites: [
      "Administrator or Senior Analyst role for pilot modifications; read access for viewers.",
    ],
    expectedResult:
      "Mathematical transparency into AI reliability and safe governance of automation pilots.",
    relatedPages: [
      { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
      { title: "Agent Simulation Lab", route: "/agent-simulation-lab" },
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
    ],
  },

  // -------------------------------------------------------------
  // PLATFORM CONTROL
  // -------------------------------------------------------------
  {
    id: "inference-control",
    slug: "inference-control",
    title: "Inference Control",
    groupTitle: "PLATFORM CONTROL",
    route: "/inference-control",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational hardware health monitor and token consumption tracker.",
    whatIsThis:
      "Inference Control is a real-time hardware health, resource utilization, and token economics monitoring console for the AI inference cluster.",
    whyDoWeNeedIt:
      "Provides operational visibility into GPU VRAM, KV cache usage, CPU/memory loads, token budgets, and historical latency to ensure high availability and prevent performance bottlenecks.",
    practicalUseCase:
      "A platform administrator checks the Verdictum Cortex GPU status after a high-volume incident burst, observing that VRAM is at 62%, KV cache is healthy, and average response latency is 1,240 ms.",
    howToUse: [
      "Navigate to Inference Control from the sidebar.",
      "Inspect Verdictum Core (Backend API) CPU, RAM, and Disk metrics.",
      "Inspect Verdictum Cortex (vLLM / Qwen GPU) status, model name, and KV cache utilization.",
      "Review the Token Bifurcation widget: Breakdown of tokens across Incident Triage, Batch Triage, Simulation Replay, and Policy Testing.",
      "Check cluster status alerts if Verdictum Cortex is offline or unreachable.",
    ],
    prerequisites: [
      "System monitoring service active; Verdictum Core & Verdictum Cortex telemetry accessible.",
    ],
    expectedResult:
      "Full situational awareness of AI cluster health, token costs, and processing latency.",
    relatedPages: [
      { title: "Agent Mission Control", route: "/agent-mission-control" },
      { title: "Agent Configuration", route: "/agent-configuration" },
      { title: "Verdictum Sentinel", route: "/soc-chatbot" },
    ],
  },
  {
    id: "agent-configuration",
    slug: "agent-configuration",
    title: "Agent Configuration",
    groupTitle: "PLATFORM CONTROL",
    route: "/agent-configuration",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational settings panel for FortiSIEM, Verdictum Cortex LLM, and double-blind mode.",
    whatIsThis:
      "Agent Configuration is the master integration settings and environmental preferences panel for FortiSIEM and the Verdictum Cortex LLM server.",
    whyDoWeNeedIt:
      "Centralizes API endpoints, authentication credentials, network timeouts, context window budgets, and operational flags in one secure interface.",
    practicalUseCase:
      "An administrator updates the FortiSIEM hostname, tests the connection successfully with green feedback, adjusts the LLM context window budget to 16,384 tokens, and enables Double-Blind Review Mode.",
    howToUse: [
      "Open Agent Configuration from the sidebar.",
      "FortiSIEM Section: Enter Host URL, Username, Password, and timeout; click 'Test Connection'; click 'Save Configuration'.",
      "Local LLM Section: Configure Verdictum Cortex Host, Port, Model Name ('Qwen/Qwen2.5-7B-Instruct-AWQ'), and context budget; click 'Test LLM Connection'.",
      "Preferences Section: Toggle 'Blind Review Mode' (hides AI verdicts across analysts) and switch themes.",
    ],
    prerequisites: [
      "Administrator role required to save or test credentials.",
    ],
    expectedResult:
      "Securely persisted system settings and verified connectivity to external security infrastructure.",
    relatedPages: [
      { title: "Inference Control", route: "/inference-control" },
      { title: "Telemetry Hub", route: "/telemetry-hub" },
      { title: "Governance & Access", route: "/governance-access" },
    ],
  },
  {
    id: "governance-access",
    slug: "governance-access",
    title: "Governance & Access",
    groupTitle: "PLATFORM CONTROL",
    route: "/governance-access",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational RBAC user management and immutable audit log viewer.",
    whatIsThis:
      "Governance & Access is the user management, role-based access control (RBAC), and immutable security audit log center.",
    whyDoWeNeedIt:
      "Enforces the principle of least privilege, ensures multi-tenant isolation, and provides tamper-proof historical accountability for all administrative and triage actions.",
    practicalUseCase:
      "A Security Director creates a new user account for a junior analyst with the 'SOC Analyst' role and reviews audit logs to verify who engaged the emergency automation kill-switch last night.",
    howToUse: [
      "Navigate to Governance & Access from the sidebar.",
      "Tab 1 (User Management): Fill out the 'Create New User' form (Username, Email, Full Name, Password, Role) and click 'Create User'.",
      "View the table of active users and toggle user status as needed.",
      "Tab 2 (Audit Trail): Inspect timestamped records of user logins, rule transitions, prompt approvals, and system configurations.",
    ],
    prerequisites: [
      "Administrator role for user creation and modification; read-only access for analysts.",
    ],
    expectedResult:
      "Strict access control compliance and verifiable audit history.",
    relatedPages: [
      { title: "Agent Configuration", route: "/agent-configuration" },
      { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
    ],
  },
  {
    id: "admin-guide",
    slug: "admin-guide",
    title: "Verdictum AI Admin Guide",
    groupTitle: "PLATFORM CONTROL",
    route: "/admin-guide",
    implementationStatus: "FULLY_AVAILABLE",
    statusDescription: "Fully operational interactive documentation manual covering all 14 pages and end-to-end workflows.",
    whatIsThis:
      "The Verdictum AI Admin Guide is an interactive user documentation and operational reference manual integrated directly into the application interface.",
    whyDoWeNeedIt:
      "Empowers analysts, engineers, and administrators to understand system workflows, prerequisites, and use cases without leaving the platform or consulting external documents.",
    practicalUseCase:
      "A newly hired L1 analyst uses the Admin Guide to understand how the 8-stage verification pipeline works, reviews the step-by-step instructions for the Double-Blind Review Workbench, and clicks a direct link to the Human Review Queue.",
    howToUse: [
      "Open Verdictum AI Admin Guide from the bottom of the sidebar.",
      "Use the left-side Table of Contents to navigate through the 4 core groups (SOC Operations, Agent Intelligence, Validation & Trust, Platform Control) or the 'How Verdictum AI Works' end-to-end workflow guide.",
      "Use the search bar to locate specific terms, pages, or use cases.",
      "Click direct links to jump immediately to the corresponding application page.",
      "Use 'Previous' and 'Next' buttons at the bottom of each page for guided reading.",
    ],
    prerequisites: [
      "Accessible to all authenticated users (SOC Analysts, Administrators, Read-Only Viewers).",
    ],
    expectedResult:
      "Instant comprehension of application capabilities, operational procedures, and safety rules.",
    relatedPages: [
      { title: "Agent Mission Control", route: "/agent-mission-control" },
      { title: "AI Triage Workbench", route: "/ai-triage-workbench" },
      { title: "Agent Intelligence Studio", route: "/agent-intelligence-studio" },
    ],
  },
];
