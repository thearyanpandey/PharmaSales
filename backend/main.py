"""FastAPI service exposing the optimizer and Monte Carlo simulation.

Endpoints
---------
GET  /health            liveness check
POST /optimize          run baseline vs LP optimization on a scenario
POST /simulate          run Monte Carlo stress-test on the optimized plan
POST /scenario          run optimization + simulation in one call (dashboard)

The scenario is regenerated deterministically from the request parameters
(with a seed) on every call, so the dashboard can drive real-time what-if
analysis just by changing sliders.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from generate_data import generate_scenario
from optimizer import optimize, naive_baseline, AllocationResult
from simulate import simulate

app = FastAPI(title="PharmaSales Territory Optimizer", version="1.0.0")

# Allow the Vite dev server (and any local origin) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Request / response models
# --------------------------------------------------------------------------- #
class ScenarioParams(BaseModel):
    n_reps: int = Field(20, ge=1, le=200)
    n_territories: int = Field(40, ge=1, le=400)
    n_regions: int = Field(5, ge=1, le=5)
    avg_capacity: float = Field(100.0, gt=0)
    priority_fraction: float = Field(0.25, ge=0, le=1)
    priority_floor: float = Field(0.5, ge=0, le=1)
    seed: int = 42


class SimulationParams(BaseModel):
    n_trials: int = Field(1000, ge=100, le=20000)
    uncertainty: float = Field(0.25, ge=0.0, le=1.0)
    target: float = Field(0.85, ge=0.0, le=1.0)
    sim_seed: int = 7


class ScenarioRequest(ScenarioParams, SimulationParams):
    """Combined params for the one-shot /scenario endpoint."""


def _territory_rows(scenario, allocation: AllocationResult) -> List[dict]:
    """Flatten per-territory results for charts/tables in the UI."""
    rows = []
    for t in scenario.territories:
        rows.append({
            "id": t.id,
            "name": t.name,
            "region": t.region,
            "potential": t.potential,
            "required_calls": t.required_calls,
            "priority": t.priority,
            "allocated": allocation.allocated.get(t.id, 0.0),
            "coverage": allocation.coverage.get(t.id, 0.0),
        })
    return rows


def _region_summary(scenario, allocation: AllocationResult) -> List[dict]:
    """Aggregate coverage by region for a compact bar chart."""
    agg = {}
    for t in scenario.territories:
        r = agg.setdefault(t.region, {"region": t.region, "potential": 0.0, "covered": 0.0})
        r["potential"] += t.potential
        r["covered"] += t.potential * allocation.coverage.get(t.id, 0.0)
    out = []
    for r in agg.values():
        r["coverage_ratio"] = round(r["covered"] / r["potential"], 4) if r["potential"] else 0.0
        r["potential"] = round(r["potential"], 2)
        r["covered"] = round(r["covered"], 2)
        out.append(r)
    return sorted(out, key=lambda x: x["region"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize")
def optimize_endpoint(params: ScenarioParams):
    scenario = generate_scenario(
        n_reps=params.n_reps,
        n_territories=params.n_territories,
        n_regions=params.n_regions,
        avg_capacity=params.avg_capacity,
        priority_fraction=params.priority_fraction,
        seed=params.seed,
    )
    base = naive_baseline(scenario)
    opt = optimize(scenario, priority_floor=params.priority_floor)
    improvement = (
        (opt.covered_potential - base.covered_potential) / base.covered_potential
        if base.covered_potential else 0.0
    )
    return {
        "baseline": base.as_dict(),
        "optimized": opt.as_dict(),
        "improvement": round(improvement, 4),
        "territories": _territory_rows(scenario, opt),
        "regions": _region_summary(scenario, opt),
    }


@app.post("/simulate")
def simulate_endpoint(req: ScenarioRequest):
    scenario = generate_scenario(
        n_reps=req.n_reps,
        n_territories=req.n_territories,
        n_regions=req.n_regions,
        avg_capacity=req.avg_capacity,
        priority_fraction=req.priority_fraction,
        seed=req.seed,
    )
    opt = optimize(scenario, priority_floor=req.priority_floor)
    sim = simulate(
        scenario, opt,
        n_trials=req.n_trials,
        uncertainty=req.uncertainty,
        target=req.target,
        seed=req.sim_seed,
    )
    return sim.as_dict()


@app.post("/scenario")
def scenario_endpoint(req: ScenarioRequest):
    """One-shot: optimize + simulate. This is what the dashboard calls."""
    scenario = generate_scenario(
        n_reps=req.n_reps,
        n_territories=req.n_territories,
        n_regions=req.n_regions,
        avg_capacity=req.avg_capacity,
        priority_fraction=req.priority_fraction,
        seed=req.seed,
    )
    base = naive_baseline(scenario)
    opt = optimize(scenario, priority_floor=req.priority_floor)
    improvement = (
        (opt.covered_potential - base.covered_potential) / base.covered_potential
        if base.covered_potential else 0.0
    )
    sim = simulate(
        scenario, opt,
        n_trials=req.n_trials,
        uncertainty=req.uncertainty,
        target=req.target,
        seed=req.sim_seed,
    )
    return {
        "meta": {
            "n_reps": req.n_reps,
            "n_territories": req.n_territories,
            "total_capacity": round(sum(r.capacity for r in scenario.reps), 1),
            "total_required": round(sum(t.required_calls for t in scenario.territories), 1),
        },
        "baseline": base.as_dict(),
        "optimized": opt.as_dict(),
        "improvement": round(improvement, 4),
        "territories": _territory_rows(scenario, opt),
        "regions": _region_summary(scenario, opt),
        "simulation": sim.as_dict(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
