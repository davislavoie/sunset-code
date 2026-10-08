// Styled, accessible dropdown (Base UI Select): keyboard navigation, type-ahead
// and screen-reader support come from Base UI; the look comes from style.css (.dd-*).
// The native <select> list is drawn by the OS and can't be themed, hence this.

import { Select } from "@base-ui/react/select";

const toItem = (opt) => (typeof opt === "object" ? opt : { value: opt, label: opt });

export default function Dropdown({ value, onChange, options, placeholder = "Select…", label, name, disabled, className = "" }) {
  const items = options.map(toItem);

  return (
    <Select.Root
      items={items}
      value={value ?? null}
      onValueChange={(v) => onChange?.(v)}
      name={name}
      disabled={disabled || !items.length}
      modal={false}
    >
      <Select.Trigger className={`dd-trigger ${className}`.trim()} aria-label={label}>
        <Select.Value className="dd-value" placeholder={placeholder} />
        <Select.Icon className="dd-icon">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M11 10H5l3 3.5zm0-4H5l3-3.5z" />
          </svg>
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Positioner className="dd-positioner" sideOffset={6} alignItemWithTrigger={false}>
          <Select.Popup className="dd-popup">
            <Select.List className="dd-list">
              {items.map((item) => (
                <Select.Item key={item.value} value={item.value} className="dd-item">
                  <Select.ItemText>{item.label}</Select.ItemText>
                  <Select.ItemIndicator className="dd-check">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="m2.5 8.5 4 4 7-9" />
                    </svg>
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.List>
          </Select.Popup>
        </Select.Positioner>
      </Select.Portal>
    </Select.Root>
  );
}
