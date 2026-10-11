// Weather at the time of a capture (Open-Meteo, saved with the capture in InfluxDB).
// Cloud layers matter most for sunsets: high/mid clouds catch the color, a low deck blocks it.

const pct = (v) => (v == null ? "–" : `${Math.round(v)}%`);

export default function Weather({ w, compact = false }) {
  if (!w) return null;
  const clouds = `${pct(w.cloud_cover_low)} / ${pct(w.cloud_cover_mid)} / ${pct(w.cloud_cover_high)}`;
  if (compact) {
    return (
      <div className="weather-line" title="Cloud cover low / mid / high, temperature">
        ☁ {clouds}
        {w.temperature_2m != null && <> · {Math.round(w.temperature_2m)}°F</>}
      </div>
    );
  }
  const rows = [
    ["Clouds low / mid / high", clouds],
    ["Total cloud", pct(w.cloud_cover_total)],
    ["Temperature", w.temperature_2m != null && `${Math.round(w.temperature_2m)}°F`],
    ["Humidity", pct(w.relative_humidity_2m)],
    ["Dew point", w.dew_point_2m != null && `${Math.round(w.dew_point_2m)}°F`],
    ["Chance of rain", pct(w.precipitation_probability)],
    ["Precipitation", w.precipitation != null && `${w.precipitation} mm`],
    ["Visibility", w.visibility != null && `${(w.visibility / 1000).toFixed(1)} km`],
  ].filter(([, v]) => v);
  return (
    <div className="weather-card">
      <div className="metric-label">Weather at the best shot</div>
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
