// Weather at the time of a capture, saved with it in InfluxDB: observed cloud toward the sun from
// the GOES-East satellite (ai_judge/goes.py), and Open-Meteo for the rest (temperature, humidity...).

import { ParentSize } from "@visx/responsive";

const pct = (v) => (v == null ? "–" : `${Math.round(v)}%`);

export default function Weather({ w, fill = false }) {
  if (!w) return null;
  return (
    <div className="weather-card">
      <div className="metric-label">Clouds toward the sun <span className="cp-source">· {cloudSource(w)}</span></div>
      <CloudProfile w={w} fill={fill} />
      <WeatherStats w={w} />
    </div>
  );
}

/** Temperature, humidity, rain and visibility at capture time. */
export function WeatherStats({ w }) {
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
    <dl className="weather-stats">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

// Low cloud of 70%+ along the path went with much weaker sunsets in the history (median best
// score 7 vs 31 with a clear path, from the earlier 50-300 km readings), so that's where we call
// the light blocked. ponytail: re-check against the 8-50 mi readings once they're backfilled.
const BLOCKING = 70;

// A side view of the sky from the camera out toward the sun: cloud cover in each layer
// overhead and 8 / 25 / 50 miles along the sunset (sunrise) direction, one bar per cell.
// Low cloud out toward the sun is what blocks the light, so only that gets colour.
const COLUMNS = [
  { prefix: "", label: "Overhead" },
  { prefix: "path13_", label: "8 mi" },
  { prefix: "path40_", label: "25 mi" },
  { prefix: "path80_", label: "50 mi" },
];
const LAYERS = [
  { key: "high", label: "High" },
  { key: "mid", label: "Mid" },
  { key: "low", label: "Low" },
];
const W = 336, GROUND = 116, LEFT = 40, COL = 62, GAP = 4, SUN_X = 322;
const colX = (i) => LEFT + i * (COL + GAP);

/** Clouds toward the sun at its natural height, or (fill) stretched to its box's height. What the
 * satellite saw when the capture has a reading; otherwise Open-Meteo's forecast by layer. */
export function CloudProfile({ w, fill = false }) {
  const Svg = w?.goes_fan != null ? SatelliteSvg : CloudProfileSvg;
  if (!fill) return <Svg w={w} ground={GROUND} />;
  return (
    <div className="cloud-profile-fill">
      <ParentSize>
        {({ width, height }) => width > 0 && height > 0 && (
          // Same width scale as normal, so text keeps its size; only the rows get taller.
          <Svg w={w} ground={Math.max(GROUND, (W * height) / width - 26)} />
        )}
      </ParentSize>
    </div>
  );
}

// The satellite sees cloud or no cloud, not layers: one tall bar per zone, from the camera out
// toward the sun. A far zone mostly cloudy is the bank that blocks the light, so it gets colour.
// Under each, how high the cloud tops are (GOES cloud-top height; the top layer only).
const ZONES = [
  { key: "goes_over", top: "goes_top_over", label: "Overhead" },
  { key: "goes_near", top: "goes_top_near", label: "3–25 mi" },
  { key: "goes_far", top: "goes_top_far", label: "50–190 mi" },
];
const KM_TO_KFT = 3.28084;
/** "Tops 31k ft" from a cloud-top height in km. */
const tops = (km) => `Tops ${Math.round(km * KM_TO_KFT)}k ft`;
const ZONE_COL = (SUN_X - 16 - LEFT - GAP * (ZONES.length - 1)) / ZONES.length;

function SatelliteSvg({ w, ground }) {
  const top = 8, cellH = ground - top - 8;
  const x = (i) => LEFT + i * (ZONE_COL + GAP);
  const summary = ZONES.map((z) => `${z.label} ${pct(w[z.key] != null ? 100 * w[z.key] : null)}${w[z.top] != null ? ` (${tops(w[z.top])})` : ""}`).join(", ");
  return (
    <svg
      className="cloud-profile"
      viewBox={`0 0 ${W} ${ground + 26}`}
      role="img"
      aria-label={`Cloud seen by the GOES-East satellite toward the sun: ${summary}`}
    >
      <line className="cp-horizon" x1={LEFT} x2={W} y1={ground} y2={ground} />
      <circle className="cp-sun" cx={SUN_X} cy={ground} r="7" />
      {ZONES.map((z, i) => {
        const v = w[z.key] != null ? 100 * w[z.key] : null;
        const blocks = z.key === "goes_far" && v >= BLOCKING;
        const h = v == null ? 0 : Math.max(4, (cellH * v) / 100);
        return (
          <g key={z.key} className="cp-cell">
            <rect className="cp-cell-frame" x={x(i)} y={top} width={ZONE_COL} height={cellH} rx="6" />
            {v != null && (
              <rect className={`cp-fill${blocks ? " blocks" : ""}`} x={x(i)} y={top + cellH - h} rx="6"
                width={ZONE_COL} height={h} opacity={blocks ? 0.25 : 0.18} />
            )}
            <text className="cp-value cp-big" x={x(i) + ZONE_COL / 2} y={top + cellH / 2 + 6} textAnchor="middle"
              style={blocks ? { fill: "var(--destructive)" } : undefined}>
              {pct(v)}
            </text>
            {w[z.top] != null && v > 0 && (
              <text className="cp-axis" x={x(i) + ZONE_COL / 2} y={top + cellH / 2 + 22} textAnchor="middle">
                {tops(w[z.top])}
              </text>
            )}
            <text x={x(i) + ZONE_COL / 2} y={ground + 18} textAnchor="middle" className="cp-axis">{z.label}</text>
          </g>
        );
      })}
      <text x={LEFT - 8} y={top + cellH / 2 + 4} textAnchor="end" className="cp-axis">Cloud</text>
      <text x={SUN_X} y={ground + 18} textAnchor="middle" className="cp-axis cp-sun">Sun</text>
    </svg>
  );
}

/** "Satellite" or "Forecast": where the cloud panel's numbers come from. */
export function cloudSource(w) {
  return w?.goes_fan != null ? "Satellite" : "Forecast";
}

function CloudProfileSvg({ w, ground }) {
  const step = (ground - 8) / LAYERS.length; // row pitch; 36 at the natural height
  const cellH = step - 8;
  const rowY = (i) => 8 + i * step;
  const value = (col, layer) => w[`${col.prefix}cloud_cover_${layer.key}`];
  const summary = LAYERS.map((l) => `${l.label}: ${COLUMNS.map((c) => pct(value(c, l))).join(" / ")}`).join(". ");

  return (
    <svg
      className="cloud-profile"
      viewBox={`0 0 ${W} ${ground + 26}`}
      role="img"
      aria-label={`Cloud cover overhead and 8, 25, 50 miles toward the sun. ${summary}`}
    >
      <line className="cp-horizon" x1={LEFT} x2={W} y1={ground} y2={ground} />
      <circle className="cp-sun" cx={SUN_X} cy={ground} r="7" />

      {LAYERS.map((layer, li) =>
        COLUMNS.map((col, i) => {
          const v = value(col, layer);
          const blocks = i > 0 && layer.key === "low" && v >= BLOCKING;
          return (
            <g key={layer.key + i} className="cp-cell">
              <rect className="cp-cell-frame" x={colX(i)} y={rowY(li)} width={COL} height={cellH} rx="6" />
              {v != null && (
                <rect className={`cp-fill${blocks ? " blocks" : ""}`} x={colX(i)} y={rowY(li)} rx="6"
                  width={Math.max(4, (COL * v) / 100)} height={cellH} opacity={blocks ? 0.25 : 0.18} />
              )}
              <text className="cp-value" x={colX(i) + 8} y={rowY(li) + cellH / 2 + 4.5}
                style={blocks ? { fill: "var(--destructive)" } : undefined}>
                {pct(v)}
              </text>
            </g>
          );
        }),
      )}

      {LAYERS.map((l, li) => (
        <text key={l.key} x={LEFT - 8} y={rowY(li) + cellH / 2 + 4} textAnchor="end" className="cp-axis">
          {l.label}
        </text>
      ))}
      {COLUMNS.map((c, i) => (
        <text key={c.label} x={colX(i) + COL / 2} y={ground + 18} textAnchor="middle" className="cp-axis">
          {c.label}
        </text>
      ))}
      <text x={SUN_X} y={ground + 18} textAnchor="middle" className="cp-axis cp-sun">
        Sun
      </text>
    </svg>
  );
}
