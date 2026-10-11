// Weather at the time of a capture (Open-Meteo, saved with the capture in InfluxDB).
// Cloud layers matter most for sunsets: high/mid clouds catch the color, a low deck blocks it.

const pct = (v) => (v == null ? "–" : `${Math.round(v)}%`);

export default function Weather({ w }) {
  if (!w) return null;
  const temp = w.temperature_2m != null && `${Math.round(w.temperature_2m)}°F`;
  const rows = [
    ["Temperature", temp],
    ["Humidity", pct(w.relative_humidity_2m)],
    ["Dew point", w.dew_point_2m != null && `${Math.round(w.dew_point_2m)}°F`],
    ["Chance of rain", pct(w.precipitation_probability)],
    ["Precipitation", w.precipitation != null && `${w.precipitation} mm`],
    ["Visibility", w.visibility != null && `${(w.visibility / 1000).toFixed(1)} km`],
  ].filter(([, v]) => v);
  return (
    <div className="weather-card">
      <div className="metric-label">Clouds toward the sun</div>
      <CloudProfile w={w} />
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// Low cloud of 70%+ along the path went with much weaker sunsets in the history (median best
// score 7 vs 31 with a clear path), so that's where we call the light blocked.
const BLOCKING = 70;

// A side view of the sky from the camera out toward the sun: cloud cover in each layer
// overhead and 50 / 150 / 300 km along the sunset (sunrise) direction, one bar per cell.
// Low cloud out toward the sun is what blocks the light, so only that gets colour.
const COLUMNS = [
  { prefix: "", label: "Overhead" },
  { prefix: "path50_", label: "50 km" },
  { prefix: "path150_", label: "150 km" },
  { prefix: "path300_", label: "300 km" },
];
const LAYERS = [
  { key: "high", label: "High", y: 8 },
  { key: "mid", label: "Mid", y: 44 },
  { key: "low", label: "Low", y: 80 },
];
const W = 336, CELL_H = 28, GROUND = 116, LEFT = 40, COL = 62, GAP = 4, SUN_X = 322;
const colX = (i) => LEFT + i * (COL + GAP);

function CloudProfile({ w }) {
  const value = (col, layer) => w[`${col.prefix}cloud_cover_${layer.key}`];
  const summary = LAYERS.map((l) => `${l.label}: ${COLUMNS.map((c) => pct(value(c, l))).join(" / ")}`).join(". ");

  return (
    <svg
      className="cloud-profile"
      viewBox={`0 0 ${W} ${GROUND + 26}`}
      role="img"
      aria-label={`Cloud cover overhead and 50, 150, 300 km toward the sun. ${summary}`}
    >
      <line className="cp-horizon" x1={LEFT} x2={W} y1={GROUND} y2={GROUND} />
      <circle className="cp-sun" cx={SUN_X} cy={GROUND} r="7" />

      {LAYERS.map((layer) =>
        COLUMNS.map((col, i) => {
          const v = value(col, layer);
          const blocks = i > 0 && layer.key === "low" && v >= BLOCKING;
          return (
            <g key={layer.key + i} className="cp-cell">
              <rect className="cp-cell-frame" x={colX(i)} y={layer.y} width={COL} height={CELL_H} rx="6" />
              {v != null && (
                <rect className={`cp-fill${blocks ? " blocks" : ""}`} x={colX(i)} y={layer.y} rx="6"
                  width={Math.max(4, (COL * v) / 100)} height={CELL_H} opacity={blocks ? 0.25 : 0.18} />
              )}
              <text className="cp-value" x={colX(i) + 8} y={layer.y + CELL_H / 2 + 4.5}
                style={blocks ? { fill: "var(--destructive)" } : undefined}>
                {pct(v)}
              </text>
            </g>
          );
        }),
      )}

      {LAYERS.map((l) => (
        <text key={l.key} x={LEFT - 8} y={l.y + CELL_H / 2 + 4} textAnchor="end" className="cp-axis">
          {l.label}
        </text>
      ))}
      {COLUMNS.map((c, i) => (
        <text key={c.label} x={colX(i) + COL / 2} y={GROUND + 18} textAnchor="middle" className="cp-axis">
          {c.label}
        </text>
      ))}
      <text x={SUN_X} y={GROUND + 18} textAnchor="middle" className="cp-axis">
        Sun
      </text>
    </svg>
  );
}
