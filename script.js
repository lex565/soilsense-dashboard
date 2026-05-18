// SoilSense Early Warning System — Dashboard Script

// ============================================================================
// CONFIGURATION
// ============================================================================

const CROP_ICONS = {
    maize: '🌽',
    wheat: '🌾',
    sorghum: '🌱',
};

const CROP_THRESHOLDS = {
    maize: {
        sm_critical: 0.10,
        sm_irrigation: 0.15,
        rainfall_deficit: 20,
        ndvi_stress: 0.05,
    },
    wheat: {
        sm_critical: 0.12,
        sm_irrigation: 0.18,
        rainfall_deficit: 25,
        ndvi_stress: 0.04,
    },
    sorghum: {
        sm_critical: 0.08,
        sm_irrigation: 0.13,
        rainfall_deficit: 15,
        ndvi_stress: 0.06,
    },
};

const GRID_CELLS = [
    { cell_id: 'L01', lat: -23.85, lon: 29.12, name: 'Polokwane_North', crop: 'maize' },
    { cell_id: 'L02', lat: -23.90, lon: 29.20, name: 'Polokwane_Center', crop: 'maize' },
    { cell_id: 'L03', lat: -23.95, lon: 29.28, name: 'Polokwane_South', crop: 'wheat' },
    { cell_id: 'L04', lat: -24.10, lon: 29.50, name: 'Mopani_East', crop: 'maize' },
    { cell_id: 'L05', lat: -24.20, lon: 29.60, name: 'Mopani_West', crop: 'sorghum' },
    { cell_id: 'L06', lat: -24.50, lon: 29.80, name: 'Musina_North', crop: 'wheat' },
    { cell_id: 'L07', lat: -24.55, lon: 29.85, name: 'Musina_South', crop: 'maize' },
    { cell_id: 'L08', lat: -23.70, lon: 28.90, name: 'Blouberg_West', crop: 'sorghum' },
    { cell_id: 'L09', lat: -23.80, lon: 28.80, name: 'Blouberg_Center', crop: 'maize' },
    { cell_id: 'L10', lat: -24.00, lon: 29.00, name: 'Capricorn_Central', crop: 'wheat' },
];

// Global state
let map;
let currentMarkers = {};
let allCellData = {};
let timesChart = null;
let currentFilter = 'all';
let currentCropFilter = 'all';
let cellMetrics = { total: 0, critical: 0, warning: 0, caution: 0, ok: 0, alerts: 0 };

// ============================================================================
// MOCK DATA GENERATION
// ============================================================================

function generateMockTimeSeries(cellId, days = 30) {
    const cellNum = parseInt(cellId.substring(1));
    const now = new Date();

    let smBase, smTrend;
    if (cellNum <= 3) {
        smBase = 0.12;
        smTrend = -0.005;
    } else if (cellNum <= 6) {
        smBase = 0.18;
        smTrend = 0.001;
    } else {
        smBase = 0.25;
        smTrend = -0.002;
    }

    const data = [];
    const dates = [];
    for (let i = 0; i < days; i++) {
        const date = new Date(now);
        date.setDate(date.getDate() - (days - 1 - i));
        dates.push(date.toISOString().split('T')[0]);

        let sm = smBase + smTrend * i + (Math.random() - 0.5) * 0.02;
        sm = Math.max(0.05, Math.min(0.35, sm));

        let rainfall = Math.random() > 0.7 ? Math.random() * 20 + 5 : 0;
        if ([1, 4, 7].includes(cellNum)) rainfall *= 0.5;

        const ndviBase = cellNum <= 3 ? 0.6 : 0.7;
        let ndvi = ndviBase - 0.01 * i + (Math.random() - 0.5) * 0.04;
        ndvi = Math.max(0.3, Math.min(0.8, ndvi));

        data.push({ sm, rainfall, ndvi });
    }

    // Historical baseline (30 days ago, normalized for date)
    const historicalSm = smBase + 0.02;

    return { dates, data, historicalSm };
}

// ============================================================================
// TRIGGER LOGIC
// ============================================================================

function checkThresholdAlerts(cellId, ts, crop) {
    const alerts = [];
    const thresholds = CROP_THRESHOLDS[crop] || CROP_THRESHOLDS.maize;
    const current = ts.data[ts.data.length - 1];

    if (current.sm < thresholds.sm_critical) {
        alerts.push({
            type: 'drought_critical',
            reason: 'threshold',
            message: `SM=${current.sm.toFixed(3)} < ${thresholds.sm_critical}`,
            severity: 'critical',
        });
    } else if (current.sm < thresholds.sm_irrigation) {
        alerts.push({
            type: 'irrigation_needed',
            reason: 'threshold',
            message: `SM=${current.sm.toFixed(3)} < ${thresholds.sm_irrigation}`,
            severity: 'warning',
        });
    }

    const rainfall7d = ts.data.slice(-7).reduce((sum, d) => sum + d.rainfall, 0);
    if (rainfall7d < thresholds.rainfall_deficit) {
        alerts.push({
            type: 'rainfall_deficit',
            reason: 'threshold',
            message: `7-day rainfall=${rainfall7d.toFixed(1)}mm < ${thresholds.rainfall_deficit}mm`,
            severity: 'warning',
        });
    }

    const ndviNow = current.ndvi;
    const ndvi7dAvg = ts.data.slice(-7).reduce((sum, d) => sum + d.ndvi, 0) / 7;
    const ndviDrop = ndvi7dAvg - ndviNow;
    if (ndviDrop > thresholds.ndvi_stress) {
        alerts.push({
            type: 'crop_stress',
            reason: 'threshold',
            message: `NDVI drop=${ndviDrop.toFixed(3)}`,
            severity: 'warning',
        });
    }

    return alerts;
}

function checkTrendAlerts(cellId, ts) {
    const alerts = [];
    const last3 = ts.data.slice(-3);

    if (last3.length === 3) {
        const isDecline = (last3[0].sm > last3[1].sm) && (last3[1].sm > last3[2].sm);
        if (isDecline) {
            const decline = (last3[0].sm - last3[2].sm).toFixed(4);
            alerts.push({
                type: 'drought_developing',
                reason: 'trend',
                message: `SM declining 3 days (drop=${decline}). Drought incoming.`,
                severity: 'caution',
            });
        }
    }

    return alerts;
}

function processCell(cellId, crop) {
    const ts = generateMockTimeSeries(cellId);
    const thresholdAlerts = checkThresholdAlerts(cellId, ts, crop);
    const trendAlerts = checkTrendAlerts(cellId, ts);
    const allAlerts = [...thresholdAlerts, ...trendAlerts];

    const severity = allAlerts.length > 0
        ? allAlerts.reduce((max, a) => {
            const order = { critical: 0, warning: 1, caution: 2 };
            return order[a.severity] < order[max] ? a.severity : max;
        }, 'ok')
        : 'ok';

    return { ts, alerts: allAlerts, severity };
}

// ============================================================================
// MAP INITIALIZATION
// ============================================================================

function initMap() {
    map = L.map('map').setView([-24.0, 29.3], 8);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
    }).addTo(map);

    GRID_CELLS.forEach((cell) => {
        const result = processCell(cell.cell_id, cell.crop);
        const severity = result.severity;

        allCellData[cell.cell_id] = {
            ...cell,
            ...result,
        };

        updateMetrics(severity);

        const iconColor = {
            critical: '#e74c3c',
            warning: '#f39c12',
            caution: '#e67e22',
            ok: '#27ae60',
        }[severity];

        const icon = L.divIcon({
            html: `<div class="map-marker ${severity}" style="background: ${iconColor};">📍</div>`,
            className: '',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
        });

        const marker = L.marker([cell.lat, cell.lon], { icon }).addTo(map);
        const cropIcon = CROP_ICONS[cell.crop] || '🌾';
        marker.bindPopup(`
            <strong>${cell.cell_id}: ${cell.name.replace(/_/g, ' ')}</strong><br/>
            <strong>${cropIcon} ${cell.crop.charAt(0).toUpperCase() + cell.crop.slice(1)}</strong><br/>
            Status: <strong>${severity.toUpperCase()}</strong><br/>
            Alerts: ${result.alerts.length}
        `);

        marker.on('click', () => selectCell(cell));
        currentMarkers[cell.cell_id] = marker;
    });

    populateCompareLists();
    updateSummary();
}

// ============================================================================
// METRICS
// ============================================================================

function updateMetrics(severity) {
    cellMetrics.total++;
    cellMetrics[severity]++;
    if (severity !== 'ok') cellMetrics.alerts++;
}

function updateSummary() {
    document.getElementById('statTotal').textContent = cellMetrics.total;
    document.getElementById('statCritical').textContent = cellMetrics.critical;
    document.getElementById('statWarning').textContent = cellMetrics.warning;
    document.getElementById('statCaution').textContent = cellMetrics.caution;
    document.getElementById('statOk').textContent = cellMetrics.ok;
    document.getElementById('statAlerts').textContent = cellMetrics.alerts;
}

// ============================================================================
// CELL SELECTION & DETAILS
// ============================================================================

function selectCell(cell) {
    const data = allCellData[cell.cell_id];

    const cropIcon = CROP_ICONS[cell.crop] || '🌾';
    const cellInfoHtml = `
        <table class="cell-info-table">
            <tr>
                <td>Cell ID:</td>
                <td><strong>${cell.cell_id}</strong></td>
            </tr>
            <tr>
                <td>Location:</td>
                <td>${cell.name.replace(/_/g, ' ')}</td>
            </tr>
            <tr>
                <td>Coords:</td>
                <td>${cell.lat.toFixed(2)}, ${cell.lon.toFixed(2)}</td>
            </tr>
            <tr>
                <td>Crop:</td>
                <td><strong>${cropIcon} ${cell.crop.charAt(0).toUpperCase() + cell.crop.slice(1)}</strong></td>
            </tr>
            <tr>
                <td>Status:</td>
                <td><strong class="alert-badge ${data.severity}">${data.severity.toUpperCase()}</strong></td>
            </tr>
            <tr>
                <td>SM (now):</td>
                <td><strong>${data.ts.data[data.ts.data.length - 1].sm.toFixed(3)} m³/m³</strong></td>
            </tr>
            <tr>
                <td>SM (normal):</td>
                <td>${data.ts.historicalSm.toFixed(3)} m³/m³</td>
            </tr>
            <tr>
                <td>Rainfall (7d):</td>
                <td>${data.ts.data.slice(-7).reduce((sum, d) => sum + d.rainfall, 0).toFixed(1)} mm</td>
            </tr>
            <tr>
                <td>NDVI (now):</td>
                <td>${data.ts.data[data.ts.data.length - 1].ndvi.toFixed(3)}</td>
            </tr>
            <tr>
                <td>Alerts:</td>
                <td>${data.alerts.length > 0 ? data.alerts.map(a => `<span class="alert-badge ${a.severity}">${a.type}</span>`).join('') : '<span style="color:#999;">None</span>'}</td>
            </tr>
        </table>
    `;

    document.getElementById('cellInfo').innerHTML = cellInfoHtml;
    updateTimeseriesChart(data.ts, data.severity);
    updateAlertLog(cell, data);

    Object.values(currentMarkers).forEach(m => m.setOpacity(0.5));
    currentMarkers[cell.cell_id].setOpacity(1).setZIndexOffset(1000);
}

function updateTimeseriesChart(ts, severity) {
    const ctx = document.getElementById('timeseriesChart').getContext('2d');

    if (timesChart) timesChart.destroy();

    const last10dates = ts.dates.slice(-10);
    const last10sm = ts.data.slice(-10).map(d => d.sm);
    const last10rainfall = ts.data.slice(-10).map(d => d.rainfall);
    const historicalLine = Array(10).fill(ts.historicalSm);

    // Forecast next 7 days (random mock)
    const forecastDates = Array.from({ length: 7 }, (_, i) => {
        const d = new Date(new Date(ts.dates[ts.dates.length - 1]).getTime() + (i + 1) * 24 * 60 * 60 * 1000);
        return `${d.getMonth() + 1}/${d.getDate()}*`;
    });

    const forecastRainfall = Array.from({ length: 7 }, () => Math.random() * 15);

    const allDates = [...last10dates.map(d => d.substring(5)), ...forecastDates];
    const allRainfall = [...last10rainfall, ...forecastRainfall];

    timesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDates,
            datasets: [
                {
                    label: 'SM (m³/m³)',
                    data: last10sm,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2.5,
                    tension: 0.4,
                    fill: true,
                    yAxisID: 'y',
                    segment: { borderDash: (ctx) => ctx.p0DataIndex >= 9 ? [5, 5] : [] },
                },
                {
                    label: 'Normal SM (baseline)',
                    data: historicalLine,
                    borderColor: '#95a5a6',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0,
                    fill: false,
                    yAxisID: 'y',
                    pointRadius: 0,
                },
                {
                    label: 'Rainfall (mm)',
                    data: allRainfall,
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.2)',
                    type: 'bar',
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { font: { size: 12 } },
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 10,
                    titleFont: { size: 12 },
                    bodyFont: { size: 12 },
                },
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'SM (m³/m³)', font: { size: 12 } },
                    min: 0,
                    max: 0.4,
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Rainfall (mm)', font: { size: 12 } },
                    min: 0,
                    max: 30,
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

function updateAlertLog(cell, data) {
    const alertLogHtml = data.alerts
        .map(alert => `
            <div class="alert-item ${alert.severity}">
                <div class="alert-item-header">${alert.type}</div>
                <div class="alert-item-body">${alert.message}</div>
                <div class="alert-item-time">[${alert.reason.toUpperCase()}] ${new Date().toLocaleTimeString()}</div>
            </div>
        `)
        .join('') || '<p class="hint">No active alerts for this cell.</p>';

    document.getElementById('alertLog').innerHTML = alertLogHtml;
}

// ============================================================================
// FILTERS & CONTROLS
// ============================================================================

function applyFilter(filter) {
    currentFilter = filter;
    updateMapVisibility();
}

function applyCropFilter(crop) {
    currentCropFilter = crop;
    updateMapVisibility();
}

function updateMapVisibility() {
    Object.entries(currentMarkers).forEach(([cellId, marker]) => {
        const data = allCellData[cellId];
        const meetsFilter = currentFilter === 'all' || data.severity === currentFilter;
        const meetsCropFilter = currentCropFilter === 'all' || data.crop === currentCropFilter;

        if (meetsFilter && meetsCropFilter) {
            marker.setOpacity(1);
        } else {
            marker.setOpacity(0.2);
        }
    });
}

// ============================================================================
// COMPARE CELLS
// ============================================================================

function populateCompareLists() {
    const selects = ['compareCell1', 'compareCell2'];
    selects.forEach(id => {
        const select = document.getElementById(id);
        GRID_CELLS.forEach(cell => {
            const option = document.createElement('option');
            option.value = cell.cell_id;
            const cropIcon = CROP_ICONS[cell.crop] || '🌾';
            option.textContent = `${cell.cell_id} (${cell.name.replace(/_/g, ' ')}) ${cropIcon}`;
            select.appendChild(option);
        });
    });
}

function compareCells() {
    const cell1Id = document.getElementById('compareCell1').value;
    const cell2Id = document.getElementById('compareCell2').value;

    if (!cell1Id || !cell2Id) {
        alert('Select two cells to compare');
        return;
    }

    const data1 = allCellData[cell1Id];
    const data2 = allCellData[cell2Id];

    const ctx = document.getElementById('timeseriesChart').getContext('2d');
    if (timesChart) timesChart.destroy();

    const dates = data1.ts.dates.slice(-10);
    const sm1 = data1.ts.data.slice(-10).map(d => d.sm);
    const sm2 = data2.ts.data.slice(-10).map(d => d.sm);

    timesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates.map(d => d.substring(5)),
            datasets: [
                {
                    label: `${data1.cell_id} (${data1.name})`,
                    data: sm1,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2.5,
                    tension: 0.4,
                },
                {
                    label: `${data2.cell_id} (${data2.name})`,
                    data: sm2,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2.5,
                    tension: 0.4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top' },
            },
            scales: {
                y: {
                    title: { display: true, text: 'SM (m³/m³)' },
                    min: 0,
                    max: 0.4,
                },
            },
        },
    });
}

// ============================================================================
// EXPORT
// ============================================================================

function exportAlerts() {
    let csv = 'Cell ID,Cell Name,Crop,Severity,Alert Type,Message,Timestamp\n';

    Object.entries(allCellData).forEach(([cellId, data]) => {
        if (data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                csv += `${cellId},"${data.name}","${data.crop}","${alert.severity}","${alert.type}","${alert.message}","${new Date().toISOString()}"\n`;
            });
        }
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `soilsense_alerts_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initMap();

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            applyFilter(e.target.dataset.filter);
        });
    });

    // Crop filter
    document.getElementById('cropSelect').addEventListener('change', (e) => {
        applyCropFilter(e.target.value);
    });

    // Compare button
    document.getElementById('compareBtn').addEventListener('click', compareCells);

    // Export button
    document.getElementById('exportBtn').addEventListener('click', exportAlerts);

    // Auto-select first cell
    if (GRID_CELLS.length > 0) {
        selectCell(GRID_CELLS[0]);
    }
});
