// Sunset Calendar with Day / Week / Month / Year views. The Day tab is the "latest sunset" view:
// the day's best shot and score, then every capture. View, date and the expanded
// day live in the URL so any view can be shared: /calendar?view=month&date=2025-05-16

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { dayPath, thumb as small, useDocumentTitle } from "../api.js";
import DayDetail, { captureName } from "../DayDetail.jsx";
import { ForecastCard } from "../Forecast.jsx";
import { CALL_TONE, horizonOf } from "../forecast.js";
import Img, { SIZES, sizeForLabel } from "../Img.jsx";
import Reveal from "../Reveal.jsx";
import SunsetHero from "../SunsetHero.jsx";
import Thumbs, { exclusionFor, FlagPill, GlassPill } from "../Thumbs.jsx";
import Tip from "../Tip.jsx";
import { Zoomable } from "../lightbox.jsx";

const VIEWS = [["day", "Day"], ["week", "Week"], ["month", "Month"], ["year", "Year"]];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function toISODate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fromISODate(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function shiftDate(isoStr, { days = 0, months = 0, years = 0 }) {
  const d = fromISODate(isoStr);
  if (months || years) d.setDate(1); // avoid Jan 31 + 1 month landing in March
  d.setFullYear(d.getFullYear() + years, d.getMonth() + months, d.getDate() + days);
  return toISODate(d);
}

const isoFor = (year, month, day) =>
  `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

// Labels are formatted like "01_2h_pre_...", "07_sunset_..." or "07_sunrise_...", "11_ranked_...",
// "12_histogram_..." -- the leading number is the true capture order.
const labelOrder = (label) => parseInt(label.slice(0, 2), 10);
const byLabelOrder = (a, b) => labelOrder(a.Label) - labelOrder(b.Label);

export default function Calendar({ data, camera, onLoadToHsv, admin = false }) {
  // Shots that don't count (thumbs down, bad view) still show, scored 0% with a pill saying why.
  const { ranked_images: rankedImages, all_data: allData, sunset_data: sunsetData } = data;
  const [params, setParams] = useSearchParams();

  // One entry per captured day, keyed by "YYYY-MM-DD"
  const byDate = useMemo(() => new Map(sunsetData.map((item) => [item.Date, item])), [sunsetData]);
  const rankedByDate = useMemo(() => new Map(rankedImages.map((r) => [r.Date, r])), [rankedImages]);

  if (!sunsetData.length) {
    return (
      <>
        <h1>Sunset calendar</h1>
        <div className="empty">No data available.</div>
      </>
    );
  }

  // Opens on the latest finished sunset (one with a ranked best shot).
  const view = params.get("view") || "day";
  const date = params.get("date") || [...rankedByDate.keys()].sort().at(-1) || [...byDate.keys()].sort().at(-1);
  const expanded = params.get("open");

  const update = (changes) =>
    setParams((p) => {
      for (const [k, v] of Object.entries(changes)) v == null ? p.delete(k) : p.set(k, v);
      return p;
    });
  const goTo = (newDate) => update({ date: newDate, open: null, mark: null });

  const viewProps = { date, goTo, byDate, allData, onLoadToHsv, permalinkFor: dayPath };

  return (
    <>
      <h1>Sunset calendar</h1>

      <div className="view-tabs">
        <div className="view-tab-group">
          {VIEWS.map(([key, label]) => (
            <button
              key={key}
              className={`btn view-tab-btn${view === key ? " active" : ""}`}
              onClick={() => update({ view: key, open: null })}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="view-tab-group">
          {/* mark: the day the month view outlines, until you move to another month or day */}
          {view === "day" && (
            <button className="btn" onClick={() => update({ view: "month", date, mark: date })}>Show in month</button>
          )}
          <button className="btn today-btn" onClick={() => goTo(toISODate(new Date()))}>
            Today
          </button>
        </div>
      </div>

      {view === "day" && <DayView key={date} {...viewProps} camera={camera} admin={admin} best={rankedByDate.get(date)} />}
      {view === "week" && (
        <WeekView {...viewProps} rankedByDate={rankedByDate} expanded={expanded} setExpanded={(d) => update({ open: d })} />
      )}
      {view === "year" && <YearView {...viewProps} />}
      {view === "month" && (
        <MonthView
          {...viewProps}
          expanded={expanded}
          mark={params.get("mark")}
          setExpanded={(d) => update({ open: d, mark: null })}
        />
      )}
    </>
  );
}

function CalendarHeader({ title, onPrev, onNext, prevDisabled, nextDisabled, prevTitle, nextTitle }) {
  return (
    <div className="calendar-header">
      <Tip label={prevTitle}>
        <button className="btn cal-arrow" aria-label="Previous" disabled={prevDisabled} onClick={onPrev}>
          <ChevronLeft size={18} />
        </button>
      </Tip>
      <div className="calendar-title">{title}</div>
      <Tip label={nextTitle}>
        <button className="btn cal-arrow" aria-label="Next" disabled={nextDisabled} onClick={onNext}>
          <ChevronRight size={18} />
        </button>
      </Tip>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Day view -- the "latest sunset" page: the day's best shot, score and color
// breakdown, then every capture from that day. Arrows jump between captured days.
// ---------------------------------------------------------------------------
function DayView({ date, goTo, allData, camera, admin, best }) {
  const dayImages = allData.filter((img) => img.Date === date).sort(byLabelOrder);
  const capturedDays = useMemo(() => [...new Set(allData.map((img) => img.Date))].sort(), [allData]);
  const prev = capturedDays.filter((d) => d < date).at(-1);
  const next = capturedDays.find((d) => d > date);
  const title = fromISODate(date).toLocaleDateString(undefined, {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
  useDocumentTitle(`${camera} sunset · ${title}`);
  // Opens on the day's best shot; picking another (arrows, keys, or a capture below) swaps the hero.
  const heroRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const bestIndex = Math.max(0, dayImages.findIndex((img) => img.Image === best?.["Raw Image"]));
  const shown = selected != null && selected < dayImages.length ? selected : bestIndex;
  const event = dayImages.some((img) => /^\d+_sunrise/.test(img.Label)) ? "sunrise" : "sunset";

  return (
    <div>
      <CalendarHeader
        title={title}
        onPrev={() => goTo(prev)}
        onNext={() => goTo(next)}
        prevDisabled={!prev}
        nextDisabled={!next}
        prevTitle={prev && `Previous captured day: ${prev}`}
        nextTitle={next && `Next captured day: ${next}`}
      />
      {!dayImages.length ? (
        <div className="empty">No captures for this day.</div>
      ) : (
        <>
          <div ref={heroRef} className="detail-scroll-target">
            <SunsetHero shots={dayImages} index={shown} onSelect={setSelected} best={best} camera={camera} date={date} />
          </div>
          <ForecastCard date={date} dayImages={dayImages} allData={allData} event={event} />
          <div className="detail day-captures">
            <div className="detail-title">
              <h3>All captures</h3>
              <span>{`${dayImages.length} from ${title}`}</span>
            </div>
            <div className="day-view-grid">
            {dayImages.map((img, i) => (
              <CaptureCard
                key={img.Image}
                img={img}
                camera={camera}
                admin={admin}
                event={event}
                selected={i === shown}
                onSelect={() => {
                  setSelected(i);
                  heroRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              />
            ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export function CaptureCard({ img, camera, admin = false, event = "sunset", selected = false, onSelect }) {
  const [thumb, setThumb] = useState(img.Thumb ?? 0);
  const generated = /^(11_|12_)/.test(img.Label);
  const excluded = generated ? null : exclusionFor(img, thumb);
  return (
    <div className={`day-view-card${excluded ? " not-counted" : ""}${selected ? " selected" : ""}`}>
      {onSelect ? (
        <Img src={small(img.Image)} alt={img.Label} loading="lazy" onClick={onSelect} {...sizeForLabel(img.Label)} />
      ) : (
        <Zoomable src={small(img.Image, 960)} full={img.Image} alt={img.Label} loading="lazy" {...sizeForLabel(img.Label)} />
      )}
      <div className="day-view-caption">
        <strong>{captureName(img.Label, event)}</strong>
        <span>
          {img.Time} &middot; Score: {(excluded ? 0 : img["HSV Score"] ?? img.Score).toFixed(1)}%
          {img.Weather?.temperature_2m != null && <> &middot; {Math.round(img.Weather.temperature_2m)}°F</>}
        </span>
        <FlagPill reason={excluded} />
        <GlassPill glass={img.Glass} hsv={img["HSV Score"]} />
        {admin && !generated && <Thumbs camera={camera} img={img} onChange={(s) => setThumb(s.thumb)} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Week view -- one card per day, a cut-down Day view: the best shot, its score, the 1 hr
// forecast and the weather. A card opens that day's captures under the week (as in the month view).
// ---------------------------------------------------------------------------
function WeekView({ date, goTo, byDate, rankedByDate, allData, onLoadToHsv, permalinkFor, expanded, setExpanded }) {
  const focus = fromISODate(date);
  const weekStart = new Date(focus);
  weekStart.setDate(focus.getDate() - focus.getDay());
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 6);

  const today = toISODate(new Date());
  const forecasts = useMemo(
    () => new Map(allData.filter((r) => horizonOf(r.Label) === "02_1h_pre" && r.Forecast).map((r) => [r.Date, r.Forecast])),
    [allData],
  );
  const event = allData.some((img) => /^\d+_sunrise/.test(img.Label)) ? "sunrise" : "sunset";

  const days = WEEKDAYS.map((weekday, i) => {
    const dayDate = new Date(weekStart);
    dayDate.setDate(weekStart.getDate() + i);
    const iso = toISODate(dayDate);
    // The day's best shot; before one is picked (today, mid-capture), the sunset shot or the latest capture.
    const shot = rankedByDate.get(iso) ?? byDate.get(iso) ?? allData.filter((img) => img.Date === iso).sort(byLabelOrder).at(-1);
    return { iso, weekday, day: dayDate.getDate(), shot, image: shot?.["Raw Image"] ?? shot?.Image };
  });
  const open = days.find((d) => d.iso === expanded && d.shot);

  const fmt = (d) => d.toLocaleDateString(undefined, { month: "short", day: "numeric" });

  return (
    <div>
      <CalendarHeader
        title={`${fmt(weekStart)} – ${fmt(weekEnd)}`}
        onPrev={() => goTo(shiftDate(date, { days: -7 }))}
        onNext={() => goTo(shiftDate(date, { days: 7 }))}
        nextDisabled={days.some((d) => d.iso === today)}
        prevTitle="Previous week"
        nextTitle="Next week"
      />
      <div className="week-grid">
        {days.map(({ iso, weekday, day, shot, image }) => {
          const head = (
            <div className="week-card-head">
              <span>{weekday}</span>
              <strong>{day}</strong>
            </div>
          );
          if (!shot) {
            return (
              <div key={iso} className={`week-card${iso === today ? " today" : ""}`}>
                {head}
                <span className="week-empty">No captures</span>
              </div>
            );
          }
          const toggle = () => setExpanded(iso === expanded ? null : iso);
          const w = shot.Weather;
          const call = forecasts.get(iso)?.call;
          const stats = [
            ["Temp", w?.temperature_2m != null && `${Math.round(w.temperature_2m)}°F`],
            ["Cloud", w?.cloud_cover_total != null && `${Math.round(w.cloud_cover_total)}%`],
            ["Wind", (w?.obs_wind_mph ?? w?.wind_speed_10m) != null && `${Math.round(w.obs_wind_mph ?? w.wind_speed_10m)} mph`],
          ].filter(([, v]) => v);
          return (
            <div
              key={iso}
              className={`week-card has-image${iso === today ? " today" : ""}${iso === expanded ? " selected" : ""}`}
              role="button"
              tabIndex={0}
              aria-expanded={iso === expanded}
              onClick={toggle}
              onKeyDown={(e) => {
                if (e.key !== "Enter" && e.key !== " ") return;
                e.preventDefault();
                toggle();
              }}
            >
              {head}
              <div className="week-photo">
                <Img src={small(image)} alt={`${weekday} ${iso}`} loading="lazy" {...SIZES.photo} />
                <FlagPill reason={shot.Excluded} className="on-photo" />
              </div>
              <div className="week-score">{`${shot.Score.toFixed(0)}%`}</div>
              <div className="week-meta">{`${captureName(shot.Label, event)} · ${shot.Time}`}</div>
              {call && (
                <Tip label="Forecast made 1 hr before">
                  <span className={`bubble ${CALL_TONE[call] ?? ""}`}>{call}</span>
                </Tip>
              )}
              {!!stats.length && (
                <dl className="week-stats">
                  {stats.map(([label, value]) => (
                    <div key={label} style={{ display: "contents" }}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          );
        })}
      </div>
      {open && (
        <div className="cal-inline-detail">
          <DayDetail
            key={open.iso}
            date={open.iso}
            start={open.image}
            allData={allData}
            onClose={() => setExpanded(null)}
            onLoadToHsv={onLoadToHsv}
            permalink={permalinkFor(open.iso)}
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Year view -- one row per month, month name on the left, then only the days
// that actually have a capture, laid out left-to-right (missing days and months skipped).
// ---------------------------------------------------------------------------
function YearView({ date, goTo, byDate, allData, onLoadToHsv, permalinkFor }) {
  const year = fromISODate(date).getFullYear();
  const captured = [...byDate.keys()];
  const months = MONTH_NAMES.map((name, m) => [name, m])
    .filter(([, m]) => captured.some((iso) => iso.startsWith(isoFor(year, m, 1).slice(0, 7))));

  return (
    <div>
      <CalendarHeader
        title={`${year}`}
        onPrev={() => goTo(shiftDate(date, { years: -1 }))}
        onNext={() => goTo(shiftDate(date, { years: 1 }))}
        nextDisabled={year >= new Date().getFullYear()}
      />
      <div className="year-view-list">
        {!months.length && <div className="empty">No captures this year.</div>}
        {months.map(([name, m]) => (
          <YearMonthRow key={`${year}-${m}`} {...{ year, month: m, name, byDate, allData, onLoadToHsv, permalinkFor }} />
        ))}
      </div>
    </div>
  );
}

function YearMonthRow({ year, month, name, byDate, allData, onLoadToHsv, permalinkFor }) {
  const [openDate, setOpenDate] = useState(null);
  const detailRef = useRef(null);
  // The viewer opens below the whole month, which on a phone is often off-screen: bring it into view.
  useEffect(() => {
    if (openDate) detailRef.current?.scrollIntoView({ block: "start" });
  }, [openDate]);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days = [];
  for (let day = 1; day <= daysInMonth; day++) {
    const iso = isoFor(year, month, day);
    const entry = byDate.get(iso);
    if (entry) days.push({ iso, entry }); // skip days with no captures entirely
  }

  return (
    <>
      <div className="year-month-row">
        <div className="year-month-row-label">{name}</div>
        <div className="year-month-row-strip">
          {days.map(({ iso, entry }) => (
            <div
              key={iso}
              className={`year-mini-cell has-image${entry.Excluded ? " flagged" : ""}${iso === openDate ? " selected" : ""}`}
              onClick={() => setOpenDate(iso === openDate ? null : iso)}
            >
              <Tip label={`${iso} · ${entry.Score.toFixed(0)}%${entry.Excluded ? ` · doesn't count: ${entry.Excluded}` : ""}`}>
                <Img src={small(entry.Image)} alt={iso} loading="lazy" {...SIZES.photo} />
              </Tip>
            </div>
          ))}
        </div>
      </div>
      <div ref={detailRef} className="year-detail-anchor" />
      <Reveal show={!!openDate}>
        {openDate && (
          <DayDetail
            key={openDate}
            date={openDate}
            start={byDate.get(openDate)?.Image}
            allData={allData}
            onClose={() => setOpenDate(null)}
            onLoadToHsv={onLoadToHsv}
            permalink={permalinkFor(openDate)}
          />
        )}
      </Reveal>
    </>
  );
}

/** True when the open day falls in the week (grid row) that ends on `day` of this month. */
function expandedWeek(expanded, year, month, startWeekday, day) {
  if (!expanded) return false;
  const d = fromISODate(expanded);
  if (d.getFullYear() !== year || d.getMonth() !== month) return false;
  const row = (n) => Math.floor((startWeekday + n - 1) / 7);
  return row(d.getDate()) === row(day);
}

// ---------------------------------------------------------------------------
// Month view (the original calendar grid)
// ---------------------------------------------------------------------------
function MonthView({ date, goTo, byDate, allData, onLoadToHsv, permalinkFor, expanded, mark, setExpanded }) {
  const focus = fromISODate(date);
  const year = focus.getFullYear();
  const month = focus.getMonth();

  const now = new Date();
  const isCurrentMonth = year === now.getFullYear() && month === now.getMonth();

  const startWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const trailingBlanks = (7 - ((startWeekday + daysInMonth) % 7)) % 7;

  return (
    <div>
      <CalendarHeader
        title={`${MONTH_NAMES[month]} ${year}`}
        onPrev={() => goTo(shiftDate(date, { months: -1 }))}
        onNext={() => goTo(shiftDate(date, { months: 1 }))}
        nextDisabled={isCurrentMonth}
        prevTitle="Previous month"
        nextTitle="Next month"
      />

      <div>
        <div className="calendar-grid weekday-row">
          {WEEKDAYS.map((wd) => (
            <div key={wd} className="weekday-label">
              {wd}
            </div>
          ))}
        </div>
        <div className="calendar-grid day-grid">
          {Array.from({ length: startWeekday }, (_, i) => (
            <div key={`lead-${i}`} className="calendar-cell empty-cell" />
          ))}
          {Array.from({ length: daysInMonth }, (_, i) => {
            const day = i + 1;
            const iso = isoFor(year, month, day);
            const entry = byDate.get(iso);
            const cell = (
              <div
                key={iso}
                className={`calendar-cell${entry ? " has-image" : ""}${iso === expanded || iso === mark ? " selected" : ""}`}
                onClick={entry ? () => setExpanded(iso === expanded ? null : iso) : undefined}
              >
                <div className="day-number">{day}</div>
                {entry && (
                  <>
                    <Img src={small(entry.Image)} alt={iso} loading="lazy" />
                    <div className="day-time">{entry.Time}</div>
                    <div className="day-score">{`${entry.Score.toFixed(0)}%`}</div>
                    <FlagPill reason={entry.Excluded} className="on-photo" />
                  </>
                )}
              </div>
            );
            // The viewer opens inline, right under the week of the day that was clicked (as in the year view).
            const weekEnds = (startWeekday + i) % 7 === 6 || day === daysInMonth;
            if (!weekEnds || !expandedWeek(expanded, year, month, startWeekday, day)) return cell;
            return [cell, ...(day === daysInMonth ? Array.from({ length: trailingBlanks }, (_, t) => (
              <div key={`trail-${t}`} className="calendar-cell empty-cell" />
            )) : []), (
              <div key="detail" className="cal-inline-detail">
                <DayDetail
                  key={expanded}
                  date={expanded}
                  start={byDate.get(expanded)?.Image}
                  allData={allData}
                  onClose={() => setExpanded(null)}
                  onLoadToHsv={onLoadToHsv}
                  permalink={permalinkFor(expanded)}
                />
              </div>
            )];
          })}
          {!expandedWeek(expanded, year, month, startWeekday, daysInMonth) && Array.from({ length: trailingBlanks }, (_, i) => (
            <div key={`trail-${i}`} className="calendar-cell empty-cell" />
          ))}
        </div>
      </div>

    </div>
  );
}
