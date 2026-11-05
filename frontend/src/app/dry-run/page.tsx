"use client";

import React from "react";
import { PhasePlaceholder } from "@/components/common/PhasePlaceholder";

export default function DryRunPage() {
  return (
    <PhasePlaceholder
      title="Dry-Run Incident Replay Engine"
      phase={3}
      description="The Dry-Run Engine prepares the application for future local LLM integration without connecting to any model during Phase 1-3. It implements a provider-independent ModelProvider backend abstraction with a disabled default provider and fixture-based simulation testing (strictly labeled as SIMULATED)."
      milestones={[
        "Dataset selection with chronological and incident-group-aware leakage prevention",
        "Provider-independent ModelProvider interface (get_health, list_models, analyze_incident, validate_response)",
        "Structured model output schema validation (verdict, reason, evidence refs, questions, validation status)",
        "Simulation provider with prominent SIMULATED watermarks",
      ]}
      plannedArchitecture="Asynchronous execution queue preparing for future OpenAI-compatible inference endpoint (AWS g4dn.2xlarge / Server 2)."
    />
  );
}
