/**
 * Smart Visa Route Controller for Smart Route AI.
 * Handles dynamic all-country searching, profile matching recommendations,
 * country comparisons, live visa category details, what-if simulations, and cache refreshes.
 */

let allLoadedCountries = [];
let currentVisaPurpose = "Work Visa";
let lastRecommendationResult = null;

document.addEventListener("DOMContentLoaded", () => {
  initVisaModule();
});

function initVisaModule() {
  // Load initial countries
  loadVisaCountries();

  // Setup Visa sub-tabs
  setupVisaSubTabs();

  // Setup Recommendation Form
  setupVisaRecommendForm();

  // Setup Search & Filter listeners
  setupVisaSearchListeners();

  // Setup Comparison
  setupVisaComparison();

  // Setup Simulator
  setupVisaSimulator();

  // Setup Module Switcher (Road Route <-> Visa Route)
  setupModuleSwitcher();
}

/**
 * Top-level switcher between Smart Road Route and Smart Visa Route
 */
function setupModuleSwitcher() {
  const switchBtns = document.querySelectorAll(".module-switch-btn");
  switchBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetModule = btn.getAttribute("data-module");
      switchMainModule(targetModule);
    });
  });
}

function switchMainModule(moduleName) {
  document.querySelectorAll(".module-switch-btn").forEach((b) => {
    b.classList.toggle("active", b.getAttribute("data-module") === moduleName);
  });

  const roadContent = document.getElementById("module-road");
  const visaContent = document.getElementById("module-visa");
  const roadNav = document.getElementById("roadNavLinks");
  const visaNav = document.getElementById("visaNavLinks");

  if (moduleName === "visa") {
    if (roadContent) roadContent.style.display = "none";
    if (visaContent) visaContent.style.display = "block";
    if (roadNav) roadNav.style.display = "none";
    if (visaNav) visaNav.style.display = "flex";
  } else {
    if (roadContent) roadContent.style.display = "block";
    if (visaContent) visaContent.style.display = "none";
    if (roadNav) roadNav.style.display = "flex";
    if (visaNav) visaNav.style.display = "none";
    // Trigger Leaflet map invalidateSize
    if (typeof mapInstance !== "undefined" && mapInstance) {
      setTimeout(() => {
        mapInstance.invalidateSize();
        if (typeof recenterMap === "function") recenterMap();
      }, 100);
    }
  }
}

/**
 * Visa Sub-Tab Navigation
 */
function setupVisaSubTabs() {
  const visaNavItems = document.querySelectorAll(".visa-nav-item");
  visaNavItems.forEach((item) => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-visa-tab");
      switchVisaSubTab(tabId);
    });
  });
}

function switchVisaSubTab(tabId) {
  document.querySelectorAll(".visa-nav-item").forEach((item) => {
    item.classList.toggle("active", item.getAttribute("data-visa-tab") === tabId);
  });

  document.querySelectorAll(".visa-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === `visa-tab-${tabId}`);
  });

  if (tabId === "all-countries") {
    loadVisaCountries();
  } else if (tabId === "details") {
    populateCountryDetailSelector();
  } else if (tabId === "compare") {
    populateComparisonSelectors();
  }
}

/**
 * Load all countries with active filters
 */
async function loadVisaCountries() {
  const search = document.getElementById("visaSearchInput") ? document.getElementById("visaSearchInput").value.trim() : "";
  const region = document.getElementById("visaFilterRegion") ? document.getElementById("visaFilterRegion").value : "All";
  const purpose = document.getElementById("visaFilterPurpose") ? document.getElementById("visaFilterPurpose").value : "All";
  const safety = document.getElementById("visaFilterSafety") ? document.getElementById("visaFilterSafety").value : "0";
  const language = document.getElementById("visaFilterLanguage") ? document.getElementById("visaFilterLanguage").value : "Any";

  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (region && region !== "All") params.append("region", region);
  if (purpose && purpose !== "All") params.append("purpose", purpose);
  if (safety && safety !== "0") params.append("safety_min", safety);
  if (language && language !== "Any") params.append("language", language);

  const container = document.getElementById("allCountriesGrid");
  const countBadge = document.getElementById("countryCountBadge");

  if (container) {
    container.innerHTML = `<div class="loading-spinner-box"><div class="spinner"></div><span>Loading live country catalog...</span></div>`;
  }

  try {
    const res = await fetch(`/api/visa/countries?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to load country catalog");
    const countries = await res.json();
    allLoadedCountries = countries;

    if (countBadge) {
      countBadge.textContent = `${countries.length} Destinations Available`;
    }

    renderCountryGrid(countries);
    populateCountryDetailSelector();
    populateComparisonSelectors();
  } catch (err) {
    console.error("Error loading countries:", err);
    if (container) {
      container.innerHTML = `
        <div class="api-failure-alert">
          <span>⚠️ LIVE VISA DATA TEMPORARILY UNAVAILABLE</span>
          <p>Please try again later or verify information through the official immigration authority.</p>
          <button class="btn-refresh-cache" onclick="loadVisaCountries()">Try Again</button>
        </div>
      `;
    }
  }
}

function renderCountryGrid(countries) {
  const container = document.getElementById("allCountriesGrid");
  if (!container) return;

  if (countries.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
        <span style="font-size: 2rem;">🔍</span>
        <p>No countries match your search filters. Try clearing or expanding your criteria.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = countries
    .map(
      (c) => `
    <div class="country-card" onclick="viewCountryDetail('${c.code}')">
      <div class="country-card-header">
        <span class="country-flag">${c.flag_emoji}</span>
        <div class="country-title-box">
          <h4 class="country-name">${c.name}</h4>
          <span class="country-region">${c.region} • ${c.capital}</span>
        </div>
      </div>
      
      <div class="country-stats-row">
        <div class="country-stat">
          <span class="stat-lbl">Safety</span>
          <span class="stat-val" style="color: #10B981;">${c.safety_index.toFixed(1)}</span>
        </div>
        <div class="country-stat">
          <span class="stat-lbl">Cost Index</span>
          <span class="stat-val">${c.cost_of_living_index.toFixed(1)}</span>
        </div>
        <div class="country-stat">
          <span class="stat-lbl">Avg Salary</span>
          <span class="stat-val">$${(c.avg_annual_salary_usd / 1000).toFixed(0)}k/yr</span>
        </div>
      </div>

      <div class="country-footer">
        <span class="live-source-tag" title="${c.official_source.name}">
          🏛️ ${c.official_source.name.length > 26 ? c.official_source.name.substring(0, 26) + '...' : c.official_source.name}
        </span>
        <a href="${c.official_source.url}" target="_blank" class="btn-official-link" onclick="event.stopPropagation()">
          [ VIEW OFFICIAL SOURCE ]
        </a>
      </div>
    </div>
  `
    )
    .join("");
}

function setupVisaSearchListeners() {
  const searchInput = document.getElementById("visaSearchInput");
  const filterRegion = document.getElementById("visaFilterRegion");
  const filterPurpose = document.getElementById("visaFilterPurpose");
  const filterSafety = document.getElementById("visaFilterSafety");
  const filterLanguage = document.getElementById("visaFilterLanguage");
  const btnShowAll = document.getElementById("btnShowAllCountries");

  let debounceTimer;
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadVisaCountries();
      }, 300);
    });
  }

  [filterRegion, filterPurpose, filterSafety, filterLanguage].forEach((el) => {
    if (el) {
      el.addEventListener("change", () => loadVisaCountries());
    }
  });

  if (btnShowAll) {
    btnShowAll.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      if (filterRegion) filterRegion.value = "All";
      if (filterPurpose) filterPurpose.value = "All";
      if (filterSafety) filterSafety.value = "0";
      if (filterLanguage) filterLanguage.value = "Any";
      loadVisaCountries();
    });
  }
}

/**
 * Smart Recommendation Form Handler
 */
function setupVisaRecommendForm() {
  const form = document.getElementById("visaProfileForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const profile = {
      current_country: document.getElementById("vCurrentCountry").value.trim() || "India",
      age: parseInt(document.getElementById("vAge").value) || 28,
      education: document.getElementById("vEducation").value,
      field: document.getElementById("vField").value,
      work_experience_years: parseInt(document.getElementById("vExperience").value) || 4,
      purpose: document.getElementById("vPurpose").value,
      monthly_budget_usd: parseFloat(document.getElementById("vBudget").value) || 2500,
      language_skills: [document.getElementById("vLanguage").value],
      family_status: document.getElementById("vFamily").value,
      priority: document.getElementById("vPriority").value,
    };

    currentVisaPurpose = profile.purpose;

    const loadingEl = document.getElementById("visaRecLoading");
    const resultsSection = document.getElementById("visaRecResults");
    if (loadingEl) loadingEl.style.display = "flex";
    if (resultsSection) resultsSection.style.display = "none";

    try {
      const res = await fetch("/api/visa/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });

      if (!res.ok) throw new Error("Recommendation evaluation failed");
      const data = await res.json();
      lastRecommendationResult = data;

      renderRecommendations(data);
    } catch (err) {
      console.error("Error evaluating visa recommendations:", err);
      showToast("Failed to calculate visa recommendations. Please try again.", "error");
    } finally {
      if (loadingEl) loadingEl.style.display = "none";
    }
  });
}

function renderRecommendations(data) {
  const resultsSection = document.getElementById("visaRecResults");
  if (!resultsSection) return;
  resultsSection.style.display = "block";

  // 1. Total Evaluated Banner
  const totalCountEl = document.getElementById("evaluatedCountryCount");
  if (totalCountEl) totalCountEl.textContent = data.total_countries_evaluated;

  // 2. Top 3 Spotlight Cards
  const top3Container = document.getElementById("top3CardsContainer");
  if (top3Container && data.top_3) {
    top3Container.innerHTML = data.top_3
      .map(
        (item, idx) => `
      <div class="top-rec-card ${idx === 0 ? 'card-gold' : idx === 1 ? 'card-silver' : 'card-bronze'}">
        <div class="rec-badge-pill">${item.badge || `Top #${idx + 1}`}</div>
        
        <div class="rec-card-header">
          <span class="rec-flag">${item.flag_emoji}</span>
          <div>
            <h3 class="rec-country-title">${item.country_name}</h3>
            <span class="rec-region-sub">${item.region} • ${item.visa_name}</span>
          </div>
        </div>

        <div class="rec-score-display">
          <div class="rec-score-num">${item.smart_score}</div>
          <div class="rec-score-label">SMART SCORE / 100</div>
        </div>

        <!-- Metric Meters -->
        <div class="rec-factor-meters">
          <div class="rec-meter-row">
            <span>Visa Suitability</span>
            <span>${item.score_breakdown.visa_suitability}/100</span>
          </div>
          <div class="meter-bg"><div class="meter-fill" style="width: ${item.score_breakdown.visa_suitability}%;"></div></div>

          <div class="rec-meter-row">
            <span>Safety Rating</span>
            <span>${item.score_breakdown.safety}/100</span>
          </div>
          <div class="meter-bg"><div class="meter-fill" style="width: ${item.score_breakdown.safety}%;"></div></div>

          <div class="rec-meter-row">
            <span>Job Opportunities</span>
            <span>${item.score_breakdown.job_opportunities}/100</span>
          </div>
          <div class="meter-bg"><div class="meter-fill" style="width: ${item.score_breakdown.job_opportunities}%;"></div></div>

          <div class="rec-meter-row">
            <span>Cost Feasibility</span>
            <span>${item.score_breakdown.cost_affordability}/100</span>
          </div>
          <div class="meter-bg"><div class="meter-fill" style="width: ${item.score_breakdown.cost_affordability}%;"></div></div>
        </div>

        <!-- Pros & Trade-offs -->
        <div class="rec-insights-box">
          <div class="rec-insight-col">
            <strong>✅ Key Advantages:</strong>
            <ul>
              ${item.pros.map((p) => `<li>${p}</li>`).join("")}
            </ul>
          </div>
          <div class="rec-insight-col">
            <strong>⚖️ Trade-offs:</strong>
            <ul>
              ${item.trade_offs.map((t) => `<li>${t}</li>`).join("")}
            </ul>
          </div>
        </div>

        <!-- Next Steps & Official Authority -->
        <div class="rec-action-box">
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;">
            🏛️ Source: <strong>${item.official_source.name}</strong> (Checked: ${item.official_source.last_checked})
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <a href="${item.official_source.url}" target="_blank" class="btn-primary" style="flex: 1; text-align: center; text-decoration: none; padding: 10px;">
              [ VIEW OFFICIAL SOURCE ]
            </a>
            <button class="btn-secondary" onclick="viewCountryDetail('${item.country_code}')">
              Explore Visa Details
            </button>
          </div>
        </div>
      </div>
    `
      )
      .join("");
  }

  // 3. Top 10 Destinations Table
  const tableBody = document.getElementById("top10TableBody");
  if (tableBody && data.top_10) {
    tableBody.innerHTML = data.top_10
      .map(
        (item) => `
      <tr>
        <td style="font-weight: 800;">
          ${item.rank === 1 ? '🥇 #1' : item.rank === 2 ? '🥈 #2' : item.rank === 3 ? '🥉 #3' : `#${item.rank}`}
        </td>
        <td>
          <span style="font-size: 1.2rem; margin-right: 6px;">${item.flag_emoji}</span>
          <strong>${item.country_name}</strong>
        </td>
        <td>${item.region}</td>
        <td>${item.visa_name}</td>
        <td>
          <span class="score-badge" style="background: ${item.smart_score >= 85 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(59, 130, 246, 0.2)'}; color: ${item.smart_score >= 85 ? '#10B981' : '#3B82F6'}; font-weight: 800; padding: 4px 8px; border-radius: 4px;">
            ${item.smart_score} / 100
          </span>
        </td>
        <td>
          <a href="${item.official_source.url}" target="_blank" class="btn-link" title="${item.official_source.name}">
            [ Official Portal ↗ ]
          </a>
        </td>
        <td>
          <button class="btn-xs" onclick="viewCountryDetail('${item.country_code}')">Inspect</button>
        </td>
      </tr>
    `
      )
      .join("");
  }

  // Scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

/**
 * Country Details Explorer
 */
function populateCountryDetailSelector() {
  const select = document.getElementById("countryDetailSelect");
  if (!select || allLoadedCountries.length === 0) return;

  const currentVal = select.value;
  select.innerHTML = allLoadedCountries
    .map((c) => `<option value="${c.code}" ${c.code === currentVal ? "selected" : ""}>${c.flag_emoji} ${c.name} (${c.code})</option>`)
    .join("");

  if (!select.value && allLoadedCountries.length > 0) {
    select.value = "DEU"; // Default to Germany
  }
}

async function viewCountryDetail(countryCode) {
  // Switch to details tab
  switchVisaSubTab("details");

  const select = document.getElementById("countryDetailSelect");
  if (select) select.value = countryCode;

  loadSelectedCountryDetails(countryCode);
}

async function loadSelectedCountryDetails(countryCode) {
  const code = countryCode || (document.getElementById("countryDetailSelect") ? document.getElementById("countryDetailSelect").value : "DEU");
  const categorySelect = document.getElementById("detailCategorySelect");
  const selectedCategory = categorySelect ? categorySelect.value : "Work Visa";

  const container = document.getElementById("countryDetailContent");
  if (!container) return;

  container.innerHTML = `<div class="loading-spinner-box"><div class="spinner"></div><span>Retrieving verified visa details...</span></div>`;

  try {
    const res = await fetch(`/api/visa/country/${code}`);
    if (!res.ok) throw new Error("Country not found");
    const data = await res.json();

    const visa = data.visas[selectedCategory];

    container.innerHTML = `
      <div class="detail-header-card">
        <div style="display: flex; align-items: center; gap: 16px;">
          <span style="font-size: 3rem;">${data.flag_emoji}</span>
          <div>
            <h2 style="font-size: 1.6rem; font-weight: 800; margin: 0;">${data.name}</h2>
            <span style="color: var(--text-secondary); font-size: 0.9rem;">${data.region} • Capital: ${data.capital} • Languages: ${data.primary_languages.join(", ")}</span>
          </div>
        </div>

        <div style="margin-top: 16px; display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px;">
          <div class="metric-box">
            <span class="metric-box-title">Safety Index</span>
            <span class="metric-box-val" style="color: #10B981;">${data.safety_index.toFixed(1)} / 100</span>
          </div>
          <div class="metric-box">
            <span class="metric-box-title">Cost of Living</span>
            <span class="metric-box-val">${data.cost_of_living_index.toFixed(1)}</span>
          </div>
          <div class="metric-box">
            <span class="metric-box-title">Quality of Life</span>
            <span class="metric-box-val">${data.quality_of_life_index.toFixed(1)} / 100</span>
          </div>
          <div class="metric-box">
            <span class="metric-box-title">Avg Salary</span>
            <span class="metric-box-val">$${(data.avg_annual_salary_usd / 1000).toFixed(0)}k/yr</span>
          </div>
        </div>
      </div>

      <!-- Specific Visa Category Box -->
      <div class="visa-spec-box">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; margin-bottom: 16px;">
          <div>
            <h3 style="font-size: 1.2rem; color: var(--accent-cyan); font-weight: 700;">${visa ? visa.visa_name : `${data.name} ${selectedCategory}`}</h3>
            <span style="font-size: 0.85rem; color: var(--text-muted);">${selectedCategory} Category</span>
          </div>
          <span class="badge-live">VERIFIED OFFICIAL DATA</span>
        </div>

        ${
          visa
            ? `
          <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.5; margin-bottom: 16px;">
            ${visa.description}
          </p>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
            <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
              <strong style="color: var(--accent-primary); display: block; margin-bottom: 6px;">⏱️ Processing Time:</strong>
              <span>${visa.processing_time}</span>
            </div>
            <div style="background: var(--bg-tertiary); padding: 14px; border-radius: 8px;">
              <strong style="color: var(--accent-primary); display: block; margin-bottom: 6px;">💳 Statutory Fees:</strong>
              <span>${visa.fees}</span>
            </div>
          </div>

          <div style="margin-bottom: 16px;">
            <strong style="display: block; margin-bottom: 8px;">📋 Key Eligibility Requirements:</strong>
            <ul class="pros-list">
              ${visa.eligibility.map((e) => `<li>${e}</li>`).join("")}
            </ul>
          </div>

          <div style="margin-bottom: 20px;">
            <strong style="display: block; margin-bottom: 8px;">📂 Required Documentation:</strong>
            <ul class="pros-list">
              ${visa.required_documents.map((d) => `<li>${d}</li>`).join("")}
            </ul>
          </div>
        `
            : `
          <div class="api-failure-alert">
            <span>⚠ Information unavailable for this specific category</span>
            <p>Please verify directly with the official immigration authority for specialized permit routes.</p>
          </div>
        `
        }

        <!-- Official Authority Verification Box -->
        <div class="official-verification-card">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
              <div style="font-size: 0.85rem; color: var(--text-muted);">Current official source:</div>
              <strong style="font-size: 0.95rem; color: var(--text-primary);">${data.official_source.name}</strong>
              <div style="font-size: 0.78rem; color: var(--accent-cyan); margin-top: 2px;">Last checked: ${data.last_checked}</div>
            </div>
            <a href="${data.official_source.url}" target="_blank" class="btn-primary" style="text-decoration: none; padding: 10px 20px;">
              [ VIEW OFFICIAL SOURCE ]
            </a>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error("Error loading country details:", err);
    container.innerHTML = `
      <div class="api-failure-alert">
        <span>⚠ Information unavailable</span>
        <p>Please verify directly with the official immigration authority.</p>
      </div>
    `;
  }
}

/**
 * Country Comparison Matrix
 */
function populateComparisonSelectors() {
  const c1 = document.getElementById("compCountry1");
  const c2 = document.getElementById("compCountry2");
  const c3 = document.getElementById("compCountry3");

  if (!c1 || !c2 || !c3 || allLoadedCountries.length === 0) return;

  const options = allLoadedCountries
    .map((c) => `<option value="${c.code}">${c.flag_emoji} ${c.name}</option>`)
    .join("");

  c1.innerHTML = options;
  c2.innerHTML = options;
  c3.innerHTML = options;

  if (allLoadedCountries.some((c) => c.code === "DEU")) c1.value = "DEU";
  if (allLoadedCountries.some((c) => c.code === "CAN")) c2.value = "CAN";
  if (allLoadedCountries.some((c) => c.code === "AUS")) c3.value = "AUS";
}

function setupVisaComparison() {
  const btn = document.getElementById("btnRunComparison");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const c1 = document.getElementById("compCountry1").value;
    const c2 = document.getElementById("compCountry2").value;
    const c3 = document.getElementById("compCountry3").value;
    const purpose = document.getElementById("compPurpose").value;

    const container = document.getElementById("comparisonResultsContainer");
    if (container) {
      container.innerHTML = `<div class="loading-spinner-box"><div class="spinner"></div><span>Evaluating comparative criteria...</span></div>`;
    }

    try {
      const res = await fetch("/api/visa/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          country_codes: [c1, c2, c3],
          purpose: purpose,
          user_budget: 2500,
        }),
      });

      if (!res.ok) throw new Error("Comparison failed");
      const data = await res.json();
      renderVisaComparisonTable(data);
    } catch (err) {
      console.error("Comparison error:", err);
      showToast("Unable to run comparison. Please verify selections.", "error");
    }
  });
}

function renderVisaComparisonTable(data) {
  const container = document.getElementById("comparisonResultsContainer");
  if (!container || !data.countries) return;

  container.innerHTML = `
    <div class="table-responsive" style="margin-top: 20px;">
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Dimension / Metric</th>
            ${data.countries
              .map(
                (c) => `
              <th style="text-align: center;">
                <span style="font-size: 1.4rem;">${c.flag_emoji}</span><br>
                <strong>${c.country_name}</strong>
              </th>
            `
              )
              .join("")}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Overall Smart Score</strong></td>
            ${data.countries
              .map(
                (c) => `
              <td style="text-align: center; font-weight: 800; color: #10B981; font-size: 1.1rem;">
                ${c.smart_score} / 100
              </td>
            `
              )
              .join("")}
          </tr>
          <tr>
            <td><strong>Safety Rating</strong></td>
            ${data.countries.map((c) => `<td style="text-align: center;">${c.safety_index.toFixed(1)} / 100</td>`).join("")}
          </tr>
          <tr>
            <td><strong>Cost of Living Index</strong></td>
            ${data.countries.map((c) => `<td style="text-align: center;">${c.cost_of_living_index.toFixed(1)} (US=100)</td>`).join("")}
          </tr>
          <tr>
            <td><strong>Average Annual Salary</strong></td>
            ${data.countries.map((c) => `<td style="text-align: center;">$${(c.avg_annual_salary_usd / 1000).toFixed(0)}k USD</td>`).join("")}
          </tr>
          <tr>
            <td><strong>Quality of Life Index</strong></td>
            ${data.countries.map((c) => `<td style="text-align: center;">${c.quality_of_life_index.toFixed(1)} / 100</td>`).join("")}
          </tr>
          <tr>
            <td><strong>${data.purpose} Program</strong></td>
            ${data.countries
              .map(
                (c) => `
              <td style="font-size: 0.85rem;">
                ${c.visa_details_for_purpose ? `<strong>${c.visa_details_for_purpose.visa_name}</strong><br>⏱️ ${c.visa_details_for_purpose.processing_time}` : 'Standard Statutory Route'}
              </td>
            `
              )
              .join("")}
          </tr>
          <tr>
            <td><strong>Official Source & Portal</strong></td>
            ${data.countries
              .map(
                (c) => `
              <td style="text-align: center;">
                <a href="${c.official_source.url}" target="_blank" class="btn-xs" style="text-decoration: none;">
                  [ Official Source ]
                </a>
              </td>
            `
              )
              .join("")}
          </tr>
        </tbody>
      </table>
    </div>
  `;
}

/**
 * What-If Simulator
 */
function setupVisaSimulator() {
  const ageSlider = document.getElementById("simAgeSlider");
  const expSlider = document.getElementById("simExpSlider");
  const budgetSlider = document.getElementById("simBudgetSlider");

  const ageVal = document.getElementById("simAgeVal");
  const expVal = document.getElementById("simExpVal");
  const budgetVal = document.getElementById("simBudgetVal");

  if (ageSlider && ageVal) {
    ageSlider.addEventListener("input", (e) => {
      ageVal.textContent = `${e.target.value} years`;
      triggerSimulation();
    });
  }

  if (expSlider && expVal) {
    expSlider.addEventListener("input", (e) => {
      expVal.textContent = `${e.target.value} years`;
      triggerSimulation();
    });
  }

  if (budgetSlider && budgetVal) {
    budgetSlider.addEventListener("input", (e) => {
      budgetVal.textContent = `$${parseInt(e.target.value).toLocaleString()}/mo`;
      triggerSimulation();
    });
  }

  const prioritySelect = document.getElementById("simPrioritySelect");
  if (prioritySelect) {
    prioritySelect.addEventListener("change", () => triggerSimulation());
  }
}

let simDebounceTimer;
function triggerSimulation() {
  clearTimeout(simDebounceTimer);
  simDebounceTimer = setTimeout(async () => {
    const age = parseInt(document.getElementById("simAgeSlider").value) || 28;
    const exp = parseInt(document.getElementById("simExpSlider").value) || 4;
    const budget = parseFloat(document.getElementById("simBudgetSlider").value) || 2500;
    const priority = document.getElementById("simPrioritySelect").value;

    const baseProfile = {
      current_country: "Applicant",
      age: 28,
      education: "bachelor",
      field: "tech",
      work_experience_years: 4,
      purpose: currentVisaPurpose || "Work Visa",
      monthly_budget_usd: 2500,
      language_skills: ["English"],
      family_status: "single",
      priority: "balanced",
    };

    try {
      const res = await fetch("/api/visa/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_profile: baseProfile,
          adjusted_age: age,
          adjusted_experience: exp,
          adjusted_budget: budget,
          adjusted_priority: priority,
        }),
      });

      if (!res.ok) throw new Error("Simulation failed");
      const data = await res.json();
      renderSimulationResults(data);
    } catch (err) {
      console.error("Simulation error:", err);
    }
  }, 250);
}

function renderSimulationResults(data) {
  const container = document.getElementById("simResultsContainer");
  if (!container || !data.simulated_scores) return;

  const entries = Object.entries(data.simulated_scores);
  entries.sort((a, b) => b[1] - a[1]);

  container.innerHTML = `
    <div style="margin-top: 16px;">
      <h4 style="font-size: 1rem; margin-bottom: 12px; color: var(--accent-cyan);">⚡ Real-Time Score Shifts Across Top Destinations</h4>
      <div style="display: flex; flex-direction: column; gap: 10px;">
        ${entries
          .slice(0, 6)
          .map(([code, newScore]) => {
            const origScore = data.original_scores[code] || newScore;
            const delta = data.score_deltas[code] || 0;
            const country = allLoadedCountries.find((c) => c.code === code);
            const flag = country ? country.flag_emoji : "🌍";
            const name = country ? country.name : code;

            return `
            <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-size: 1.2rem; margin-right: 8px;">${flag}</span>
                <strong>${name}</strong>
              </div>
              <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-size: 0.85rem; color: var(--text-muted);">Baseline: ${origScore}</span>
                <span style="font-weight: 800; font-size: 1rem; color: #10B981;">Simulated: ${newScore}</span>
                <span style="font-weight: 700; font-size: 0.85rem; color: ${delta >= 0 ? '#10B981' : '#EF4444'};">
                  ${delta >= 0 ? `+${delta}` : delta}
                </span>
              </div>
            </div>
          `;
          })
          .join("")}
      </div>

      <div style="margin-top: 14px; padding: 12px; background: rgba(59, 130, 246, 0.08); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.2); font-size: 0.85rem; color: var(--text-secondary);">
        💡 <strong>Key Simulation Insight:</strong> ${data.key_insights.join(" ")}
      </div>
    </div>
  `;
}

/**
 * Cache Refresh Handler
 */
async function refreshVisaCache() {
  try {
    showToast("Refreshing live visa catalog from official authorities...", "info");
    const res = await fetch("/api/visa/cache/refresh", { method: "POST" });
    const data = await res.json();
    showToast(`Refreshed ${data.total_countries} countries successfully!`, "info");
    loadVisaCountries();
  } catch (err) {
    console.error("Cache refresh error:", err);
    showToast("Cache refresh failed.", "error");
  }
}
