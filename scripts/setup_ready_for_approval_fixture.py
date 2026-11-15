import sys, os, json, uuid
sys.path.insert(0, os.path.abspath("backend"))
import asyncio
from datetime import datetime, timezone
from app.database import AsyncSessionLocal
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule_learning import RuleLearningProfile
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.services.production_readiness_service import ProductionReadinessService
from sqlalchemy import select

def iso_now():
    return datetime.now(timezone.utc)

async def setup():
    async with AsyncSessionLocal() as db:
        # Check if RULE-READY-001 exists or create it
        q = select(Rule).where(Rule.rule_id == "RULE-READY-001")
        rule = (await db.execute(q)).scalars().first()
        if not rule:
            rule = Rule(
                id=str(uuid.uuid4()),
                rule_id="RULE-READY-001",
                name="Okta Identity Engine: Privileged Credential Stuffing Attack Against Administrator Accounts [READY FOR APPROVAL]",
                event_type="PH_RULE_READY_AUTH_STUFFING",
                description="High confidence credential stuffing attack targeting administrative accounts with validated ground truth",
                severity="HIGH",
                status="ACTIVE",
                data_source="Identity Provider",
                detection_tech="Behavioral Threshold",
                pattern_logic="SELECT srcIp, targetUser, count(*) FROM events WHERE eventType = 'PH_RULE_READY_AUTH_STUFFING' GROUP BY srcIp, targetUser HAVING count(*) > 20",
                remediation="Force MFA verification and reset administrative credentials",
                raw_rule_text="rule Okta_Admin_Stuffing { eventType = 'PH_RULE_READY_AUTH_STUFFING' }",
            )
            db.add(rule)
            await db.flush()

        # Rule prompt
        rp_q = select(RulePrompt).where(RulePrompt.rule_id == rule.id)
        rp = (await db.execute(rp_q)).scalars().first()
        if not rp:
            rp = RulePrompt(
                id=f"prompt-{rule.id}",
                rule_id=rule.id,
                title=f"{rule.name} Investigation Policy",
                ai_execution_suspended=False,
            )
            db.add(rp)
            await db.flush()

        # Candidate draft version
        pv_q = select(PromptVersion).where(PromptVersion.prompt_id == rp.id)
        pv = (await db.execute(pv_q)).scalars().first()
        if not pv:
            pv = PromptVersion(
                id=f"pv-{rule.id}-v1",
                prompt_id=rp.id,
                version_number=1,
                status="DRAFT",
                is_template_draft=False,
                common_prompt="Standard SOC Triaging Common Baseline Prompt v2.0",
                rule_specific_prompt="Analyze administrative Okta authentication failure bursts. Check for distributed source IPs and targeted privileged accounts.",
                detection_conditions="Over 20 failed login attempts within 5 minutes against Administrator accounts.",
                required_evidence="src_ip, target_user, auth_result, user_agent, client_country",
                tp_indicators="Rapid distributed password spraying matching known botnet CIDRs, followed by suspicious session establishment.",
                fp_indicators="Authorized IT scheduled automated credential synchronization script running from corporate subnet.",
                missing_info_criteria="Missing user_agent or geo-IP telemetry from authentication payload.",
                escalation_conditions="Successful login following multiple failed attempts from unmanaged remote IP.",
                analyst_questions='["Has the targeted administrator account been locked out?", "Did MFA push notification trigger on administrator device?"]',
                change_summary="Candidate policy version ready for production sign-off",
                quality_status="APPROVAL_ELIGIBLE",
                quality_score=94.0,
            )
            db.add(pv)
            await db.flush()

        # Snapshot with VERIFIED definition and AUTHENTICATION archetype
        snap_q = select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id)
        snap = (await db.execute(snap_q)).scalars().first()
        if not snap:
            snap = RuleIntelligenceSnapshot(
                id=str(uuid.uuid4()),
                rule_id=rule.id,
                rule_identifier=rule.rule_id,
                primary_archetype="AUTHENTICATION",
                secondary_archetype="CREDENTIAL_ACCESS",
                definition_status="VERIFIED",
                source_provenance="FORTISIEM_CANONICAL_XML",
                threshold=20,
                threshold_unit="failures",
                aggregation_window=300,
                review_required=False,
                semantics_payload={"detection_objective": "Detects high-volume credential stuffing attacks targeting administrative accounts."},
                rule_digest=f"sha256:{uuid.uuid4().hex[:16]}",
            )
            db.add(snap)
            await db.flush()

        # Learning profile with >30 reviews (e.g. 35 reviews: 32 TP, 3 FP -> 98% precision, 96% Wilson)
        prof_q = select(RuleLearningProfile).where(RuleLearningProfile.rule_id == rule.id)
        prof = (await db.execute(prof_q)).scalars().first()
        if not prof:
            prof = RuleLearningProfile(
                id=str(uuid.uuid4()),
                rule_id=rule.id,
                rule_identifier=rule.rule_id,
                customer="DEFAULT",
                primary_archetype="AUTHENTICATION",
                lifecycle_stage="SUPERVISED_PILOT",
                active_prompt_version_id=pv.id,
                total_incidents_processed=45,
                total_analyst_reviews=35,
                verified_tp_count=32,
                verified_fp_count=3,
                ai_correct_count=34,
                ai_incorrect_count=1,
                abstention_count=0,
                validation_failure_count=0,
                empirical_accuracy=0.971,
                fp_precision=0.985,
                tp_recall=0.970,
                wilson_lower_bound=0.962,
                error_distribution={"agreement_tp": 31, "agreement_fp": 3, "disputed": 1},
                last_evaluated_at=iso_now(),
            )
            db.add(prof)
            await db.flush()

        from app.services.policy_quality_validator import PolicyQualityValidator
        real_policy_digest = PolicyQualityValidator.compute_policy_digest(pv)

        # Historical evaluation simulation run
        sim_q = select(HistoricalEvaluationRunRecord).where(HistoricalEvaluationRunRecord.rule_id == rule.id)
        sim = (await db.execute(sim_q)).scalars().first()
        if not sim:
            sim = HistoricalEvaluationRunRecord(
                id=str(uuid.uuid4()),
                run_name=f"Validation Simulation for {rule.rule_id}",
                rule_id=rule.id,
                archetype="AUTHENTICATION",
                dataset_id="ds_eval_001",
                dataset_hash="sha256:evaldataset",
                policy_version_id=str(pv.id),
                status="COMPLETED",
                validation_state="PASSED",
                total_cases=35,
                evaluated_cases=35,
                verified_ground_truth_cases=35,
                metrics={
                    "balanced_accuracy": 0.975,
                    "overall_accuracy": 0.971,
                    "verified_ground_truth_cases": 35,
                    "critical_false_negatives": 0,
                },
                regression_summary={"regression_status": "NO_REGRESSION"},
                config_snapshot={
                    "provider_type": "OPENAI_COMPATIBLE",
                    "model_identifier": "qwen2.5-7b-instruct-awq",
                    "is_simulated": False,
                    "policy_digest": real_policy_digest,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
            )
            db.add(sim)
            await db.flush()
        else:
            sim.validation_state = "PASSED"
            sim.config_snapshot = {
                "provider_type": "OPENAI_COMPATIBLE",
                "model_identifier": "qwen2.5-7b-instruct-awq",
                "is_simulated": False,
                "policy_digest": real_policy_digest,
            }
            db.add(sim)
            await db.flush()

        # Quality assessment record with all 8 gates passed
        qa_q = select(PolicyQualityAssessmentRecord).where(PolicyQualityAssessmentRecord.rule_id == rule.id)
        qa = (await db.execute(qa_q)).scalars().first()
        gate_results = {
            "G1_RULE_INTEGRITY": {"status": "PASSED", "score": 20, "max_score": 20},
            "G2_ARCHETYPE_RELEVANCE": {"status": "PASSED", "score": 10, "max_score": 10},
            "G3_EVIDENCE_FEASIBILITY": {"status": "PASSED", "score": 20, "max_score": 20},
            "G4_TP_CRITERIA_VALIDITY": {"status": "PASSED", "score": 10, "max_score": 10},
            "G5_FP_CRITERIA_VALIDITY": {"status": "PASSED", "score": 10, "max_score": 10},
            "G6_ABSTENTION_ESCALATION": {"status": "PASSED", "score": 10, "max_score": 10},
            "G7_POLICY_CONSISTENCY": {"status": "PASSED", "score": 5, "max_score": 5},
            "G8_SIMULATION_REGRESSION": {"status": "PASSED", "score": 5, "max_score": 5},
        }
        if not qa:
            qa = PolicyQualityAssessmentRecord(
                id=str(uuid.uuid4()),
                rule_id=rule.id,
                prompt_version_id=pv.id,
                version_number=1,
                archetype="AUTHENTICATION",
                quality_score=94.0,
                approval_eligible=True,
                simulation_status="COMPLETED",
                score_breakdown={"detection_semantics": 20, "evidence_contract": 20, "tp_fp_criteria": 20, "abstention_escalation": 10, "internal_consistency": 5, "historical_simulation": 5},
                gate_results=gate_results,
                blocking_issues=[],
                warnings=[],
                missing_evidence_mappings=[],
                recommendations=["Ready for Administrator sign-off."],
                policy_digest=f"sha256:{uuid.uuid4().hex[:16]}",
                contract_digest=f"sha256:{uuid.uuid4().hex[:16]}",
                rule_digest=f"sha256:{uuid.uuid4().hex[:16]}",
                validator_version="v2.2.0",
                evaluated_at=iso_now(),
            )
            db.add(qa)
            await db.flush()

        await db.commit()
        print(f"Setup complete for rule {rule.rule_id} (ID: {rule.id})")

        # Evaluate readiness
        res = await ProductionReadinessService.evaluate_readiness(db, rule.id, version_id=pv.id)
        print("\n=== EVALUATION RESULT ===")
        print(f"Rule Name: {res.rule_name}")
        print(f"Readiness Status: {res.readiness_status}")
        print(f"Readiness Label: {res.readiness_label}")
        print(f"Approval Eligible: {res.approval_eligible}")
        print(f"Recommended Action: {res.recommended_action.title} ({res.recommended_action.label})")
        print("Stages:")
        for s in res.stages:
            print(f"  Stage {s.stage_number} ({s.stage_name}): {s.status}")

if __name__ == "__main__":
    asyncio.run(setup())
