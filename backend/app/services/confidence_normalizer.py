"""
Confidence Normalizer (AIS 2.0 V8.2).
Standardizes, validates, and interprets model confidence scores into canonical
confidence_percent (0.0 to 100.0) without silent inflation or loss of auditability.
"""

import math
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class NormalizedConfidence(BaseModel):
    is_valid: bool = False
    raw_confidence: Optional[float] = None
    raw_scale: Optional[str] = None
    normalized_percent: Optional[float] = None
    interpretation: str = "UNCHECKED"
    error_message: Optional[str] = None
    confidence_limitations: list = Field(default_factory=list)


class ConfidenceNormalizer:
    """
    Deterministic Confidence Normalization Engine.
    Enforces unambiguous scale declarations and rejects ambiguous (0.0 < conf <= 1.0)
    values when confidence_scale is not explicitly provided.
    """

    ALLOWED_SCALES = {"PERCENT_0_100", "PROBABILITY_0_1"}

    @classmethod
    def normalize(
        cls,
        raw_confidence: Any,
        declared_scale: Optional[str] = None,
    ) -> NormalizedConfidence:
        """
        Normalizes raw model confidence to canonical confidence_percent (0.0 to 100.0).

        Rules:
        1. None or missing -> INVALID (MISSING_CONFIDENCE).
        2. Non-numeric, NaN, Infinity -> INVALID (NAN_OR_INF).
        3. Negative (< 0.0) or out-of-range (> 100.0) -> INVALID (OUT_OF_RANGE).
        4. Exactly 0.0 -> VALID (0.0%), unambiguous regardless of scale.
        5. Declared scale 'PERCENT_0_100':
           - 0.0 <= conf <= 100.0 -> VALID (conf).
           - Otherwise -> INVALID.
        6. Declared scale 'PROBABILITY_0_1':
           - 0.0 <= conf <= 1.0 -> VALID (conf * 100.0).
           - Otherwise -> INVALID.
        7. Undeclared scale (declared_scale is None or empty):
           - conf > 1.0 and conf <= 100.0 -> VALID (conf as percentage, UNAMBIGUOUS_PERCENT).
           - 0.0 < conf <= 1.0 -> REJECTED (AMBIGUOUS_SCALE_REJECTED).
             Per V8.2 security invariant: emitting 0.95 without scale declaration
             cannot be silently multiplied by 100.
        """
        if raw_confidence is None:
            return NormalizedConfidence(
                is_valid=False,
                interpretation="MISSING_CONFIDENCE",
                error_message="Model confidence score is missing or null.",
            )

        try:
            conf_float = float(raw_confidence)
        except (ValueError, TypeError):
            return NormalizedConfidence(
                is_valid=False,
                interpretation="NON_NUMERIC_CONFIDENCE",
                error_message=f"Confidence value '{raw_confidence}' cannot be parsed as a float.",
            )

        if math.isnan(conf_float) or math.isinf(conf_float):
            return NormalizedConfidence(
                is_valid=False,
                raw_confidence=conf_float,
                interpretation="NAN_OR_INF",
                error_message="Confidence value is NaN or Infinite.",
            )

        if conf_float < 0.0 or conf_float > 100.0:
            return NormalizedConfidence(
                is_valid=False,
                raw_confidence=conf_float,
                interpretation="OUT_OF_RANGE",
                error_message=f"Confidence value {conf_float} is outside the allowed range [0.0, 100.0].",
            )

        clean_scale = str(declared_scale).strip().upper() if declared_scale else None
        if clean_scale and clean_scale not in cls.ALLOWED_SCALES:
            return NormalizedConfidence(
                is_valid=False,
                raw_confidence=conf_float,
                raw_scale=clean_scale,
                interpretation="UNKNOWN_DECLARED_SCALE",
                error_message=f"Unknown confidence_scale '{clean_scale}'. Allowed: {sorted(cls.ALLOWED_SCALES)}.",
            )

        # Exactly 0.0 is zero under any scale
        if conf_float == 0.0:
            return NormalizedConfidence(
                is_valid=True,
                raw_confidence=0.0,
                raw_scale=clean_scale or "PERCENT_0_100",
                normalized_percent=0.0,
                interpretation="ZERO_UNAMBIGUOUS",
            )

        # Declared percentage scale
        if clean_scale == "PERCENT_0_100":
            return NormalizedConfidence(
                is_valid=True,
                raw_confidence=conf_float,
                raw_scale=clean_scale,
                normalized_percent=round(conf_float, 2),
                interpretation="DECLARED_PERCENT",
            )

        # Declared probability scale
        if clean_scale == "PROBABILITY_0_1":
            if conf_float <= 1.0:
                pct = round(conf_float * 100.0, 2)
                return NormalizedConfidence(
                    is_valid=True,
                    raw_confidence=conf_float,
                    raw_scale=clean_scale,
                    normalized_percent=pct,
                    interpretation="DECLARED_PROBABILITY_CONVERTED",
                )
            else:
                return NormalizedConfidence(
                    is_valid=False,
                    raw_confidence=conf_float,
                    raw_scale=clean_scale,
                    interpretation="PROBABILITY_EXCEEDS_ONE",
                    error_message=f"Confidence {conf_float} exceeds 1.0 under declared PROBABILITY_0_1 scale.",
                )

        # Undeclared scale:
        if conf_float > 1.0:
            return NormalizedConfidence(
                is_valid=True,
                raw_confidence=conf_float,
                raw_scale="PERCENT_0_100",
                normalized_percent=round(conf_float, 2),
                interpretation="UNAMBIGUOUS_PERCENT",
            )

        # 0.0 < conf_float <= 1.0 without declared scale: Ambiguous!
        return NormalizedConfidence(
            is_valid=False,
            raw_confidence=conf_float,
            raw_scale=None,
            normalized_percent=None,
            interpretation="AMBIGUOUS_SCALE_REJECTED",
            error_message=(
                f"Model emitted confidence {conf_float} in (0.0, 1.0] without declaring "
                f"confidence_scale ('PERCENT_0_100' or 'PROBABILITY_0_1'). "
                "Silent multiplication by 100 is strictly prohibited to prevent false precision."
            ),
            confidence_limitations=[
                f"Ambiguous raw confidence {conf_float} without scale declaration."
            ],
        )
