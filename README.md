# PharmaSales — Sales-Force & Territory Optimization

A territory-alignment optimizer for pharma commercial teams. Given rep capacity
and territory potential, it **allocates sales reps across regions to maximize
covered potential under constraints** (linear programming), then **stress-tests
the plan against demand uncertainty** with Monte Carlo simulation — all driven
from an interactive what-if dashboard.

> This is the signature class of problem in pharma sales-force analytics:
> sales-force sizing and territory alignment. LP for the allocation, Monte Carlo
> to prove the plan is robust.

## What it does

- **Linear-programming allocation** (PuLP + CBC): assigns each rep's call
  capacity to territories in their region to maximize `Σ potential × coverage`,
  subject to rep capacity, no-over-coverage, region adjacency, and a
  priority-territory coverage floor.
- **Naive baseline vs. optimized**: an honest before/after. On the default
  20-rep / 40-territory scenario the optimizer lifts covered potential from
  **82.5% → 92.0% of total — an ~11.6% improvement over the naive plan.**
  (The number is computed live, not hardcoded — it shifts with the scenario.)
- **Monte Carlo stress test**: 1,000+ trials draw uncertain demand from a
  lognormal distribution and re-evaluate the fixed plan, reporting mean
  coverage, 5th-percentile downside, and probability of hitting a service-level
  target.
- **Interactive dashboard** (React + Vite + Recharts): sliders for rep count,
  capacity, priority floor, demand uncertainty, and target; live coverage-by-
  region bar chart and a simulation histogram.

## Architecture

```
PharmaSales/
├── backend/
│   ├── generate_data.py    # synthetic reps + territories (reproducible seed)
│   ├── optimizer.py        # PuLP LP model + naive baseline + compare()
│   ├── simulate.py         # Monte Carlo demand stress-test
│   ├── main.py             # FastAPI: /optimize, /simulate, /scenario
│   └── requirements.txt
├── frontend/               # React + Vite + Recharts dashboard
│   └── src/{App.jsx, main.jsx, styles.css}
├── data/
│   └── sample_scenario.csv # generated sample scenario
└── README.md
```

### The optimization model

- **Decision variables** `x[i][j]` — call capacity rep *i* allocates to
  territory *j* (only created when rep and territory share a region).
- **Objective** — maximize `Σ_j (potential[j] / required[j]) · allocated[j]`,
  a linear form of `Σ_j potential[j] · coverage[j]`.
- **Constraints** — per-rep capacity; per-territory no-over-coverage (so
  coverage never exceeds 1); region adjacency; priority coverage floor. If the
  floor is infeasible for a region's capacity, the solver retries without it so
  the dashboard always returns a usable plan.

## Running it

### Backend (Python 3.10+)

```bash
cd backend
pip install -r requirements.txt

# Run the models directly (prints baseline vs optimized, and a simulation):
python generate_data.py
python optimizer.py
python simulate.py

# Or serve the API:
python -m uvicorn main:app --reload --port 8000
```

API: `POST /scenario` (optimize + simulate in one call — what the dashboard
uses), `POST /optimize`, `POST /simulate`, `GET /health`. Interactive docs at
`http://127.0.0.1:8000/docs`.

### Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → :8000)
```

Start the backend first, then the frontend. The Vite dev server proxies `/api/*`
to the FastAPI backend on port 8000.

## Notes

- **Data is synthetic** and generated from a fixed seed, so results are
  reproducible. That's normal and honest for a modeling demo — the value is in
  the optimization and simulation, not proprietary data.
- **The improvement % is measured, not assumed.** It's `(optimized − baseline) /
  baseline` on covered potential and changes with the scenario. Read it off your
  own run rather than quoting a fixed figure.

## Interview talking points

- **Why LP and not a heuristic?** LP guarantees the optimal allocation under the
  stated constraints; a greedy heuristic doesn't.
- **What's the objective, in business terms?** Cover the most high-value sales
  potential given limited rep call capacity.
- **Why Monte Carlo on top?** A plan that's optimal for one demand estimate can
  be fragile. Simulation shows how it holds up under uncertainty and quantifies
  downside risk (the 5th-percentile coverage).
- **How would this scale to real problems?** More constraints — travel time,
  product mix, physician tiers, multi-period — same modeling approach, bigger
  solver.
- **Limitation?** Quality depends on the potential estimates; garbage in,
  garbage out — so data quality matters as much as the model.
