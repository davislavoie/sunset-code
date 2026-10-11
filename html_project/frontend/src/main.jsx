import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MotionConfig } from "motion/react";
import { BrowserRouter } from "react-router";
import App from "./App.jsx";
import { LightboxProvider } from "./lightbox.jsx";
import "./tailwind.css";
import "./style.css";
import { TipProvider } from "./Tip.jsx";
import "@fontsource/titillium-web/300.css";
import "@fontsource/titillium-web/400.css";
import "@fontsource/titillium-web/600.css";
import "@fontsource/titillium-web/700.css";

// A theme picked with the sidebar toggle; otherwise the OS setting decides.
try {
  const theme = localStorage.getItem("theme");
  if (theme) document.documentElement.dataset.theme = theme;
} catch {
  // storage blocked: follow the OS
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      {/* Honor the OS "reduce motion" setting for Motion animations (CSS ones are handled in style.css). */}
      <MotionConfig reducedMotion="user">
        <LightboxProvider>
          <TipProvider delay={300}>
            <App />
          </TipProvider>
        </LightboxProvider>
      </MotionConfig>
    </BrowserRouter>
  </StrictMode>,
);
