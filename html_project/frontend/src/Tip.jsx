// Styled tooltip (Base UI Tooltip) in place of the browser's native title popups.
// <Tip label="…"><button …/></Tip>: the child is the trigger, so it must accept a ref.

import { Tooltip } from "@base-ui/react/tooltip";

// Touch screens have no hover, and an iPhone treats a tooltip appearing on touch as a hover
// and swallows the tap, so tooltips are off there.
const canHover = typeof window !== "undefined" && window.matchMedia?.("(hover: hover)").matches;

export default function Tip({ label, side = "top", children }) {
  if (!label || !canHover) return children;
  return (
    <Tooltip.Root>
      <Tooltip.Trigger render={children} />
      <Tooltip.Portal>
        <Tooltip.Positioner className="tip-positioner" side={side} sideOffset={6}>
          <Tooltip.Popup className="tip-popup">{label}</Tooltip.Popup>
        </Tooltip.Positioner>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

// Wrap the app once: after the first tooltip opens, moving to the next one shows it instantly.
export const TipProvider = Tooltip.Provider;
