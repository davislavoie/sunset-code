// Sunset forecast helpers (ai_judge/predict.py writes the forecast on each pre shot).
// A day's actual result is its best score from 15 min before to 30 min after sunset, as a
// percentile of the earlier days' bests: the same scale the forecast predicts.

const WINDOW = /^(05|06|07|08|09|10)_/;
const MIN_DAYS = 10;
// Same cut points as ai_judge/predict.py (percentile 0-100).
export const CALLS = [
  [80, "banger"],
  [60, "good"],
  [35, "maybe"],
  [0, "poor"],
];
export const callFor = (pct) => CALLS.find(([cut]) => pct >= cut)[1];
export const CALL_TONE = { banger: "success", good: "success", maybe: "warning", poor: "destructive" };

const baseLabel = (label) => (label ?? "").split("/").pop();

/** {date: best in-window score} from all_data rows (Score is already 0 for shots that don't count). */
export function dailyBests(allData) {
  const best = {};
  for (const r of allData) {
    if (!WINDOW.test(baseLabel(r.Label))) continue;
    best[r.Date] = Math.max(best[r.Date] ?? 0, r.Score ?? 0);
  }
  return best;
}

/** The day's actual percentile (0-100) among earlier days, or null without enough history. */
export function actualPct(bests, date) {
  if (bests[date] == null) return null;
  const earlier = Object.entries(bests).filter(([d]) => d < date).map(([, v]) => v);
  if (earlier.length < MIN_DAYS) return null;
  return (100 * earlier.filter((v) => v <= bests[date]).length) / earlier.length;
}

/** Hit = same call, Close = one call off, Miss = further. */
export function accuracy(predictedPct, actual) {
  if (predictedPct == null || actual == null) return null;
  const order = CALLS.map(([, c]) => c);
  const off = Math.abs(order.indexOf(callFor(predictedPct)) - order.indexOf(callFor(actual)));
  return { verdict: off === 0 ? "Hit" : off === 1 ? "Close" : "Miss", points: Math.round(Math.abs(predictedPct - actual)) };
}
export const VERDICT_TONE = { Hit: "success", Close: "warning", Miss: "destructive" };

const HORIZON = /^(0[1-6])_(\w+?)_pre/;
/** "02_1h_pre..." -> "02_1h_pre", or null for shots that carry no forecast. */
export const horizonOf = (label) => {
  const m = HORIZON.exec(baseLabel(label));
  return m ? `${m[1]}_${m[2]}_pre` : null;
};

/** Per horizon across all days: {horizon: {days, hit, close, miss}}. */
export function summary(allData) {
  const bests = dailyBests(allData);
  const out = {};
  for (const r of allData) {
    const h = horizonOf(r.Label);
    const acc = h && r.Forecast && accuracy(r.Forecast.pct, actualPct(bests, r.Date));
    if (!acc) continue;
    const s = (out[h] ??= { days: 0, Hit: 0, Close: 0, Miss: 0 });
    s.days += 1;
    s[acc.verdict] += 1;
  }
  return out;
}
