// Themed slider (Base UI Slider): pass a number for one thumb or [min, max] for a range.
// Keyboard, touch and screen-reader support come from Base UI; the look from style.css (.rs-*).

import { Slider } from "@base-ui/react/slider";

export default function RangeSlider({ label, value, onChange, min = 0, max = 100, step = 1, trackBackground, format = String }) {
  const values = Array.isArray(value) ? value : [value];
  const thumbLabels = values.length > 1 ? [`${label} minimum`, `${label} maximum`] : [label];

  return (
    <Slider.Root
      className="rs-root"
      value={value}
      onValueChange={(next) => onChange(next)}
      min={min}
      max={max}
      step={step}
    >
      <div className="rs-header">
        <span className="rs-label">{label}</span>
        <span className="rs-value">{values.map(format).join(" – ")}</span>
      </div>
      <Slider.Control className="rs-control">
        <Slider.Track className="rs-track" style={trackBackground && { background: trackBackground }}>
          <Slider.Indicator className={`rs-indicator${trackBackground ? " rs-indicator-outline" : ""}`} />
          {values.map((_, i) => (
            <Slider.Thumb key={i} index={i} className="rs-thumb" aria-label={thumbLabels[i]} />
          ))}
        </Slider.Track>
      </Slider.Control>
    </Slider.Root>
  );
}
