"use client";

import React from "react";
import { PhasePlaceholder } from "@/components/common/PhasePlaceholder";

export default function PromptStudioPage() {
  return (
    <PhasePlaceholder
      title="Rule Prompt Studio & Version Management"
      phase={2}
      description="The Rule Prompt Studio allows SOC engineers to manage, version, compare, and rollback rule-specific LLM investigation prompts. In Phase 2, initial prompt drafts are generated deterministically from imported SIEM rule specifications (clearly labeled as template-generated drafts, not AI-generated) without requiring any active LLM."
      milestones={[
        "Rule-specific prompt editing with draft and approved states",
        "Deterministic template generation from parsed SIEM rule definitions",
        "Version comparison, diff viewer, and rollback mechanism",
        "Structured prompt schema: detection conditions, required evidence, TP/FP indicators, escalation criteria",
      ]}
      plannedArchitecture="Rule prompt versioning tables in PostgreSQL with semantic diffing, approval gating, and human sign-off."
    />
  );
}
