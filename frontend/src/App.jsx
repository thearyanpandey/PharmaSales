import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell, ReferenceLine, Legend,
} from "recharts";

const DEFAULTS = {
  n_reps: 20,
  n_territories: 40,
  avg_capacity: 100,
  priority_floor: 0.5,
  uncertainty: 0.25,
  n_trials: 1000,
  target: 0.85,
};

const pct = (x) => `${(x * 100).toFixed(1)}%`;

function Slider({ label, value, min, max, step, format, onChange }) {
  return (
    <div className="control">
      <label>
        <span>{label}</span>
        <span className="val">{format ? format(value) : value}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
}

function Metric({ label, value, sub, tone }) {
  return (
    <div className="metric">
      <div className="label">{label}</div>
      <div className={`value ${tone || ""}`}>{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export default function App() {
  const [params, setParams] = useState(DEFAULTS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const debounceRef = useRef(null);

  const setParam = (key) => (val) => setParams((p) => ({ ...p, [key]: val }));

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setLoading(true);
      setError(null);
      fetch("/api/scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      })
        .then((r) => {
          if (!r.ok) throw new Error(`API ${r.status}`);
          return r.json();
        })
        .then((d) => setData(d))
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(debounceRef.current);
  }, [params]);

  const regionData = useMemo(
    () =>
      data?.regions?.map((r) => ({
        region: r.region,
        coverage: +(r.coverage_ratio * 100).toFixed(1),
      })) || [],
    [data]
  );

  const histData = useMemo(() => {
    if (!data?.simulation?.histogram) return [];
    const { bins, counts } = data.simulation.histogram;
    return bins.map((b, i) => ({
      bin: +(b * 100).toFixed(0),
      count: counts[i],
    }));
  }, [data]);

  const sim = data?.simulation;

  return (
    <div className="app">
      <div className="header">
        <h1>PharmaSales — Territory Optimizer</h1>
        <p>
          Linear-programming rep allocation, stress-tested with Monte Carlo.
          Move the sliders to run a what-if scenario.
        </p>
      </div>

      <div className="layout">
        <div className="panel">
          <h2>Scenario</h2>
          <Slider label="Sales reps" value={params.n_reps} min={5} max={80} step={1}
            onChange={setParam("n_reps")} />
          <Slider label="Territories" value={params.n_territories} min={10} max={120} step={1}
            onChange={setParam("n_territories")} />
          <Slider label="Avg rep capacity" value={params.avg_capacity} min={40} max={200} step={5}
            onChange={setParam("avg_capacity")} />
          <Slider label="Priority coverage floor" value={params.priority_floor} min={0} max={1} step={0.05}
            format={pct} onChange={setParam("priority_floor")} />

          <h2 style={{ marginTop: 22 }}>Uncertainty</h2>
          <Slider label="Demand uncertainty" value={params.uncertainty} min={0} max={0.8} step={0.05}
            format={pct} onChange={setParam("uncertainty")} />
          <Slider label="Service-level target" value={params.target} min={0.5} max={1} step={0.05}
            format={pct} onChange={setParam("target")} />
          <Slider label="Monte Carlo trials" value={params.n_trials} min={200} max={5000} step={200}
            onChange={setParam("n_trials")} />

          {loading && <div className="loading">Solving…</div>}
          {error && <div className="error">Error: {error}. Is the backend running on :8000?</div>}
        </div>

        <div>
          <div className="metrics">
            <Metric
              label="Optimized coverage"
              tone="good"
              value={data ? pct(data.optimized.coverage_ratio) : "—"}
              sub="of total potential"
            />
            <Metric
              label="vs. naive baseline"
              tone="accent"
              value={data ? `+${pct(data.improvement)}` : "—"}
              sub={data ? `baseline ${pct(data.baseline.coverage_ratio)}` : ""}
            />
            <Metric
              label="Worst case (5th pct)"
              tone="warn"
              value={sim ? pct(sim.p5_coverage) : "—"}
              sub="downside risk"
            />
            <Metric
              label={`P(coverage ≥ ${data ? pct(params.target) : ""})`}
              value={sim ? pct(sim.prob_meets_target) : "—"}
              sub={sim ? `${sim.n_trials} trials` : ""}
            />
          </div>

          <div className="charts">
            <div className="chart-card">
              <h3>Coverage by region (optimized plan)</h3>
              <p className="desc">
                Share of each region's sales potential covered after LP allocation.
              </p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={regionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="region" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                    formatter={(v) => [`${v}%`, "Coverage"]}
                  />
                  <Bar dataKey="coverage" radius={[4, 4, 0, 0]}>
                    {regionData.map((d, i) => (
                      <Cell key={i} fill={d.coverage >= 90 ? "#34d399" : d.coverage >= 75 ? "#38bdf8" : "#fbbf24"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Monte Carlo — realized coverage distribution</h3>
              <p className="desc">
                {sim ? `${sim.n_trials} trials` : ""} of the fixed plan against uncertain demand.
                Dashed line = service-level target.
              </p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={histData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="bin" stroke="#94a3b8" fontSize={12}
                    tickFormatter={(v) => `${v}%`}
                    label={{ value: "realized coverage", position: "insideBottom", offset: -2, fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                    formatter={(v) => [v, "trials"]}
                    labelFormatter={(l) => `${l}% coverage`}
                  />
                  {sim && (
                    <ReferenceLine x={Math.round(params.target * 100)} stroke="#f87171"
                      strokeDasharray="4 4" />
                  )}
                  <Bar dataKey="count" fill="#a78bfa" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {data && (
            <div className="footnote">
              Scenario: {data.meta.n_reps} reps · {data.meta.n_territories} territories ·
              total capacity {data.meta.total_capacity.toLocaleString()} calls vs
              {" "}{data.meta.total_required.toLocaleString()} required.
              Synthetic data — reproducible from a fixed seed.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
