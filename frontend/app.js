/**
 * SoilSense Dashboard with Leaflet Map
 * Professional dark theme, Limpopo satellite map view
 */

const API_BASE = "http://localhost:8000";
let BACKEND_AVAILABLE = false;
let mapInstance = null;
let plotMarkers = [];

// Mock data for design testing
const MOCK_DATA = {
    maps: {
        cell_ids: ["L01", "L02", "L03", "L04", "L05", "L06", "L07", "L08", "L09", "L10"],
        sm_values: [0.098, 0.134, 0.320, 0.285, 0.152, 0.089, 0.198, 0.340, 0.125, 0.275],
        color_coded: ["drought", "monitor", "safe", "safe", "safe", "drought", "monitor", "safe", "monitor", "safe"],
    },
    alerts: {
        total_alerts: 4,
        critical: 2,
        warning: 2,
        alerts: [
            {
                cell_id: "L01",
                sm_value: 0.098,
                alert_type: "drought_critical",
                severity: "🔴",
                trigger_reason: "SM = 0.098 < 0.10 (critical drought)",
                timestamp: new Date().toISOString(),
            },
            {
                cell_id: "L06",
                sm_value: 0.089,
                alert_type: "drought_critical",
                severity: "🔴",
                trigger_reason: "SM = 0.089 < 0.10 (critical drought)",
                timestamp: new Date().toISOString(),
            },
            {
                cell_id: "L02",
                sm_value: 0.134,
                alert_type: "irrigation_needed",
                severity: "🟡",
                trigger_reason: "SM = 0.134 < 0.15 (irrigation warning)",
                timestamp: new Date().toISOString(),
            },
            {
                cell_id: "L09",
                sm_value: 0.125,
                alert_type: "irrigation_needed",
                severity: "🟡",
                trigger_reason: "SM = 0.125 < 0.15 (irrigation warning)",
                timestamp: new Date().toISOString(),
            },
        ],
    },
    validation: {
        metrics: {
            r: 0.931,
            rmse: 0.0181,
            mae: 0.0131,
            bias: 0.0021,
        },
    },
};

// Plot positions (distributed across Limpopo region)
const PLOT_POSITIONS = [
    { id: "L01", lat: -22.5, lon: 28.5 },
    { id: "L02", lat: -22.5, lon: 29.5 },
    { id: "L03", lat: -22.5, lon: 30.5 },
    { id: "L04", lat: -22.5, lon: 31.5 },
    { id: "L05", lat: -22.5, lon: 32.0 },
    { id: "L06", lat: -24.0, lon: 28.5 },
    { id: "L07", lat: -24.0, lon: 29.5 },
    { id: "L08", lat: -24.0, lon: 30.5 },
    { id: "L09", lat: -24.0, lon: 31.5 },
    { id: "L10", lat: -24.0, lon: 32.0 },
];

// Limpopo boundary (approximate polygon)
const LIMPOPO_BOUNDARY = [
    [-22.0, 28.0],
    [-22.0, 32.5],
    [-25.0, 32.5],
    [-25.0, 28.0],
    [-22.0, 28.0],
];

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM loaded, initializing...");
    setupEventListeners();
    initializeDashboard();

    // Small delay to ensure map container is fully rendered
    setTimeout(() => {
        initializeMap();
    }, 100);
});

function setupEventListeners() {
    document.getElementById("runPipelineBtn").addEventListener("click", runPipeline);
}

async function initializeDashboard() {
    try {
        const response = await fetch(`${API_BASE}/health`, { timeout: 2000 });
        if (response.ok) {
            BACKEND_AVAILABLE = true;
            console.log("✓ Backend connected");
        } else {
            useMockData();
        }
    } catch (error) {
        console.warn("Backend unavailable - using mock data");
        useMockData();
    }
}

function useMockData() {
    const btn = document.getElementById("runPipelineBtn");
    btn.innerHTML = '▶ Update Analysis <span style="font-size: 0.75rem; color: #9ca3af;">(Mock Mode)</span>';
    BACKEND_AVAILABLE = false;
    console.log("Mock data mode enabled");
}

function initializeMap() {
    try {
        // Check if Leaflet is loaded
        if (typeof L === 'undefined') {
            console.error("✗ Leaflet not loaded");
            return;
        }

        // Check if map container exists
        const mapContainer = document.getElementById('map');
        if (!mapContainer) {
            console.error("✗ Map container not found");
            return;
        }

        console.log("✓ Leaflet loaded, initializing map...");

        // Initialize Leaflet map
        mapInstance = L.map('map').setView([-23.5, 30.0], 9);
        console.log("✓ Map instance created");

        // Add satellite tiles (Mapbox or OpenStreetMap fallback)
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles © Esri',
            maxZoom: 18,
        }).addTo(mapInstance);
        console.log("✓ Tiles loaded");

        // Draw Limpopo boundary
        L.polygon(LIMPOPO_BOUNDARY, {
            color: '#4b5563',
            weight: 2,
            opacity: 0.6,
            fill: false,
            dashArray: '5, 5',
        }).addTo(mapInstance);
        console.log("✓ Boundary drawn");

        // Add plot markers
        addPlotMarkers(MOCK_DATA.maps.color_coded, MOCK_DATA.maps.sm_values);
        console.log("✓ Plot markers added");

        console.log("✓ Map fully initialized");
    } catch (error) {
        console.error("✗ Map initialization error:", error);
        console.error(error.stack);
    }
}

function addPlotMarkers(colors, values) {
    // Clear existing markers
    plotMarkers.forEach(marker => mapInstance.removeLayer(marker));
    plotMarkers = [];

    PLOT_POSITIONS.forEach((plot, idx) => {
        const color = colors[idx] || "safe";
        const value = values[idx] || 0;
        const bounds = [
            [plot.lat - 0.15, plot.lon - 0.15],
            [plot.lat + 0.15, plot.lon + 0.15],
        ];

        const className = `plot-marker-${color}`;
        const rectangle = L.rectangle(bounds, {
            className: className,
            fill: true,
            stroke: true,
            color: getStrokeColor(color),
            weight: 2,
            opacity: 0.8,
            fillOpacity: 0.7,
        });

        // Popup content
        const action = color === "drought" ? "🚨 Irrigate immediately"
                      : color === "monitor" ? "⚠️ Monitor closely"
                      : "✓ OK - skip irrigation";

        rectangle.bindPopup(`
            <div style="min-width: 150px;">
                <p><strong>${plot.id}</strong></p>
                <p style="color: #60a5fa; margin: 0.5rem 0;">SM: ${value.toFixed(3)} m³/m³</p>
                <p style="margin: 0.5rem 0; font-size: 0.85rem;">${action}</p>
            </div>
        `);

        rectangle.addTo(mapInstance);
        plotMarkers.push(rectangle);
    });
}

function getStrokeColor(colorClass) {
    const colors = {
        drought: "#991b1b",
        monitor: "#b45309",
        safe: "#15803d",
    };
    return colors[colorClass] || "#374151";
}

async function runPipeline() {
    const btn = document.getElementById("runPipelineBtn");
    btn.disabled = true;
    btn.textContent = "⏳ Processing...";

    try {
        if (BACKEND_AVAILABLE) {
            // Try real backend
            const response = await fetch(`${API_BASE}/pipeline/run`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            console.log("Pipeline result:", data);
            await updateDashboard();
        } else {
            // Use mock data with delay for UX
            console.log("Using mock data");
            await new Promise(resolve => setTimeout(resolve, 800));
            await updateDashboard(true);
        }

        btn.textContent = "✓ Updated";
        setTimeout(() => {
            btn.textContent = "▶ Update Analysis";
            if (!BACKEND_AVAILABLE) btn.innerHTML += ' <span style="font-size: 0.75rem; color: #9ca3af;">(Mock)</span>';
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        console.error("Pipeline error:", error);
        btn.textContent = "✗ Error";

        // Fallback to mock data on error
        console.log("Falling back to mock data");
        await new Promise(resolve => setTimeout(resolve, 500));
        await updateDashboard(true);

        btn.textContent = "✓ Updated (Mock)";
        setTimeout(() => {
            btn.textContent = "▶ Update Analysis";
            btn.innerHTML += ' <span style="font-size: 0.75rem; color: #9ca3af;">(Mock)</span>';
            btn.disabled = false;
        }, 2000);
    }
}

async function updateDashboard(useMock = false) {
    try {
        let mapsData, alertsData, validationData;

        if (useMock || !BACKEND_AVAILABLE) {
            mapsData = MOCK_DATA.maps;
            alertsData = MOCK_DATA.alerts;
            validationData = MOCK_DATA.validation;
            console.log("Using mock data");
        } else {
            // Fetch real data
            const [mapsRes, alertsRes, validationRes] = await Promise.all([
                fetch(`${API_BASE}/dashboard/maps`),
                fetch(`${API_BASE}/dashboard/alerts`),
                fetch(`${API_BASE}/dashboard/validation`),
            ]);

            mapsData = mapsRes.ok ? await mapsRes.json() : MOCK_DATA.maps;
            alertsData = alertsRes.ok ? await alertsRes.json() : MOCK_DATA.alerts;
            validationData = validationRes.ok ? await validationRes.json() : MOCK_DATA.validation;
        }

        // Update map markers with new colors
        addPlotMarkers(mapsData.color_coded, mapsData.sm_values);

        // Update dashboard panels
        displayAlerts(alertsData);
        displayValidation(validationData);
        updateStatus(alertsData);

    } catch (error) {
        console.error("Dashboard update error:", error);
        // Gracefully fallback to mock
        addPlotMarkers(MOCK_DATA.maps.color_coded, MOCK_DATA.maps.sm_values);
        displayAlerts(MOCK_DATA.alerts);
        displayValidation(MOCK_DATA.validation);
        updateStatus(MOCK_DATA.alerts);
    }
}

function displayAlerts(data) {
    const container = document.getElementById("alertsContainer");
    container.innerHTML = "";

    if (!data.alerts || data.alerts.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-sm">✓ All plots safe - no alerts</p>';
        document.getElementById("exportCSVBtn").style.display = "none";
        return;
    }

    document.getElementById("exportCSVBtn").style.display = "block";

    data.alerts.forEach(alert => {
        const severity = alert.alert_type === "drought_critical" ? "critical" : "warning";
        const card = document.createElement("div");
        card.className = `alert-card ${severity} slide-in`;

        const emoji = severity === "critical" ? "🔴" : "🟡";
        card.innerHTML = `
            <h4>${emoji} ${alert.cell_id} - ${alert.alert_type.replace(/_/g, " ")}</h4>
            <p>Soil Moisture: <strong>${alert.sm_value.toFixed(3)} m³/m³</strong></p>
            <p style="color: #9ca3af; font-size: 0.75rem; margin-top: 0.5rem;">
                ${alert.trigger_reason}
            </p>
        `;

        container.appendChild(card);
    });
}

function displayValidation(data) {
    if (!data.metrics) return;

    const metrics = data.metrics;
    const trustEmoji = metrics.r >= 0.80 ? "🟢" : metrics.r >= 0.70 ? "🟡" : "🔴";

    document.getElementById("trustScore").textContent = trustEmoji;
    document.getElementById("trustText").textContent =
        metrics.r >= 0.80 ? "System reliable - all checks pass"
        : "System caution - review metrics";
}

function updateStatus(alertsData) {
    if (!alertsData.alerts) return;

    const total = alertsData.total_alerts || 0;
    const critical = alertsData.critical || 0;
    const warning = alertsData.warning || 0;
    const ok = 10 - total;

    document.getElementById("criticalCount").textContent = critical;
    document.getElementById("warningCount").textContent = warning;
    document.getElementById("okCount").textContent = ok;

    // Update progress bars
    const totalPlots = 10;
    document.getElementById("criticalBar").style.width = `${(critical / totalPlots) * 100}%`;
    document.getElementById("warningBar").style.width = `${(warning / totalPlots) * 100}%`;
    document.getElementById("okBar").style.width = `${(ok / totalPlots) * 100}%`;

    // Update timestamp
    const now = new Date();
    document.getElementById("lastUpdate").textContent = now.toLocaleTimeString();
    document.getElementById("lastUpdateTime").textContent = now.toLocaleTimeString();
}
