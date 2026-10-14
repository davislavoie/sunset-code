// Sunset Calendar with Day / Week / Month / Year views (mirrors
// streamlit_project/sunset_gallery.py). The Day tab is the "latest sunset" view:
// the day's best shot and score, then every capture. View, date and the expanded
// day live in the URL so any view can be shared: /calendar?view=month&date=2025-05-16

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { dayPath, useDocumentTitle } from "../api.js";
import DayDetail, { captureName } from "../DayDetail.jsx";
import { ForecastCard } from "../Forecast.jsx";
import Img, { SIZES, sizeForLabel } from "../Img.jsx";
import Reveal from "../Reveal.jsx";
import SunsetHero, { AiVerdict } from "../SunsetHero.jsx";
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

// Normalize display labels - ranked/histogram get generic names since they vary per day
function normalizeLabel(label) {
  const lower = label.toLowerCase();
  if (lower.includes("ranked")) return "Ranked";
  if (lower.includes("histogram")) return "Histogram";
  return label.slice(3); // Remove "01_", "07_", etc.
}

export default function Calendar({ data, camera, onLoadToHsv }) {
  // Shots that don't count (thumbs down, bad view, dark) still show, scored 0% with a pill saying why.
  const { ranked_images: rankedImages, all_data: allData, sunset_data: sunsetData } = data;
  const [params, setParams] = useSearchParams();
  const [cellHeight, setCellHeight] = useState(110);

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
  const goTo = (newDate) => update({ date: newDate, open: null });

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
        <button className="btn today-btn" onClick={() => goTo(toISODate(new Date()))}>
          Today
        </button>
      </div>

      {view === "day" && <DayView key={date} {...viewProps} camera={camera} best={rankedByDate.get(date)} />}
      {view === "week" && <WeekView {...viewProps} />}
      {view === "year" && <YearView {...viewProps} />}
      {view === "month" && (
        <MonthView
          {...viewProps}
          cellHeight={cellHeight}
          setCellHeight={setCellHeight}
          expanded={expanded}
          setExpanded={(d) => update({ open: d })}
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
function DayView({ date, goTo, allData, camera, best }) {
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

export function CaptureCard({ img, camera, event = "sunset", selected = false, onSelect }) {
  const [thumb, setThumb] = useState(img.Thumb ?? 0);
  const generated = /^(11_|12_)/.test(img.Label);
  const excluded = generated ? null : exclusionFor(img, thumb);
  return (
    <div className={`day-view-card${excluded ? " ai-not-sky" : ""}${selected ? " selected" : ""}`}>
      {onSelect ? (
        <Img src={img.Image} alt={img.Label} loading="lazy" onClick={onSelect} {...sizeForLabel(img.Label)} />
      ) : (
        <Zoomable src={img.Image} alt={img.Label} loading="lazy" {...sizeForLabel(img.Label)} />
      )}
      <div className="day-view-caption">
        <strong>{captureName(img.Label, event)}</strong>
        <span>
          {img.Time} &middot; Score: {(excluded ? 0 : img["HSV Score"] ?? img.Score).toFixed(1)}%
          {img.Weather?.temperature_2m != null && <> &middot; {Math.round(img.Weather.temperature_2m)}°F</>}
        </span>
        <FlagPill reason={excluded} />
        <GlassPill glass={img.Glass} hsv={img["HSV Score"]} />
        <AiVerdict ai={img.AI} compact />
        {!generated && <Thumbs camera={camera} img={img} onChange={(s) => setThumb(s.thumb)} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Week view -- table layout with photo labels in column 1, days across top
// ---------------------------------------------------------------------------
function WeekView({ date, goTo, allData }) {
  const focus = fromISODate(date);
  const weekStart = new Date(focus);
  weekStart.setDate(focus.getDate() - focus.getDay());
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 6);

  const now = new Date();
  const todayWeekStart = new Date(now);
  todayWeekStart.setDate(now.getDate() - now.getDay());
  const isCurrentWeek = toISODate(weekStart) === toISODate(todayWeekStart);

  const weekDates = WEEKDAYS.map((weekday, i) => {
    const dayDate = new Date(weekStart);
    dayDate.setDate(weekStart.getDate() + i);
    const iso = toISODate(dayDate);
    return { iso, dayDate, weekday, images: allData.filter((img) => img.Date === iso).sort(byLabelOrder) };
  });

  // Unique photo labels across the week (normalized for grouping), in capture order
  const labelSet = new Set(weekDates.flatMap((d) => d.images.map((img) => normalizeLabel(img.Label))));
  const firstLabel = (label) => allData.find((img) => normalizeLabel(img.Label) === label)?.Label || "99";
  const photoLabels = [...labelSet].sort((a, b) => labelOrder(firstLabel(a)) - labelOrder(firstLabel(b)));

  const fmt = (d) => d.toLocaleDateString(undefined, { month: "short", day: "numeric" });

  return (
    <div>
      <CalendarHeader
        title={`${fmt(weekStart)} – ${fmt(weekEnd)}`}
        onPrev={() => goTo(shiftDate(date, { days: -7 }))}
        onNext={() => goTo(shiftDate(date, { days: 7 }))}
        nextDisabled={isCurrentWeek}
      />
      <table className="week-view-table">
        <thead>
          <tr>
            <th className="week-label-col">Photo</th>
            {weekDates.map((d) => (
              <th key={d.iso}>{`${d.weekday} ${d.dayDate.getDate()}`}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {photoLabels.map((label) => (
            <tr key={label}>
              <td className="week-label-col">{label}</td>
              {weekDates.map((d) => {
                const img = d.images.find((i) => normalizeLabel(i.Label) === label);
                if (!img) {
                  return (
                    <td key={d.iso} className="week-day-empty">
                      —
                    </td>
                  );
                }
                return (
                  <td key={d.iso}>
                    <div className="week-day-thumb-wrap">
                      <Tip label={`${img.Time} · Score ${img.Score.toFixed(1)}%`}>
                        <Zoomable
                          {...sizeForLabel(img.Label)}
                          alt={img.Label}
                          className="week-day-thumb"
                          src={img.Image}
                          loading="lazy"
                        />
                      </Tip>
                      <div className="week-thumb-score">{`${img.Score.toFixed(0)}%`}</div>
                      <FlagPill reason={img.Excluded} className="on-photo" />
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Year view -- one row per month, month name on the left, then only the days
// that actually have a capture, laid out left-to-right (missing days skipped).
// ---------------------------------------------------------------------------
function YearView({ date, goTo, byDate, allData, onLoadToHsv, permalinkFor }) {
  const year = fromISODate(date).getFullYear();

  return (
    <div>
      <CalendarHeader
        title={`${year}`}
        onPrev={() => goTo(shiftDate(date, { years: -1 }))}
        onNext={() => goTo(shiftDate(date, { years: 1 }))}
        nextDisabled={year >= new Date().getFullYear()}
      />
      <div className="year-view-list">
        {MONTH_NAMES.map((name, m) => (
          <YearMonthRow key={`${year}-${m}`} {...{ year, month: m, name, byDate, allData, onLoadToHsv, permalinkFor }} />
        ))}
      </div>
    </div>
  );
}

function YearMonthRow({ year, month, name, byDate, allData, onLoadToHsv, permalinkFor }) {
  const [openDate, setOpenDate] = useState(null);
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
          {!days.length && <div className="year-month-row-empty">No captures</div>}
          {days.map(({ iso, entry }) => (
            <div
              key={iso}
              className={`year-mini-cell has-image${entry.Excluded ? " flagged" : ""}${iso === openDate ? " selected" : ""}`}
              onClick={() => setOpenDate(iso === openDate ? null : iso)}
            >
              <Tip label={`${iso} · ${entry.Score.toFixed(0)}%${entry.Excluded ? ` · doesn't count: ${entry.Excluded}` : ""}`}>
                <Img src={entry.Image} alt={iso} loading="lazy" {...SIZES.photo} />
              </Tip>
            </div>
          ))}
        </div>
      </div>
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
function MonthView({ date, goTo, byDate, allData, onLoadToHsv, permalinkFor, cellHeight, setCellHeight, expanded, setExpanded }) {
  const focus = fromISODate(date);
  const year = focus.getFullYear();
  const month = focus.getMonth();

  const now = new Date();
  const isCurrentMonth = year === now.getFullYear() && month === now.getMonth();

  const startWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const trailingBlanks = (7 - ((startWeekday + daysInMonth) % 7)) % 7;

  return (
    <div style={{ "--cal-row-height": `${cellHeight}px` }}>
      <CalendarHeader
        title={`${MONTH_NAMES[month]} ${year}`}
        onPrev={() => goTo(shiftDate(date, { months: -1 }))}
        onNext={() => goTo(shiftDate(date, { months: 1 }))}
        nextDisabled={isCurrentMonth}
        prevTitle="Previous month"
        nextTitle="Next month"
      />

      <div className="cal-size-control">
        <label>{`Size: ${cellHeight}px`}</label>
        <input
          type="range"
          min={50}
          max={220}
          value={cellHeight}
          onChange={(e) => setCellHeight(Number(e.target.value))}
        />
      </div>

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
                className={`calendar-cell${entry ? " has-image" : ""}${iso === expanded ? " selected" : ""}`}
                onClick={entry ? () => setExpanded(iso === expanded ? null : iso) : undefined}
              >
                <div className="day-number">{day}</div>
                {entry && (
                  <>
                    <Img src={entry.Image} alt={iso} loading="lazy" />
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
