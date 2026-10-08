// Labeled dropdown used by the Ranked Images and Score Tracker controls.

import Dropdown from "./Dropdown.jsx";

const labelStyle = { display: "block", marginBottom: 4, color: "var(--text-muted)", fontSize: "0.85em" };

export default function Select({ label, options, value, onChange }) {
  return (
    <div>
      <span style={labelStyle}>{label}</span>
      <Dropdown label={label} options={options} value={value} onChange={onChange} />
    </div>
  );
}
