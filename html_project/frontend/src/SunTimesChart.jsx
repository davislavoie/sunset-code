// Yearly sunrise / sunset / golden-hour times for one camera, drawn with bklit
// (shadcn registry, source in src/components/charts). The marker follows the
// map's date slider.

import { useMemo } from "react";
import { Sun } from "lucide-react";
import SunCalc from "suncalc";
import { Grid } from "@/components/charts/grid";
import { Line, LineChart } from "@/components/charts/line-chart";
import { ChartMarkers } from "@/components/charts/markers";
import { ChartTooltip } from "@/components/charts/tooltip";
import { XAxis } from "@/components/charts/x-axis";
import { YAxis } from "@/components/charts/y-axis";
import { GRID_STYLE, INSTANT_TOOLTIP, monthTicks } from "./chartTheme.js";

const SERIES = [
  { key: "sunrise", label: "Sunrise", color: "var(--chart-1)" },
  { key: "sunset", label: "Sunset", color: "var(--chart-2)" },
  { key: "golden", label: "Golden hour", color: "var(--chart-3)" },
];

const toDecimalHour = (dt) => (dt && !isNaN(dt) ? dt.getHours() + dt.getMinutes() / 60 : null);

/** 18.5 -> "6:30 PM" */
function formatHour(value) {
  if (value == null) return "—";
  const h = Math.floor(value);
  const m = Math.round((value - h) * 60);
  const date = new Date(2000, 0, 1, h, m);
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// Full day on the y-axis with a gridline every 4 hours, as the Plotly chart had.
const HOUR_TICKS = [0, 4, 8, 12, 16, 20, 24];
const formatTick = (hour) => ["12am", "4am", "8am", "12pm", "4pm", "8pm", "12am"][hour / 4] ?? `${hour}`;

export default function SunTimesChart({ config, date }) {
  const data = useMemo(() => {
    if (!config) return [];
    const lat = parseFloat(config.LAT);
    const lon = parseFloat(config.LON);
    const year = new Date().getFullYear();
    return Array.from({ length: 365 }, (_, i) => {
      const day = new Date(year, 0, i + 1);
      const times = SunCalc.getTimes(day, lat, lon);
      return {
        date: day,
        sunrise: toDecimalHour(times.sunrise),
        sunset: toDecimalHour(times.sunset),
        golden: toDecimalHour(times.goldenHour),
      };
    });
  }, [config]);

  const markers = useMemo(
    () => [
      {
        date,
        icon: <Sun size={14} />,
        title: date.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        color: "var(--chart-2)",
      },
    ],
    [date],
  );

  const xTicks = useMemo(() => (data.length ? monthTicks(data[0].date, data.at(-1).date) : {}), [data]);

  if (!config) return <div id="sun-times-chart" />;

  return (
    <div id="sun-times-chart">
      <LineChart data={data} aspectRatio="" className="h-full" margin={{ left: 48, right: 16 }} yDomain={[0, 24]}>
        <Grid {...GRID_STYLE} horizontal rowTickValues={HOUR_TICKS} vertical numTicksColumns={12} />
        {SERIES.map((s) => (
          <Line
            key={s.key}
            dataKey={s.key}
            stroke={s.color}
            strokeWidth={s.key === "golden" ? 1.5 : 2.5}
            // Golden hour stays dashed, as in the old Plotly chart.
            {...(s.key === "golden" && { dashFromIndex: 0, dashArray: "4,4" })}
          />
        ))}
        <YAxis formatValue={formatTick} tickValues={HOUR_TICKS} />
        <XAxis {...xTicks} />
        <ChartMarkers items={markers} />
        <ChartTooltip
          {...INSTANT_TOOLTIP}
          rows={(point) =>
            SERIES.map((s) => ({ color: s.color, label: s.label, value: formatHour(point[s.key]) }))
          }
        />
      </LineChart>
      <div className="sun-chart-legend">
        {SERIES.map((s) => (
          <span key={s.key}>
            <i style={{ background: s.color }} /> {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}
