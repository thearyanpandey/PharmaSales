"""Linear-programming territory-alignment optimizer.

Decision variables:  x[i][j] = call capacity rep i allocates to territory j.

Objective:  maximize total covered potential
            = Σ_j potential[j] * coverage[j]
    where coverage[j] = allocated[j] / required[j], capped at 1 by the
    no-over-coverage constraint below. Because required[j] is a constant, the
    objective stays linear:  Σ_j (potential[j] / required[j]) * allocated[j].

Constraints:
    - Each rep's total allocation ≤ rep capacity.
    - Each territory's allocation ≤ its required call volume (no wasted
      over-coverage — coverage never exceeds 1).
    - Adjacency: a rep can only serve territories in their own region
      (x[i][j] is simply not created when regions differ).
    - Priority floor: must-cover territories get at least `priority_floor` of
      their required calls (a hard service-level guarantee).

Solved with PuLP's default CBC solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pulp

from generate_data import Scenario


@dataclass
class AllocationResult:
    # allocated calls per territory id
    allocated: Dict[int, float]
    coverage: Dict[int, float]          # coverage fraction per territory id
    total_potential: float              # Σ potential over all territories
    covered_potential: float            # Σ potential[j] * coverage[j]
    coverage_ratio: float               # covered_potential / total_potential
    status: str

    def as_dict(self) -> dict:
        return {
            "allocated": self.allocated,
            "coverage": self.coverage,
            "total_potential": self.total_potential,
            "covered_potential": self.covered_potential,
            "coverage_ratio": self.coverage_ratio,
            "status": self.status,
        }


def _region_pairs(scenario: Scenario) -> List[Tuple[int, int]]:
    """Valid (rep, territory) pairs — same region only (adjacency constraint)."""
    pairs = []
    for rep in scenario.reps:
        for terr in scenario.territories:
            if rep.region == terr.region:
                pairs.append((rep.id, terr.id))
    return pairs


def optimize(scenario: Scenario, priority_floor: float = 0.5) -> AllocationResult:
    """Solve the LP allocation for a scenario.

    priority_floor: minimum coverage guaranteed for priority territories
    (0.0 disables the floor). If the floor is infeasible given regional
    capacity, CBC returns an infeasible status and we fall back gracefully.
    """
    reps = {r.id: r for r in scenario.reps}
    terrs = {t.id: t for t in scenario.territories}
    pairs = _region_pairs(scenario)

    prob = pulp.LpProblem("territory_alignment", pulp.LpMaximize)

    # x[(i, j)] ≥ 0 continuous capacity allocation.
    x = {
        (i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0)
        for (i, j) in pairs
    }

    # Objective: maximize covered potential (linear form).
    prob += pulp.lpSum(
        (terrs[j].potential / terrs[j].required_calls) * x[(i, j)]
        for (i, j) in pairs
    )

    # Rep capacity constraints.
    for rep in scenario.reps:
        rep_vars = [x[(i, j)] for (i, j) in pairs if i == rep.id]
        if rep_vars:
            prob += pulp.lpSum(rep_vars) <= rep.capacity, f"cap_rep_{rep.id}"

    # Territory no-over-coverage + optional priority floor.
    for terr in scenario.territories:
        terr_vars = [x[(i, j)] for (i, j) in pairs if j == terr.id]
        if not terr_vars:
            continue
        prob += pulp.lpSum(terr_vars) <= terr.required_calls, f"cap_terr_{terr.id}"
        if terr.priority and priority_floor > 0:
            prob += (
                pulp.lpSum(terr_vars) >= priority_floor * terr.required_calls,
                f"floor_terr_{terr.id}",
            )

    status_code = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    status = pulp.LpStatus[status_code]

    # If the priority floor made it infeasible, retry without the floor so the
    # dashboard still returns a usable (if unconstrained) plan.
    if status != "Optimal" and priority_floor > 0:
        return optimize(scenario, priority_floor=0.0)

    allocated = {t.id: 0.0 for t in scenario.territories}
    for (i, j) in pairs:
        val = x[(i, j)].value() or 0.0
        allocated[j] += val

    coverage = {}
    covered_potential = 0.0
    total_potential = 0.0
    for terr in scenario.territories:
        cov = min(1.0, allocated[terr.id] / terr.required_calls) if terr.required_calls else 0.0
        coverage[terr.id] = cov
        covered_potential += terr.potential * cov
        total_potential += terr.potential

    return AllocationResult(
        allocated={k: round(v, 2) for k, v in allocated.items()},
        coverage={k: round(v, 4) for k, v in coverage.items()},
        total_potential=round(total_potential, 2),
        covered_potential=round(covered_potential, 2),
        coverage_ratio=round(covered_potential / total_potential, 4) if total_potential else 0.0,
        status=status,
    )


def naive_baseline(scenario: Scenario) -> AllocationResult:
    """Naive baseline: within each region, split each rep's capacity evenly
    across that region's territories (capped at required calls). No optimization,
    no awareness of territory potential — the "just spread the reps out" plan.
    """
    terrs = {t.id: t for t in scenario.territories}
    allocated = {t.id: 0.0 for t in scenario.territories}

    # Group territory ids by region.
    region_terrs: Dict[str, List[int]] = {}
    for t in scenario.territories:
        region_terrs.setdefault(t.region, []).append(t.id)

    for rep in scenario.reps:
        region_ids = region_terrs.get(rep.region, [])
        if not region_ids:
            continue
        share = rep.capacity / len(region_ids)
        for j in region_ids:
            allocated[j] += share

    # Cap at required (over-coverage is wasted — matches the LP's coverage cap).
    coverage = {}
    covered_potential = 0.0
    total_potential = 0.0
    for terr in scenario.territories:
        capped = min(allocated[terr.id], terr.required_calls)
        allocated[terr.id] = capped
        cov = min(1.0, capped / terr.required_calls) if terr.required_calls else 0.0
        coverage[terr.id] = cov
        covered_potential += terr.potential * cov
        total_potential += terr.potential

    return AllocationResult(
        allocated={k: round(v, 2) for k, v in allocated.items()},
        coverage={k: round(v, 4) for k, v in coverage.items()},
        total_potential=round(total_potential, 2),
        covered_potential=round(covered_potential, 2),
        coverage_ratio=round(covered_potential / total_potential, 4) if total_potential else 0.0,
        status="Baseline",
    )


def compare(scenario: Scenario, priority_floor: float = 0.5) -> dict:
    """Run baseline vs optimized and compute the honest improvement %."""
    base = naive_baseline(scenario)
    opt = optimize(scenario, priority_floor=priority_floor)
    improvement = (
        (opt.covered_potential - base.covered_potential) / base.covered_potential
        if base.covered_potential
        else 0.0
    )
    return {
        "baseline": base.as_dict(),
        "optimized": opt.as_dict(),
        "improvement": round(improvement, 4),
    }


if __name__ == "__main__":
    from generate_data import generate_scenario

    sc = generate_scenario()
    result = compare(sc)
    base = result["baseline"]
    opt = result["optimized"]
    print(f"Baseline covered potential : {base['covered_potential']:,.0f} "
          f"({base['coverage_ratio'] * 100:.1f}% of total)")
    print(f"Optimized covered potential: {opt['covered_potential']:,.0f} "
          f"({opt['coverage_ratio'] * 100:.1f}% of total)   [{opt['status']}]")
    print(f"Improvement over baseline  : {result['improvement'] * 100:.1f}%")
