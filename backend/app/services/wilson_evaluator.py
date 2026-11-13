import math
from typing import Tuple, Optional


class WilsonScoreEvaluator:
    """
    Calculates Wilson Score Confidence Intervals (95% default) for empirical
    proportions, particularly False Positive prediction precision.
    Protects against the small-sample zero-failure fallacy.
    """

    DEFAULT_Z_95 = 1.959963984540054  # 95% two-tailed confidence level

    @classmethod
    def calculate_wilson_interval(
        cls,
        successes: int,
        total: int,
        z: float = DEFAULT_Z_95
    ) -> Tuple[float, float]:
        """
        Calculates (lower_bound, upper_bound) of Wilson Score Interval.
        If total == 0, returns (0.0, 0.0).
        """
        if total <= 0:
            return 0.0, 0.0

        p = float(successes) / float(total)
        z2 = z * z
        denominator = 1.0 + (z2 / total)
        center = p + (z2 / (2.0 * total))
        margin = z * math.sqrt((p * (1.0 - p) / total) + (z2 / (4.0 * total * total)))

        lower = max(0.0, (center - margin) / denominator)
        upper = min(1.0, (center + margin) / denominator)
        return round(lower, 4), round(upper, 4)

    @classmethod
    def calculate_lower_bound(
        cls,
        successes: int,
        total: int,
        z: float = DEFAULT_Z_95
    ) -> float:
        """Returns the lower 95% confidence bound."""
        lower, _ = cls.calculate_wilson_interval(successes, total, z)
        return lower

