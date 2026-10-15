import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "./index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App.tsx";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("#root bulunamadı");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
