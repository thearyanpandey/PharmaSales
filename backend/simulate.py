"""Monte Carlo stress-test of an optimized allocation.

The optimizer produces a plan against a single *estimate* of territory demand
(required_calls). Real demand is uncertain. For each trial we:

    1. Draw actual demand per territory from a lognormal distribution centered
       on the base estimate (spread controlled by `uncertainty`).
    2. Evaluate the FIXED allocation against that drawn demand:
       realized_coverage[j] = min(1, allocated[j] / drawn_demand[j]).
    3. Record the total covered potential for the trial.

We then report the distribution: mean, 5th percentile (downside / worst-case),
and the probability of hitting a target service level. That is what
"quantify downside risk" means in the resume bullet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from generate_data import Scenario
from optimizer import AllocationResult


@dataclass
class SimulationResult:
    coverage_ratios: List[float]        # per-trial covered/total potential
    mean_coverage: float
    p5_coverage: float                  # 5th percentile — downside
    p95_coverage: float
    std_coverage: float
    prob_meets_target: float            # P(coverage_ratio >= target)
    target: float
    n_trials: int
    histogram: dict                     # {bins: [...], counts: [...]}

    def as_dict(self) -> dict:
        return {
            "mean_coverage": self.mean_coverage,
            "p5_coverage": self.p5_coverage,
            "p95_coverage": self.p95_coverage,
            "std_coverage": self.std_coverage,
            "prob_meets_target": self.prob_meets_target,
            "target": self.target,
            "n_trials": self.n_trials,
            "histogram": self.histogram,
        }


def simulate(
    scenario: Scenario,
    allocation: AllocationResult,
    n_trials: int = 1000,
    uncertainty: float = 0.25,
    target: float = 0.85,
    seed: int = 7,
) -> SimulationResult:
    """Run Monte Carlo trials against a fixed allocation.

    uncertainty: coefficient of variation of demand (0.25 = 25% swings).
    target: service-level threshold for the "probability of meeting target".
    """
    rng = np.random.default_rng(seed)

    terr_ids = [t.id for t in scenario.territories]
    potential = np.array([t.potential for t in scenario.territories], dtype=float)
    base_demand = np.array([t.required_calls for t in scenario.territories], dtype=float)
    allocated = np.array([allocation.allocated.get(t.id, 0.0) for t in scenario.territories], dtype=float)
    total_potential = potential.sum()

    # Lognormal parameters chosen so the distribution's mean ≈ base_demand and
    # its coefficient of variation ≈ `uncertainty`.
    sigma = np.sqrt(np.log(1 + uncertainty ** 2))
    mu = np.log(np.maximum(base_demand, 1e-9)) - 0.5 * sigma ** 2

    coverage_ratios = np.empty(n_trials, dtype=float)
    for k in range(n_trials):
        drawn_demand = rng.lognormal(mean=mu, sigma=sigma)
        drawn_demand = np.maximum(drawn_demand, 1e-9)
        realized_cov = np.minimum(1.0, allocated / drawn_demand)
        coverage_ratios[k] = float((potential * realized_cov).sum() / total_potential)

    counts, edges = np.histogram(coverage_ratios, bins=20, range=(0.0, 1.0))
    histogram = {
        "bins": [round(float(e), 4) for e in edges[:-1]],
        "counts": [int(c) for c in counts],
    }

    return SimulationResult(
        coverage_ratios=[round(float(c), 4) for c in coverage_ratios],
        mean_coverage=round(float(coverage_ratios.mean()), 4),
        p5_coverage=round(float(np.percentile(coverage_ratios, 5)), 4),
        p95_coverage=round(float(np.percentile(coverage_ratios, 95)), 4),
        std_coverage=round(float(coverage_ratios.std()), 4),
        prob_meets_target=round(float((coverage_ratios >= target).mean()), 4),
        target=target,
        n_trials=n_trials,
        histogram=histogram,
    )


if __name__ == "__main__":
    from generate_data import generate_scenario
    from optimizer import optimize

    sc = generate_scenario()
    alloc = optimize(sc)
    sim = simulate(sc, alloc, n_trials=2000, uncertainty=0.3)
    print(f"Trials              : {sim.n_trials}")
    print(f"Mean coverage       : {sim.mean_coverage * 100:.1f}%")
    print(f"Worst-case (5th pct): {sim.p5_coverage * 100:.1f}%")
    print(f"Best-case (95th pct): {sim.p95_coverage * 100:.1f}%")
    print(f"P(coverage >= {sim.target:.0%}) : {sim.prob_meets_target * 100:.1f}%")
