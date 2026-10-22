/**
 * History Manager for Smart Route AI
 * Interacts with SQLite history endpoints to list, delete, and re-load past searches.
 */

async function loadHistoryList() {
  const tbody = document.getElementById("historyTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/history?limit=50");
    const json = await res.json();

    if (!json.success || !json.data || json.data.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">
            No route search history found. Try calculating your first smart route!
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = "";
    json.data.forEach((item) => {
      const tr = document.createElement("tr");
      const dateStr = new Date(item.timestamp).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });

      tr.innerHTML = `
        <td><span style="font-size: 11px; color: var(--text-muted);">${dateStr}</span></td>
        <td><strong>${item.source}</strong> → <strong>${item.destination}</strong></td>
        <td><span style="text-transform: capitalize;">${item.vehicle_type}</span></td>
        <td><span style="text-transform: uppercase; font-size: 11px; padding: 2px 6px; background: var(--bg-tertiary); border-radius: 4px;">${item.preference}</span></td>
        <td>${item.distance_km} km (${Math.round(item.duration_minutes)} mins)</td>
        <td><strong style="color: #10B981;">${Math.round(item.smart_score)}/100</strong></td>
        <td>
          <button class="map-ctrl-btn" onclick="loadHistoryItemIntoForm('${encodeURIComponent(item.source)}', '${encodeURIComponent(item.destination)}', '${item.vehicle_type}', '${item.preference}')" style="margin-right: 6px;">
            Load
          </button>
          <button class="btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="deleteHistoryItem(${item.id})">
            ✕
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

async function deleteHistoryItem(id) {
  if (!confirm("Delete this history record?")) return;
  try {
    const res = await fetch(`/api/history/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.success) {
      showToast("History entry deleted", "info");
      loadHistoryList();
    }
  } catch (err) {
    console.error("Error deleting history:", err);
  }
}

async function clearAllHistory() {
  if (!confirm("Are you sure you want to clear ALL search history?")) return;
  try {
    const res = await fetch("/api/history", { method: "DELETE" });
    const data = await res.json();
    if (data.success) {
      showToast("All search history cleared", "info");
      loadHistoryList();
    }
  } catch (err) {
    console.error("Error clearing history:", err);
  }
}

function loadHistoryItemIntoForm(source, destination, vehicle, preference) {
  document.getElementById("sourceInput").value = decodeURIComponent(source);
  document.getElementById("destInput").value = decodeURIComponent(destination);
  if (document.getElementById("vehicleSelect")) {
    document.getElementById("vehicleSelect").value = vehicle || "car";
  }
  if (document.getElementById("preferenceSelect")) {
    document.getElementById("preferenceSelect").value = preference || "balanced";
  }

  // Switch to dashboard tab
  switchTab("dashboard");

  // Trigger search
  const form = document.getElementById("routeForm");
  if (form) {
    form.dispatchEvent(new Event("submit"));
  }
}
