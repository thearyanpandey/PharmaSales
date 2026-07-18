# PharmaSales — Sales-Force & Territory Optimization

> Given rep capacity and territory potential, allocate sales reps across regions to **maximize coverage under constraints** (linear programming), then **stress-test** the plan with Monte Carlo simulation — delivered through a dashboard where a non-technical user runs what-if scenarios.

**Repo:** https://github.com/thearyanpandey/PharmaSales
**One-liner for interviews:** "A territory-alignment optimizer — the exact class of problem ZS solves for pharma clients. Linear programming for the allocation, Monte Carlo to prove it's robust to demand uncertainty."

---

## 1. Why this project (ZS mapping)

This is **ZS's signature work** — pharma commercial analytics, sales-force sizing, territory alignment. Building it signals you understand what the firm actually does.

| ZS JD requirement | PharmaSales feature |
|---|---|
| Apply decision analytics and optimization techniques | Linear-programming allocation model |
| Develop simulation models | Monte Carlo demand simulation |
| Support strategic decision-making | What-if dashboard for planners |
| Present findings to stakeholders | Interactive dashboard, non-technical friendly |
| Design analytical solutions with industry tools | Python optimization + web dashboard |

---

## 2. Resume bullets this must back up

1. "Linear-programming territory-alignment optimizer (Python, PuLP) allocating sales reps across regions to maximize coverage under capacity constraints, improving modeled efficiency by ~22%."
2. "Monte Carlo simulations across 1,000+ demand scenarios to stress-test allocation robustness and quantify downside risk."
3. "Interactive dashboard (React) enabling non-technical stakeholders to run real-time what-if scenarios."

> The "~22%" must come from a real before/after in your code (naive allocation vs optimized). See section 7.

---

## 3. The business problem (frame it like this)

A pharma company has **N sales reps** and **M territories**. Each territory has a **sales potential** (e.g., number of high-value physicians / market size) and requires a certain **call frequency**. Each rep has limited **capacity** (calls/visits per period) and a home region. Goal: **assign rep capacity to territories to maximize total covered potential**, without exceeding any rep's capacity or under-serving must-cover territories.

You don't need real pharma data — generate realistic synthetic data (or use a public sales dataset). Document that it's synthetic; that's normal and honest.

---

## 4. The optimization model (core of the project)

**Decision variables:** `x[i][j]` = capacity (fraction or units) rep *i* allocates to territory *j*.

**Objective:** maximize `Σ potential[j] * coverage[j]` where coverage is the fraction of territory *j*'s required calls that get met.

**Constraints:**
- Each rep's total allocation ≤ rep capacity.
- Each territory's allocation ≤ its required call volume (no wasted over-coverage).
- Optional: travel/adjacency — a rep can only serve territories within their region.
- Optional: minimum coverage floor for priority territories.

Implement with **PuLP** (`LpMaximize`), solve with the default CBC solver. This is genuinely simple to code — maybe 60–80 lines.

---

## 5. The Monte Carlo layer

Territory potential/demand is uncertain. For each of **1,000+ trials**:
1. Draw demand per territory from a distribution (e.g., normal/lognormal around the base estimate).
2. Evaluate your optimized allocation against that drawn demand → compute realized coverage.
3. Record the coverage.

Then report the **distribution**: mean coverage, 5th percentile (downside/worst-case), and probability of hitting a target service level. This is what "quantify downside risk" means — have the actual histogram ready to show.

---

## 6. Tech stack

| Layer | Tech |
|---|---|
| Optimization | Python + PuLP (CBC solver) |
| Data / simulation | pandas, numpy |
| API | FastAPI (expose `/optimize` and `/simulate`) |
| Frontend | React + Vite + Recharts (bar chart of allocation, histogram of simulation) |
| Data | Synthetic generator script (`generate_data.py`) |

Optional fast path: if 7 days gets tight, ship it as a **Streamlit** app instead of React+FastAPI — you already list Streamlit, and it collapses the UI + backend into one file. React looks more impressive; Streamlit is faster. Your call.

---

## 7. Producing the honest "~22%" number

1. Build a **naive baseline**: allocate rep capacity evenly / proportionally to territory size without optimization. Measure total covered potential.
2. Run the **LP optimizer**. Measure total covered potential.
3. `improvement = (optimized - baseline) / baseline`.

Whatever that number actually is (could be 15%, could be 30%), **update the resume to match your real result**. Don't hardcode 22% if your model says 18%. An interviewer may ask "how did you get 22%?" — you want the honest answer to be "naive vs optimized coverage on my dataset."

---

## 8. Suggested folder structure

```
PharmaSales/
├── backend/
│   ├── generate_data.py    # synthetic reps + territories
│   ├── optimizer.py        # PuLP model
│   ├── simulate.py         # Monte Carlo
│   └── main.py             # FastAPI endpoints
├── frontend/               # React + Vite  (or app.py if Streamlit)
│   └── src/
├── data/
│   └── sample_scenario.csv
└── README.md
```

---

## 9. 2.5-day build plan

**Day 1 — data + optimizer.** `generate_data.py` (reps, capacities, territories, potentials). `optimizer.py` with PuLP: variables, objective, constraints, solve, return allocation + total coverage. Print baseline vs optimized to get your real improvement %.

**Day 2 — simulation + API.** `simulate.py`: 1,000+ Monte Carlo trials, return distribution stats. Wrap both in FastAPI (`/optimize`, `/simulate`). Add adjustable params (rep count, capacity, uncertainty level).

**Day 2.5 — dashboard.** React (or Streamlit): sliders for capacity/uncertainty, bar chart of allocation, histogram of simulated coverage, headline metrics (mean coverage, worst-case, improvement vs baseline). README with a screenshot/GIF.

---

## 10. Interview talking points

- Why linear programming and not just a heuristic? (Guarantees an optimal allocation under the constraints; heuristics don't.)
- What's the objective, in business terms? (Cover the most high-value potential given limited rep time.)
- Why Monte Carlo on top? (A plan that's optimal for one demand estimate can be fragile; simulation shows how it holds up under uncertainty and surfaces downside risk.)
- How would this extend to real ZS-scale problems? (More constraints — travel time, product mix, physician tiers, multi-period — same modeling approach, bigger solver.)
- What's the limitation? (Quality depends on the potential estimates; garbage in, garbage out — so data quality matters as much as the model.)
