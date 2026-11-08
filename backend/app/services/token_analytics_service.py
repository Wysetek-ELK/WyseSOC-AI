from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.token_usage import TokenUsageRecord


class TokenAnalyticsService:
    """
    Token Analytics Service on Server 1.
    Provides detailed bifurcation and analysis of token consumption:
    - Input (Prompt) Tokens vs Output (Completion) Tokens
    - Bifurcated by Process Type (Incident Triage, Batch Triage, Simulation Replay, Policy Testing)
    - Bifurcated by Model Identifier
    - Bifurcated by Time Series (Daily / Hourly trend)
    - Bifurcated by Detection Rule
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_token_usage(
        self,
        process_type: str,
        model_identifier: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: Optional[int] = None,
        latency_ms: int = 0,
        incident_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        process_id: Optional[str] = None,
        is_simulated: bool = False,
        executed_by_user: str = "system",
        details: Optional[Dict[str, Any]] = None,
    ) -> TokenUsageRecord:
        """Records a new token usage event into the Server 1 persistent ledger."""
        tot = total_tokens if total_tokens is not None else (prompt_tokens + completion_tokens)
        record = TokenUsageRecord(
            process_type=process_type.upper().strip(),
            process_id=process_id,
            incident_id=incident_id,
            rule_id=rule_id,
            model_identifier=model_identifier,
            prompt_tokens=max(0, int(prompt_tokens)),
            completion_tokens=max(0, int(completion_tokens)),
            total_tokens=max(0, int(tot)),
            latency_ms=max(0, int(latency_ms)),
            is_simulated=is_simulated,
            executed_by_user=executed_by_user,
            timestamp=datetime.utcnow(),
            details=details or {},
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_bifurcated_analytics(
        self,
        window_days: int = 30,
        process_type: Optional[str] = None,
        model_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates comprehensive bifurcated token analytics across all processes.
        """
        cutoff = datetime.utcnow() - timedelta(days=window_days)

        # Base filter
        filters = [TokenUsageRecord.timestamp >= cutoff]
        if process_type:
            filters.append(TokenUsageRecord.process_type == process_type.upper().strip())
        if model_identifier:
            filters.append(TokenUsageRecord.model_identifier == model_identifier)

        # 1. High-level aggregates
        agg_stmt = (
            select(
                func.count(TokenUsageRecord.id).label("total_calls"),
                func.coalesce(func.sum(TokenUsageRecord.total_tokens), 0).label("sum_total"),
                func.coalesce(func.sum(TokenUsageRecord.prompt_tokens), 0).label("sum_prompt"),
                func.coalesce(func.sum(TokenUsageRecord.completion_tokens), 0).label("sum_completion"),
                func.coalesce(func.avg(TokenUsageRecord.latency_ms), 0.0).label("avg_latency"),
            )
            .where(*filters)
        )
        agg_res = await self.db.execute(agg_stmt)
        total_calls, sum_total, sum_prompt, sum_completion, avg_latency = agg_res.one()

        prompt_pct = round((sum_prompt / sum_total * 100.0), 1) if sum_total > 0 else 0.0
        completion_pct = round((sum_completion / sum_total * 100.0), 1) if sum_total > 0 else 0.0

        # 2. Bifurcation by Process Type
        proc_stmt = (
            select(
                TokenUsageRecord.process_type,
                func.count(TokenUsageRecord.id).label("calls"),
                func.coalesce(func.sum(TokenUsageRecord.prompt_tokens), 0).label("prompt_toks"),
                func.coalesce(func.sum(TokenUsageRecord.completion_tokens), 0).label("comp_toks"),
                func.coalesce(func.sum(TokenUsageRecord.total_tokens), 0).label("total_toks"),
                func.coalesce(func.avg(TokenUsageRecord.latency_ms), 0.0).label("avg_lat"),
            )
            .where(*filters)
            .group_by(TokenUsageRecord.process_type)
            .order_by(desc("total_toks"))
        )
        proc_res = await self.db.execute(proc_stmt)
        by_process = []
        for r in proc_res.all():
            p_type, calls, p_tok, c_tok, t_tok, a_lat = r
            pct = round((t_tok / sum_total * 100.0), 1) if sum_total > 0 else 0.0
            by_process.append({
                "process_type": p_type,
                "calls": calls,
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "total_tokens": t_tok,
                "percentage_of_total": pct,
                "avg_latency_ms": round(float(a_lat), 1),
            })

        # 3. Bifurcation by Model Identifier
        model_stmt = (
            select(
                TokenUsageRecord.model_identifier,
                func.count(TokenUsageRecord.id).label("calls"),
                func.coalesce(func.sum(TokenUsageRecord.prompt_tokens), 0).label("prompt_toks"),
                func.coalesce(func.sum(TokenUsageRecord.completion_tokens), 0).label("comp_toks"),
                func.coalesce(func.sum(TokenUsageRecord.total_tokens), 0).label("total_toks"),
            )
            .where(*filters)
            .group_by(TokenUsageRecord.model_identifier)
            .order_by(desc("total_toks"))
        )
        model_res = await self.db.execute(model_stmt)
        by_model = []
        for r in model_res.all():
            m_id, calls, p_tok, c_tok, t_tok = r
            pct = round((t_tok / sum_total * 100.0), 1) if sum_total > 0 else 0.0
            by_model.append({
                "model_identifier": m_id,
                "calls": calls,
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "total_tokens": t_tok,
                "percentage_of_total": pct,
            })

        # 4. Recent Transactions Ledger (Last 50 entries)
        recent_stmt = (
            select(TokenUsageRecord)
            .where(*filters)
            .order_by(desc(TokenUsageRecord.timestamp))
            .limit(50)
        )
        recent_res = await self.db.execute(recent_stmt)
        recent_records = []
        for rec in recent_res.scalars().all():
            recent_records.append({
                "id": rec.id,
                "process_type": rec.process_type,
                "process_id": rec.process_id,
                "incident_id": rec.incident_id,
                "rule_id": rec.rule_id,
                "model_identifier": rec.model_identifier,
                "prompt_tokens": rec.prompt_tokens,
                "completion_tokens": rec.completion_tokens,
                "total_tokens": rec.total_tokens,
                "latency_ms": rec.latency_ms,
                "is_simulated": rec.is_simulated,
                "executed_by_user": rec.executed_by_user,
                "timestamp": rec.timestamp.isoformat() + "Z",
                "details": rec.details,
            })

        return {
            "window_days": window_days,
            "cutoff_timestamp": cutoff.isoformat() + "Z",
            "storage_location": "Server 1 Persistent Database",
            "totals": {
                "total_tokens": sum_total,
                "prompt_tokens": sum_prompt,
                "completion_tokens": sum_completion,
                "prompt_percentage": prompt_pct,
                "completion_percentage": completion_pct,
                "total_calls": total_calls,
                "avg_latency_ms": round(float(avg_latency), 1),
            },
            "by_process": by_process,
            "by_model": by_model,
            "recent_ledger": recent_records,
        }

