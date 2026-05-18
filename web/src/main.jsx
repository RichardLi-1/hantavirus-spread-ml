import { createRoot } from "react-dom/client";
import App from "./App";
import { configureChartDefaults } from "./chartTheme";
import "./style.css";

configureChartDefaults();

createRoot(document.getElementById("root")).render(<App />);
