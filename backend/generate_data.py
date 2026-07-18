"""Synthetic scenario generator for the PharmaSales territory optimizer.

Produces a set of sales reps and territories with the fields the optimizer and
Monte Carlo layer need. Everything is synthetic but shaped to look like a real
pharma commercial dataset (regions, territory sales potential, call frequency
requirements, rep call capacity).

The data is intentionally synthetic. That is normal and honest for a modeling
demo — the value is in the optimization, not in owning proprietary data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


REGIONS = ["Northeast", "Southeast", "Midwest", "West", "Southwest"]


@dataclass
class Rep:
    id: int
    name: str
    region: str
    capacity: float  # calls the rep can make per period


@dataclass
class Territory:
    id: int
    name: str
    region: str
    potential: float       # market value / high-value physician count
    required_calls: float  # call volume needed for full coverage
    priority: bool         # must-cover territory (has a coverage floor)


@dataclass
class Scenario:
    reps: List[Rep] = field(default_factory=list)
    territories: List[Territory] = field(default_factory=list)

    @property
    def regions(self) -> List[str]:
        return sorted({t.region for t in self.territories})


def generate_scenario(
    n_reps: int = 20,
    n_territories: int = 40,
    n_regions: int = 5,
    avg_capacity: float = 100.0,
    priority_fraction: float = 0.25,
    seed: int = 42,
) -> Scenario:
    """Generate a reproducible synthetic scenario.

    Territories carry a `potential` (business value) and `required_calls`
    (effort for full coverage). Reps have a `capacity` (available calls) and a
    home `region`; a rep can only serve territories in their own region, which
    is what makes the allocation non-trivial.
    """
    rng = np.random.default_rng(seed)

    n_regions = max(1, min(n_regions, len(REGIONS)))
    regions = REGIONS[:n_regions]

    # --- Reps -------------------------------------------------------------
    reps: List[Rep] = []
    for i in range(n_reps):
        region = regions[i % n_regions]  # spread reps roughly evenly
        capacity = float(np.round(rng.normal(avg_capacity, avg_capacity * 0.15)))
        capacity = max(capacity, avg_capacity * 0.4)  # no absurdly small reps
        reps.append(Rep(id=i, name=f"Rep-{i:02d}", region=region, capacity=capacity))

    # --- Territories ------------------------------------------------------
    territories: List[Territory] = []
    n_priority = int(round(n_territories * priority_fraction))
    priority_ids = set(rng.choice(n_territories, size=n_priority, replace=False).tolist())

    for j in range(n_territories):
        region = regions[j % n_regions]
        # Potential is lognormal: a few very high-value territories, many small.
        potential = float(np.round(rng.lognormal(mean=4.2, sigma=0.6)))
        required = float(np.round(rng.normal(avg_capacity * 0.6, avg_capacity * 0.15)))
        required = max(required, avg_capacity * 0.2)
        territories.append(
            Territory(
                id=j,
                name=f"T-{j:02d}",
                region=region,
                potential=potential,
                required_calls=required,
                priority=j in priority_ids,
            )
        )

    return Scenario(reps=reps, territories=territories)


def scenario_to_records(scenario: Scenario) -> dict:
    """Flatten a scenario into JSON-serializable records (for the API / CSV)."""
    return {
        "reps": [rep.__dict__ for rep in scenario.reps],
        "territories": [t.__dict__ for t in scenario.territories],
    }


if __name__ == "__main__":
    import csv
    import os

    sc = generate_scenario()
    total_capacity = sum(r.capacity for r in sc.reps)
    total_required = sum(t.required_calls for t in sc.territories)
    print(f"Reps: {len(sc.reps)}  Territories: {len(sc.territories)}  Regions: {sc.regions}")
    print(f"Total rep capacity: {total_capacity:,.0f}  Total required calls: {total_required:,.0f}")
    print(f"Capacity / demand ratio: {total_capacity / total_required:.2f}")

    # Write a sample scenario CSV next to the data folder.
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "sample_scenario.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "id", "name", "region", "capacity", "potential", "required_calls", "priority"])
        for r in sc.reps:
            writer.writerow(["rep", r.id, r.name, r.region, r.capacity, "", "", ""])
        for t in sc.territories:
            writer.writerow(["territory", t.id, t.name, t.region, "", t.potential, t.required_calls, t.priority])
    print(f"Wrote {out_path}")
