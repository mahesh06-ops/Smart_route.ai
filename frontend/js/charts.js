/**
 * Charts and Analytics Engine for Smart Route AI
 * Visualizes multi-factor comparisons and traffic delays using Chart.js
 */

let radarChartInstance = null;
let barChartInstance = null;

function renderAnalyticsCharts(routes) {
  if (!routes || routes.length === 0) return;

  const labels = ["Time Efficiency", "Traffic Flow", "Safety Index", "Weather Quality", "Fuel Economy", "Directness"];
  const colors = [
    { border: "#10B981", bg: "rgba(16, 185, 129, 0.2)" }, // Green (Recommended)
    { border: "#F59E0B", bg: "rgba(245, 158, 11, 0.2)" },  // Amber
    { border: "#8B5CF6", bg: "rgba(139, 92, 246, 0.2)" },  // Purple
  ];

  // 1. Radar Chart: Multi-Factor Comparison
  const radarCanvas = document.getElementById("radarChart");
  if (radarCanvas) {
    if (radarChartInstance) radarChartInstance.destroy();

    const datasets = routes.map((r, i) => {
      const b = r.score_breakdown || {};
      const normTime = b.travel_time ? b.travel_time.normalized_pct : 80;
      const normTraf = b.traffic ? b.traffic.normalized_pct : 75;
      const normSafe = b.safety ? b.safety.normalized_pct : 80;
      const normWeath = b.weather ? b.weather.normalized_pct : 90;
      const normFuel = b.fuel ? b.fuel.normalized_pct : 70;
      const normDist = b.distance ? b.distance.normalized_pct : 75;

      const style = colors[i % colors.length];
      return {
        label: `${r.route_name} (${r.smart_score})`,
        data: [normTime, normTraf, normSafe, normWeath, normFuel, normDist],
        borderColor: style.border,
        backgroundColor: style.bg,
        borderWidth: r.is_recommended ? 3 : 1.5,
        pointBackgroundColor: style.border,
      };
    });

    const isLight = document.body.classList.contains("light-theme");
    const gridColor = isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
    const textColor = isLight ? "#475569" : "#94A3B8";

    radarChartInstance = new Chart(radarCanvas.getContext("2d"), {
      type: "radar",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: { color: gridColor },
            grid: { color: gridColor },
            pointLabels: { color: textColor, font: { size: 11, weight: "bold" } },
            ticks: { display: false, min: 0, max: 100 },
          },
        },
        plugins: {
          legend: {
            position: "top",
            labels: { color: textColor, boxWidth: 12, font: { size: 11 } },
          },
        },
      },
    });
  }

  // 2. Bar Chart: Travel Time & Congestion Delays
  const barCanvas = document.getElementById("barChart");
  if (barCanvas) {
    if (barChartInstance) barChartInstance.destroy();

    const isLight = document.body.classList.contains("light-theme");
    const gridColor = isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
    const textColor = isLight ? "#475569" : "#94A3B8";

    const routeNames = routes.map((r) => r.route_name.split("(")[0].trim());
    const baseMinutes = routes.map((r) => r.base_duration_minutes || r.duration_minutes);
    const delayMinutes = routes.map((r) => r.traffic.delay_minutes || 0);

    barChartInstance = new Chart(barCanvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: routeNames,
        datasets: [
          {
            label: "Base Free-Flow Time (mins)",
            data: baseMinutes,
            backgroundColor: "#3B82F6",
            borderRadius: 4,
          },
          {
            label: "Traffic Congestion Delay (mins)",
            data: delayMinutes,
            backgroundColor: "#EF4444",
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: { color: textColor },
          },
          y: {
            stacked: true,
            grid: { color: gridColor },
            ticks: { color: textColor },
            title: { display: true, text: "Minutes", color: textColor },
          },
        },
        plugins: {
          legend: {
            position: "top",
            labels: { color: textColor, boxWidth: 12 },
          },
        },
      },
    });
  }
}
