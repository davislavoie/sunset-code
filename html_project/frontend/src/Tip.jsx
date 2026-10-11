// Styled tooltip (Base UI Tooltip) in place of the browser's native title popups.
// <Tip label="…"><button …/></Tip>: the child is the trigger, so it must accept a ref.

import { Tooltip } from "@base-ui/react/tooltip";

export default function Tip({ label, side = "top", children }) {
  if (!label) return children;
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
