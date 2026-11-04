import { createRoot } from "react-dom/client";
import { AiFileInspector } from "./index.js";
import "./standalone.css";
createRoot(document.getElementById("root")).render(
  <AiFileInspector localMode />,
);
