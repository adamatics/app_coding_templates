import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { getRouterBasename } from "./lib/basepath";
import "./theme.css";
import "./ui.css";

// Router basename follows the runtime base path (resolved from the URL) so client-side
// navigation works under a sub-path (e.g. /apps/<slug>/). undefined means root.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={getRouterBasename()}>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
