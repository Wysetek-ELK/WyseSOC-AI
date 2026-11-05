"use client";

import React from "react";
import { PhasePlaceholder } from "@/components/common/PhasePlaceholder";

export default function AnalystAttentionPage() {
  return (
    <PhasePlaceholder
      title="Analyst Attention Queue & Investigation Workflow"
      phase={2}
      description="The Analyst Attention Queue enables security analysts to claim pending incidents, record investigation questions & answers, attach supporting evidence, and record verified verdicts (TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION) with separate insufficient evidence reasoning without altering historical ground truth."
      milestones={[
        "Interactive analyst triage state transitions (Pending, Assigned, In Progress, Reviewed, Closed)",
        "SOC analyst Q&A thread management per incident",
        "Dual-verdict architecture (preserves historical verdict while recording analyst-verified outcome)",
        "Evidence gap flagging and dispute marking",
      ]}
      plannedArchitecture="Backend SQLAlchemy investigation & question tables, isolated from ground truth, with deterministic similar-case matching."
    />
  );
}
