import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MotionConfig } from "motion/react";
import { BrowserRouter } from "react-router";
import App from "./App.jsx";
import { LightboxProvider } from "./lightbox.jsx";
import "./tailwind.css";
import "./style.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      {/* Honor the OS "reduce motion" setting for Motion animations (CSS ones are handled in style.css). */}
      <MotionConfig reducedMotion="user">
        <LightboxProvider>
          <App />
        </LightboxProvider>
      </MotionConfig>
    </BrowserRouter>
  </StrictMode>,
);
