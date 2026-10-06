import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { initTheme } from "./theme";
import { initLang } from "./i18n";
import "./styles.css";

initTheme();
initLang();

const el = document.getElementById("root");
if (!el) throw new Error("root element not found");
createRoot(el).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
