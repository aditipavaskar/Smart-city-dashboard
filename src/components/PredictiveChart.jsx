import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const TREND_COLOR = {
  worsening: "#ef5959",
  improving: "#5fd68e",
  stable: "#3fd0c9",
};

export default function PredictiveChart({ result, unit }) {
  if (!result) {
    return <div className="text-sm text-slate-400 p-4">Not enough history yet for a forecast.</div>;
  }

  const { history, forecast, trend, confidence_band: band } = result;
  const data = [
    ...history.map((v, i) => ({ idx: i, actual: v })),
    ...forecast.map((v, i) => ({
      idx: history.length + i,
      forecast: v,
      upper: v + band,
      lower: Math.max(0, v - band),
    })),
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-2 text-sm">
        <span className="text-slate-400">Forecast trend:</span>
        <span className="font-semibold" style={{ color: TREND_COLOR[trend] || "#fff" }}>
          {trend}
        </span>
        <span className="text-slate-500">± {band} {unit} (95%)</span>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#223252" />
          <XAxis dataKey="idx" tick={{ fontSize: 10, fill: "#7d8aa8" }} />
          <YAxis tick={{ fontSize: 10, fill: "#7d8aa8" }} unit={unit} />
          <Tooltip
            contentStyle={{ background: "#101a2c", border: "1px solid #223252", fontSize: 12 }}
            labelFormatter={(v) => `t = ${v}`}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <ReferenceLine x={history.length - 1} stroke="#7d8aa8" strokeDasharray="4 4" label="now" />
          <Line type="monotone" dataKey="actual" stroke="#3fd0c9" dot={false} strokeWidth={2} name="observed" />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke={TREND_COLOR[trend] || "#fff"}
            strokeDasharray="5 3"
            dot={false}
            strokeWidth={2}
            name="forecast"
          />
          <Line type="monotone" dataKey="upper" stroke="#7d8aa8" dot={false} strokeWidth={1} name="upper band" />
          <Line type="monotone" dataKey="lower" stroke="#7d8aa8" dot={false} strokeWidth={1} name="lower band" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
