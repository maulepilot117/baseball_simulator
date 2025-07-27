import { React, createRoot } from "../deps.ts";
import App from "./App.tsx";

const root = createRoot(document.getElementById("root")!);
root.render(React.createElement(App));