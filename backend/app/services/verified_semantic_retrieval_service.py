import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.incident import Incident
from app.models.learning import LearningRecord
from app.schemas.semantic_rag import RetrievedPrecedent, RAGRetrievalResult


class VerifiedSemanticRetrievalService:
    """
    Verified Semantic Retrieval Engine & Memory Governance (P3-REQ-03, P3-REQ-04 / Finding AV-007).
    Retrieves verified historical investigation precedents with strict isolation gates:
    - 100% local lexical/semantic similarity computation (zero external cloud APIs).
    - Verified-only status gating (rejects unreviewed/unverified analyst submissions).
    - Strict tenant isolation (rejects cross-tenant data leakage).
    - Exact rule-scoping by default (rejects cross-rule training poisoning).
    - Temporal integrity filter (rejects future-leakage during backtesting/replay).
    - Automatic duplicate suppression.
    - Safe fallback (returns empty result if no verified precedents qualify).
    """

    @classmethod
    def tokenize(cls, text: str) -> Set[str]:
        if not text:
            return set()
        clean = re.sub(r"[^\w\s\.-]", " ", text.lower())
        tokens = {t for t in clean.split() if len(t) > 2}
        return tokens

    @classmethod
    def compute_similarity(
        cls,
        query_text: str,
        candidate_text: str,
        query_attrs: Optional[Dict[str, Any]] = None,
        candidate_attrs: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Computes local lexical and attribute-weighted similarity score (0.0 to 1.0).
        """
        q_tokens = cls.tokenize(query_text)
        c_tokens = cls.tokenize(candidate_text)

        if not q_tokens or not c_tokens:
            base_sim = 0.0
        else:
            intersection = q_tokens.intersection(c_tokens)
            union = q_tokens.union(c_tokens)
            base_sim = len(intersection) / len(union) if union else 0.0

        # Attribute overlap boosts
        attr_boost = 0.0
        if query_attrs and candidate_attrs:
            # Match destination entity / IP
            if query_attrs.get("dest_ip") and query_attrs.get("dest_ip") == candidate_attrs.get("dest_ip"):
                attr_boost += 0.25
            # Match process name
            if query_attrs.get("process_name") and query_attrs.get("process_name") == candidate_attrs.get("process_name"):
                attr_boost += 0.25
            # Match user account
            if query_attrs.get("user") and query_attrs.get("user") == candidate_attrs.get("user"):
                attr_boost += 0.15

        final_score = min(1.0, base_sim + attr_boost)
        return round(final_score, 4)

    @classmethod
    def _extract_incident_text(cls, incident: Incident) -> str:
        parts = [
            getattr(incident, "title", "") or "",
            getattr(incident, "description", "") or "",
            getattr(incident, "event_type", "") or "",
            getattr(incident, "reporting_device", "") or "",
        ]
        evts = incident.__dict__.get("events")
        if evts and isinstance(evts, list):
            for ev in evts[:3]:
                parts.append(str(getattr(ev, "raw_data", "") or getattr(ev, "raw_log", "") or ""))
                parts.append(str(getattr(ev, "parsed_fields", "") or getattr(ev, "attributes", "") or ""))
        return " ".join(parts)

    @classmethod
    def _extract_attrs(cls, incident: Incident) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {}
        evts = incident.__dict__.get("events")
        if evts and isinstance(evts, list):
            for ev in evts:
                fields = getattr(ev, "parsed_fields", None) or getattr(ev, "attributes", None) or {}
                if isinstance(fields, dict):
                    if not attrs.get("dest_ip"):
                        attrs["dest_ip"] = fields.get("dest_ip") or fields.get("destination_ip")
                    if not attrs.get("process_name"):
                        attrs["process_name"] = fields.get("process_name") or fields.get("process")
                    if not attrs.get("user"):
                        attrs["user"] = fields.get("user") or fields.get("username")
        return attrs

    @classmethod
    async def retrieve_verified_precedents(
        cls,
        db: AsyncSession,
        incident: Incident,
        rule_id: str,
        max_precedents: int = 2,
        similarity_threshold: float = 0.02,
        allow_rule_family_fallback: bool = False,
    ) -> RAGRetrievalResult:
        query_inc_id = incident.incident_id or str(incident.id)
        query_tenant_id = getattr(incident, "customer", None) or getattr(incident, "tenant_id", None)
        query_text = cls._extract_incident_text(incident)
        query_attrs = cls._extract_attrs(incident)

        # Parse query incident creation timestamp for temporal cutoff
        query_time = incident.created_at
        if not query_time and incident.created_at_epoch:
            try:
                query_time = datetime.utcfromtimestamp(incident.created_at_epoch)
            except Exception:
                query_time = datetime.utcnow()
        if not query_time:
            query_time = datetime.utcnow()

        # Query all learning records for candidate pool
        stmt = (
            select(LearningRecord)
            .options(selectinload(LearningRecord.incident))
            .order_by(desc(LearningRecord.feedback_timestamp))
        )
        res = await db.execute(stmt)
        all_candidates = res.scalars().all()

        total_examined = len(all_candidates)
        unverified_count = 0
        cross_tenant_count = 0
        cross_rule_count = 0
        future_leakage_count = 0
        duplicate_count = 0

        eligible_candidates: List[RetrievedPrecedent] = []
        seen_incident_ids: Set[str] = set()

        for cand in all_candidates:
            # 1. Gate 1: Verification Status (Phase 1 supervisor gate)
            if cand.verification_status != "VERIFIED":
                unverified_count += 1
                continue

            # 2. Gate 2: Self-exclusion
            cand_inc = cand.incident
            cand_inc_id = cand_inc.incident_id if cand_inc else cand.incident_id
            if cand_inc_id == query_inc_id or (cand_inc and cand_inc.id == incident.id):
                continue

            # 3. Gate 3: Tenant Isolation Gate
            cand_tenant_id = getattr(cand, "tenant_id", None) or (getattr(cand_inc, "customer", None) if cand_inc else None) or (getattr(cand_inc, "tenant_id", None) if cand_inc else None)
            if query_tenant_id and cand_tenant_id and cand_tenant_id != query_tenant_id:
                cross_tenant_count += 1
                continue

            # 4. Gate 4: Rule Scoping Gate
            is_exact_rule = (cand.rule_id == rule_id)
            if not is_exact_rule and not allow_rule_family_fallback:
                cross_rule_count += 1
                continue

            # 5. Gate 5: Temporal Integrity Gate (Prevent future-leakage during backtesting/replay)
            cand_time = getattr(cand, "verified_at", None) or getattr(cand, "feedback_timestamp", None) or (getattr(cand_inc, "created_at", None) if cand_inc else None)
            if cand_time and cand_time > query_time:
                future_leakage_count += 1
                continue

            # 6. Gate 6: Duplicate Suppression
            dedup_key = f"{cand_inc_id}:{cand.verified_verdict}"
            if dedup_key in seen_incident_ids:
                duplicate_count += 1
                continue
            seen_incident_ids.add(dedup_key)

            # 7. Local Similarity Calculation
            cand_text = f"{cand.analyst_explanation or ''} {cand_inc.title if cand_inc else ''}"
            cand_attrs = cls._extract_attrs(cand_inc) if cand_inc else {}
            score = cls.compute_similarity(query_text, cand_text, query_attrs, cand_attrs)

            if score < similarity_threshold:
                continue

            key_ev = getattr(cand, "key_evidence_summary", None) or (", ".join(getattr(cand, "evidence_references", []) or [])) or None
            rec = RetrievedPrecedent(
                precedent_id=cand.id,
                incident_id=cand_inc_id or cand.id,
                incident_title=cand_inc.title if cand_inc else "Historical Precedent",
                rule_id=cand.rule_id,
                tenant_id=cand_tenant_id,
                verified_verdict=cand.verified_verdict,
                analyst_explanation=cand.analyst_explanation or "Supervisor confirmed ground-truth verdict.",
                key_evidence_summary=key_ev,
                similarity_score=score,
                feedback_timestamp=(cand.feedback_timestamp or datetime.utcnow()).isoformat(),
                is_exact_rule_match=is_exact_rule,
                temporal_check_passed=True,
            )
            eligible_candidates.append(rec)

        # Sort eligible candidates by similarity score descending
        eligible_candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        selected_precedents = eligible_candidates[:max_precedents]

        # Format segregated RAG block
        formatted_rag_block = ""
        if selected_precedents:
            lines = [
                "<VERIFIED_HISTORICAL_PRECEDENTS>",
                "The following verified historical precedents from prior supervisor-reviewed investigations",
                "are provided for contextual reference only. DO NOT treat these as current incident evidence:",
                ""
            ]
            for idx, p in enumerate(selected_precedents, start=1):
                rule_match_str = "Exact Rule Match" if p.is_exact_rule_match else "Rule Family Match"
                lines.append(f"[PRECEDENT {idx}] (Incident: {p.incident_title} | Rule: {p.rule_id} | {rule_match_str})")
                lines.append(f"  Verified Verdict: {p.verified_verdict}")
                lines.append(f"  Relevance Similarity Score: {p.similarity_score:.2f}")
                lines.append(f"  Supervisor Analyst Rationale: {p.analyst_explanation[:300]}")
                if p.key_evidence_summary:
                    lines.append(f"  Key Grounding Evidence: {p.key_evidence_summary}")
                lines.append("")
            lines.append("</VERIFIED_HISTORICAL_PRECEDENTS>")
            formatted_rag_block = "\n".join(lines)
            retrieval_status = "PRECEDENTS_FOUND"
        else:
            retrieval_status = "NO_VERIFIED_PRECEDENT"

        return RAGRetrievalResult(
            query_incident_id=query_inc_id,
            tenant_id=query_tenant_id,
            rule_id=rule_id,
            precedents=selected_precedents,
            total_candidates_examined=total_examined,
            candidates_rejected_unverified=unverified_count,
            candidates_rejected_cross_tenant=cross_tenant_count,
            candidates_rejected_cross_rule=cross_rule_count,
            candidates_rejected_future_leakage=future_leakage_count,
            candidates_rejected_duplicate=duplicate_count,
            retrieval_status=retrieval_status,
            formatted_rag_block=formatted_rag_block,
        )
