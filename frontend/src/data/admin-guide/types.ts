export type GuideMode =
  | "guided-tour"
  | "architecture"
  | "policy-lifecycle"
  | "decision-engine"
  | "incident-walkthrough"
  | "requirements"
  | "troubleshooting";

export type FlowLane = "governance" | "runtime" | "bridge" | "decision" | "outcome";

export type NodeAccent = "cyan" | "sky" | "indigo" | "emerald" | "amber" | "rose" | "slate";

export interface WorkflowStepSpec {
  id: string;
  stepNumber: number;
  title: string;
  shortLabel: string;
  lane: FlowLane;
  laneLabel: string;
  accent: NodeAccent;
  componentName: string;
  serviceModule: string;
  uiRoute?: string;
  uiLabel?: string;
  summary: string;
  inputData: string[];
  processingLogic: string[];
  outputData: string[];
  requiredConfig: string[];
  failureOrAbstention: string[];
  position: { x: number; y: number };
  outcomeBadge?: "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ANALYST_ATTENTION";
}

export interface WorkflowEdgeSpec {
  id: string;
  source: string;
  target: string;
  label?: string;
  isBridge?: boolean;
  bridgeNote?: string;
  accent?: NodeAccent;
  activeOnStepIds?: string[];
  sourceHandle?: string;
  targetHandle?: string;
}

export interface SwimlaneBoxSpec {
  id: string;
  title: string;
  subtitle: string;
  accent: "cyan" | "emerald";
  position: { x: number; y: number };
  width: number;
  height: number;
}

export interface QualityGateDoc {
  gateId: string;
  gateCode: string;
  gateName: string;
  category: "STRUCTURAL" | "EMPIRICAL";
  breakdownBucket: string;
  maxScore: number;
  weightNote: string;
  description: string;
  passConditions: string[];
  warningConditions: string[];
  blockerConditions: string[];
  remediationGuidance: string[];
}

export interface PolicySectionDoc {
  sectionNumber: number;
  sectionId: string;
  title: string;
  owner: string;
  description: string;
  purposeInTriage: string;
  gateDependencies: string[];
  exampleSnippet: string;
}

export interface StudioLifecycleStage {
  step: number;
  id: string;
  title: string;
  service: string;
  uiTab: string;
  summary: string;
  keyGuarantee: string;
  details: string[];
}

export interface IncidentWalkthroughStep {
  stepNumber: number;
  id: string;
  stageName: string;
  componentName: string;
  statusBadge: string;
  statusTone: "cyan" | "amber" | "rose" | "emerald" | "slate";
  whatHappens: string;
  observedFacts: string[];
  illustrativePlaceholders: string[];
  guardrailOrScoreImpact: string;
  takeaway: string;
}

export type RequirementCriticality = "REQUIRED" | "CONDITIONAL" | "OPTIONAL";

export interface RequirementCheckItem {
  id: string;
  title: string;
  criticality: RequirementCriticality;
  description: string;
  whereToConfigure: string;
  route?: string;
  routeLabel?: string;
  consequenceIfMissing: string;
  verificationCheck: string;
  liveStatusKey?: "fortisiem" | "llm" | "policies" | "verdict_metrics";
}

export interface RequirementDomain {
  id: string;
  domainNumber: number;
  title: string;
  stageTag: string;
  summary: string;
  items: RequirementCheckItem[];
}

export interface GlossaryEntry {
  id: string;
  term: string;
  aliases?: string[];
  category: "Architecture" | "AIS 2.0 & Gates" | "Decision & Trust" | "Empirical & Stats" | "Operations";
  definition: string;
  codeReference: string;
  relatedTerms?: string[];
}

export interface TroubleshootingScenario {
  id: string;
  question: string;
  category: "Policy & Gates" | "Verdict & Trust" | "Simulation & Metrics" | "Operations";
  shortAnswer: string;
  rootCauses: string[];
  howSystemBehaves: string[];
  adminResolutionSteps: string[];
  relatedRoute?: string;
  relatedRouteLabel?: string;
}

export interface GuidedTourStop {
  stopNumber: number;
  id: string;
  title: string;
  subtitle: string;
  targetMode: GuideMode;
  targetSectionId?: string;
  estimatedMinutes: string;
  keyTakeaways: string[];
  narrative: string;
  actionLabel: string;
}

