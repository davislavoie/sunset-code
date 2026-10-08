// Shared bklit settings so the app's charts feel the same.

// Crosshair/dots track the cursor almost instantly (bklit's default spring lags behind).
export const SNAPPY_SPRING = { stiffness: 1500, damping: 90 };

/** Props for <ChartTooltip>: snappy crosshair, and the panel follows with no spring (damping 0). */
export const INSTANT_TOOLTIP = { springConfig: SNAPPY_SPRING, damping: 0 };

// Solid, clearly visible gridlines like the old Plotly charts (bklit's default is a faint fading dash).
export const GRID_STYLE = {
  stroke: "rgba(255, 255, 255, 0.1)",
  strokeDasharray: "0",
  fadeHorizontal: false,
};

const monthFmt = new Intl.DateTimeFormat(undefined, { month: "short" });
const monthYearFmt = new Intl.DateTimeFormat(undefined, { month: "short", year: "2-digit" });

/**
 * The 1st of each month between two dates, for x-axis ticks. Spans over a year
 * label the year too, and thin out to every other month so labels don't collide.
 */
export function monthTicks(start, end) {
  const ticks = [];
  for (let d = new Date(start.getFullYear(), start.getMonth() + (start.getDate() > 1 ? 1 : 0), 1); d <= end; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) {
    ticks.push(d);
  }
  const multiYear = start.getFullYear() !== end.getFullYear();
  return {
    tickDates: ticks.length > 14 ? ticks.filter((_, i) => i % 2 === 0) : ticks,
    formatTick: (date) => (multiYear ? monthYearFmt : monthFmt).format(date),
  };
}
