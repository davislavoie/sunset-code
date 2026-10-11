// Weather at the time of a capture (Open-Meteo, saved with the capture in InfluxDB).
// Cloud layers matter most for sunsets: high/mid clouds catch the color, a low deck blocks it.

const pct = (v) => (v == null ? "–" : `${Math.round(v)}%`);

export default function Weather({ w, compact = false }) {
  if (!w) return null;
  const temp = w.temperature_2m != null && `${Math.round(w.temperature_2m)}°F`;
  if (compact) {
    return (
      <>
        <CloudProfile w={w} mini />
        <LightPath w={w} />
        {temp && <div className="weather-line">{temp}</div>}
      </>
    );
  }
  const rows = [
    ["Total cloud", pct(w.cloud_cover_total)],
    ["Temperature", temp],
    ["Humidity", pct(w.relative_humidity_2m)],
    ["Dew point", w.dew_point_2m != null && `${Math.round(w.dew_point_2m)}°F`],
    ["Chance of rain", pct(w.precipitation_probability)],
    ["Precipitation", w.precipitation != null && `${w.precipitation} mm`],
    ["Visibility", w.visibility != null && `${(w.visibility / 1000).toFixed(1)} km`],
  ].filter(([, v]) => v);
  return (
    <div className="weather-card">
      <div className="metric-label">Clouds toward the sun at the best shot</div>
      <CloudProfile w={w} />
      <LightPath w={w} />
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

function LightPath({ w }) {
  const low = [50, 150, 300].map((km) => [km, w[`path${km}_cloud_cover_low`]]);
  if (low.every(([, v]) => v == null)) return null;
  const wall = low.find(([, v]) => v >= BLOCKING);
  const [text, tone] = wall
    ? [`Low cloud blocks the sun ${wall[0]} km out`, "blocked"]
    : low.every(([, v]) => v == null || v < 30)
      ? ["Clear path to the sun", "open"]
      : ["Patchy low cloud toward the sun", "patchy"];
  return <div className={`light-path ${tone}`}>{text}</div>;
}

// A side view of the sky from the camera out toward the sun: cloud cover in each layer
// overhead and 50 / 150 / 300 km along the sunset (sunrise) direction. Low cloud out
// toward the sun is what blocks the light; high and mid cloud overhead is what catches it.
const COLUMNS = [
  { prefix: "", label: "Overhead" },
  { prefix: "path50_", label: "50 km" },
  { prefix: "path150_", label: "150 km" },
  { prefix: "path300_", label: "300 km" },
];
const LAYERS = [
  { key: "high", label: "High", y: 22, color: "#f6a5b8" },
  { key: "mid", label: "Mid", y: 64, color: "#f7b267" },
  { key: "low", label: "Low", y: 106, color: "#9aa5b8" },
];
const W = 400, GROUND = 146, BAND = 32, LEFT = 40, COL = 74, SUN_X = 372;
// Cloud thickness and brightness both follow coverage, so each row reads like a bar graph.
const thick = (v) => 4 + (BAND - 6) * (v / 100);
const colX = (i) => LEFT + 6 + i * (COL + 4);

function CloudProfile({ w, mini = false }) {
  const value = (col, layer) => w[`${col.prefix}cloud_cover_${layer.key}`];
  // Light reaching the sky over the camera has to get past low cloud out toward the sun.
  const blocked = Math.max(0, ...COLUMNS.slice(1).map((c) => value(c, LAYERS[2]) ?? 0)) / 100;
  const title = LAYERS.map((l) => `${l.label}: ${COLUMNS.map((c) => pct(value(c, l))).join(" / ")}`).join("\n");

  return (
    <svg
      className={`cloud-profile${mini ? " mini" : ""}`}
      viewBox={`0 0 ${W} ${mini ? GROUND + 4 : GROUND + 22}`}
      role="img"
      aria-label={`Cloud cover overhead and 50, 150, 300 km toward the sun. ${title}`}
    >
      {mini && <title>{`Cloud cover, overhead / 50 / 150 / 300 km toward the sun\n${title}`}</title>}
      <defs>
        <linearGradient id="cp-sky" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#141a33" />
          <stop offset="0.65" stopColor="#3b2a4a" />
          <stop offset="1" stopColor="#c8643a" />
        </linearGradient>
        <radialGradient id="cp-sun">
          <stop offset="0" stopColor="#ffe8a3" />
          <stop offset="0.35" stopColor="#ffb347" stopOpacity="0.9" />
          <stop offset="1" stopColor="#ff7a3d" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="cp-ray" x1="1" x2="0">
          <stop offset="0" stopColor="#ffcf70" />
          <stop offset="1" stopColor="#ffcf70" stopOpacity="0.15" />
        </linearGradient>
        <clipPath id="cp-clip">
          <rect width={W} height={GROUND} rx="8" />
        </clipPath>
        <filter id="cp-soft" x="-10%" y="-30%" width="120%" height="160%">
          <feGaussianBlur stdDeviation={mini ? 1.5 : 2.5} />
        </filter>
      </defs>

      <g clipPath="url(#cp-clip)">
        <rect width={W} height={GROUND} fill="url(#cp-sky)" />
        <circle cx={SUN_X + 10} cy={GROUND} r="58" fill="url(#cp-sun)" />
        <circle cx={SUN_X + 10} cy={GROUND} r="11" fill="#ffd57a" />
      </g>
      {/* Sunlight skimming the horizon up to the clouds over the camera, dimmed by low cloud on the way. */}
      <line
        x1={SUN_X} y1={GROUND - 6} x2={colX(0) + COL / 2} y2={LAYERS[0].y + BAND}
        stroke="url(#cp-ray)" strokeWidth={mini ? 3 : 2} strokeDasharray={mini ? undefined : "6 5"}
        opacity={1 - 0.85 * blocked}
      />

      {LAYERS.map((layer) =>
        COLUMNS.map((col, i) => {
          const v = value(col, layer);
          const x = colX(i);
          return (
            <g key={layer.key + i} className="cp-cell" style={{ animationDelay: `${(3 - i) * 70}ms` }}>
              {!mini && <title>{`${layer.label} cloud, ${i ? `${col.label} toward the sun` : "overhead"}: ${pct(v)}`}</title>}
              <rect x={x} y={layer.y} width={COL} height={BAND} rx="6"
                fill="none" stroke="rgba(255,255,255,0.12)" strokeDasharray={v == null ? "3 3" : undefined} />
              {v != null && (
                <rect x={x + 3} y={layer.y + BAND / 2 - thick(v) / 2} width={COL - 6} height={thick(v)} rx={thick(v) / 2}
                  fill={layer.color} opacity={0.25 + 0.7 * (v / 100)} filter="url(#cp-soft)" />
              )}
              {!mini && (
                <text x={x + COL / 2} y={layer.y + BAND / 2 + 4} textAnchor="middle" className="cp-value">
                  {pct(v)}
                </text>
              )}
            </g>
          );
        }),
      )}

      {!mini && (
        <>
          {LAYERS.map((l) => (
            <text key={l.key} x={LEFT - 4} y={l.y + BAND / 2 + 4} textAnchor="end" className="cp-axis">
              {l.label}
            </text>
          ))}
          {COLUMNS.map((c, i) => (
            <text key={c.label} x={colX(i) + COL / 2} y={GROUND + 15} textAnchor="middle" className="cp-axis">
              {c.label}
            </text>
          ))}
          <text x={SUN_X + 10} y={GROUND + 15} textAnchor="middle" className="cp-axis cp-sun-label">sun</text>
        </>
      )}
    </svg>
  );
}
