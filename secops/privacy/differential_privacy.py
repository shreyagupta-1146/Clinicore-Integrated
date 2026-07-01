"""
secops/privacy/differential_privacy.py

Differential-privacy noise for aggregate analytics — ported and hardened from
SentiHealth's deception/noise.py.

Purpose: when the SOC console (or any dashboard/export) shows AGGREGATE
statistics — patient counts, access counts, per-facility rates — an adversary
who can read those aggregates can run inference/aggregation attacks to
reconstruct information about individuals. Adding calibrated Laplacian noise
gives (epsilon, 0)-differential privacy: the released aggregate is provably
close to the true value, but an attacker cannot reliably back out any single
record's contribution.

  Noise ~ Laplace(0, sensitivity / epsilon)
    - lower epsilon  = stronger privacy (more noise)
    - sensitivity    = max change in the query output from one record (usually 1)

Individual authorized lookups are NEVER noised — only released aggregates are.
Also provides moving-target timing jitter to prevent latency fingerprinting.

epsilon default 2.0 (from settings) — a reasonable balance for security metrics
that don't require clinical precision. Use epsilon=1.0 for display-only dashboards.
"""

from __future__ import annotations

import os
import random
import time
from typing import Dict, List, Optional, Union

Number = Union[int, float]

_DEFAULT_EPSILON = float(os.environ.get("DP_NOISE_EPSILON", "2.0"))


def laplace_noise(sensitivity: float = 1.0, epsilon: Optional[float] = None) -> float:
    """Sample from Laplace(0, sensitivity/epsilon). Higher epsilon = less noise."""
    eps = epsilon if epsilon is not None else _DEFAULT_EPSILON
    if eps <= 0:
        return 0.0
    scale = sensitivity / eps
    # Laplace = difference of two exponentials; here: exponential * random sign
    return random.expovariate(1.0 / scale) * random.choice([-1, 1])


def add_noise_to_number(value: Number, sensitivity: float = 1.0, epsilon: Optional[float] = None) -> Number:
    """Add calibrated Laplacian noise to a numeric aggregate."""
    noisy = value + laplace_noise(sensitivity, epsilon)
    if isinstance(value, int):
        return max(0, int(round(noisy)))  # counts stay non-negative integers
    return round(noisy, 3)


def add_noise_to_dict(data: Dict, numeric_keys: Optional[List[str]] = None, epsilon: Optional[float] = None) -> Dict:
    """Return a copy of `data` with Laplacian noise on the given (or all) numeric keys."""
    out = dict(data)
    for k, v in out.items():
        if numeric_keys and k not in numeric_keys:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = add_noise_to_number(v, epsilon=epsilon)
    return out


def add_noise_to_list(items: List[Dict], numeric_keys: Optional[List[str]] = None, epsilon: Optional[float] = None) -> List[Dict]:
    """Apply add_noise_to_dict to every element of a list of aggregate rows."""
    return [add_noise_to_dict(item, numeric_keys, epsilon) for item in items]


def apply_jitter(base_ms: float = 50.0, jitter_ms: float = 200.0) -> None:
    """Sleep a random duration to break timing-based fingerprinting of defenses."""
    delay = (base_ms + random.uniform(0, jitter_ms)) / 1000.0
    time.sleep(delay)


def privacy_report(epsilon: Optional[float] = None) -> Dict:
    """Metadata to surface in the UI so the DP guarantee is transparent."""
    eps = epsilon if epsilon is not None else _DEFAULT_EPSILON
    return {
        "mechanism": "Laplace",
        "epsilon": eps,
        "guarantee": f"({eps}, 0)-differential privacy on released aggregates",
        "applies_to": "aggregate analytics & exports only — never individual authorized lookups",
    }
