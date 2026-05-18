import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

export function MainChart({ chartConfig }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.destroy();
      chartRef.current = null;
    }
    if (!chartConfig || !canvasRef.current) return;

    const ctx = canvasRef.current.getContext("2d");
    chartRef.current = new Chart(ctx, chartConfig);

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [chartConfig]);

  return (
    <div className="canvas-wrap">
      <canvas ref={canvasRef} id="main-chart" />
    </div>
  );
}
