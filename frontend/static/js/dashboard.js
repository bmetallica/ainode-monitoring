const API = "";
const REFRESH_MS = 5000;

const charts = {
    cpu: null,
    mem: null,
    gpuUtil: null,
    gpuMem: null,
    modelPie: null,
    modelBar: null,
    clusterPie: null,
};

const historyData = {
    cpu: { labels: [], data: [] },
    mem: { labels: [], data: [] },
    gpuUtil: { labels: [], data: [] },
    gpuMem: { labels: [], data: [] },
};

const MAX_HISTORY = 60;

function fmtUptime(s) {
    if (!s) return "--";
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    return d > 0 ? `${d}d ${h}h ${m}m` : `${h}h ${m}m`;
}

function fmtMem(mb) {
    if (mb == null) return "--";
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
    return `${Math.round(mb)} MB`;
}

function fmtTemps(temps) {
    if (!temps || typeof temps !== "object") return "--";
    return Object.entries(temps)
        .map(([k, v]) => `${k}: ${v}°C`)
        .join(", ");
}

async function loadConfig() {
    try {
        const res = await fetch(`${API}/api/config`);
        const c = await res.json();
        document.getElementById("broker").value = c.broker || "";
        document.getElementById("port").value = c.port || 1883;
        document.getElementById("user").value = c.user || "";
        document.getElementById("password").value = c.password || "";
        document.getElementById("topic-prefix").value = c.topic_prefix || "";
        updateStatus(c.connected);
    } catch (e) {
        console.error("Failed to load config", e);
    }
}

function updateStatus(connected) {
    const el = document.getElementById("mqtt-status");
    el.className = "status-dot " + (connected ? "connected" : "disconnected");
}

document.getElementById("mqtt-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        broker: document.getElementById("broker").value,
        port: parseInt(document.getElementById("port").value, 10),
        user: document.getElementById("user").value,
        password: document.getElementById("password").value,
        topic_prefix: document.getElementById("topic-prefix").value,
    };
    try {
        const res = await fetch(`${API}/api/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const c = await res.json();
        updateStatus(c.connected);
    } catch (err) {
        console.error("Failed to save config", err);
    }
});

async function loadNodes() {
    try {
        const res = await fetch(`${API}/api/nodes`);
        const nodes = await res.json();
        const sel = document.getElementById("node-select");
        const current = sel.value;
        sel.innerHTML = '<option value="">All Nodes</option>';
        for (const n of nodes) {
            const opt = document.createElement("option");
            opt.value = n;
            opt.textContent = n;
            sel.appendChild(opt);
        }
        if (nodes.includes(current)) sel.value = current;
    } catch (e) {
        console.error("Failed to load nodes", e);
    }
}

function selectedNode() {
    return document.getElementById("node-select").value || null;
}

async function loadSystem() {
    try {
        const url = selectedNode()
            ? `${API}/api/live/system?node_id=${encodeURIComponent(selectedNode())}`
            : `${API}/api/live/system`;
        const res = await fetch(url);
        const data = await res.json();
        const item = Array.isArray(data) ? data[0] : data;
        if (!item) return;

        document.getElementById("sys-cpu").textContent = `${item.cpu_percent ?? "--"}%`;
        document.getElementById("sys-cpu-cores").textContent = item.cpu_cores ?? "--";
        document.getElementById("sys-load").textContent =
            [item.cpu_load_1m, item.cpu_load_5m, item.cpu_load_15m]
                .map(v => v != null ? v.toFixed(2) : "--")
                .join("/");
        document.getElementById("sys-mem").textContent = `${item.mem_percent ?? "--"}%`;
        document.getElementById("sys-mem-detail").textContent =
            `${fmtMem(item.mem_used_mb)} / ${fmtMem(item.mem_total_mb)}`;
        document.getElementById("sys-swap").textContent =
            item.swap_used_mb != null
                ? `${fmtMem(item.swap_used_mb)} / ${fmtMem(item.swap_total_mb)}`
                : "--";
        document.getElementById("sys-uptime").textContent = fmtUptime(item.uptime_seconds);
        document.getElementById("sys-temps").textContent = fmtTemps(item.temperatures);

        pushHistory("cpu", item.cpu_percent);
        pushHistory("mem", item.mem_percent);
    } catch (e) {
        console.error("Failed to load system metrics", e);
    }
}

async function loadGPU() {
    try {
        const url = selectedNode()
            ? `${API}/api/live/gpu?node_id=${encodeURIComponent(selectedNode())}`
            : `${API}/api/live/gpu`;
        const res = await fetch(url);
        const data = await res.json();
        const item = Array.isArray(data) ? data[0] : data;
        if (!item) return;

        document.getElementById("gpu-util").textContent = `${item.utilization_percent ?? "--"}%`;
        document.getElementById("gpu-mem-used").textContent = fmtMem(item.memory_used_mb);
        document.getElementById("gpu-mem-total").textContent = fmtMem(item.memory_total_mb);
        document.getElementById("gpu-temp").textContent = `${item.temperature_c ?? "--"}°C`;

        pushHistory("gpuUtil", item.utilization_percent);
        pushHistory("gpuMem", item.memory_used_mb);
    } catch (e) {
        console.error("Failed to load GPU metrics", e);
    }
}

async function loadModels() {
    try {
        const url = selectedNode()
            ? `${API}/api/live/models?node_id=${encodeURIComponent(selectedNode())}`
            : `${API}/api/live/models`;
        const res = await fetch(url);
        const data = await res.json();
        const item = Array.isArray(data) ? data[0] : data;
        if (!item) return;

        document.getElementById("model-requests").textContent = item.requests_total ?? "--";
        document.getElementById("model-errors").textContent = item.errors_total ?? "--";
        document.getElementById("model-uptime").textContent = fmtUptime(item.uptime_seconds);

        renderModelDetails(item);
        renderModelPie(item);
        renderModelBar(item);
    } catch (e) {
        console.error("Failed to load model metrics", e);
    }
}

function renderModelDetails(item) {
    const container = document.getElementById("model-details");
    const perModel = item.per_model || {};
    const models = Object.entries(perModel);
    if (!models.length) {
        container.innerHTML = "";
        return;
    }
    let html = "<table class='model-table'><thead><tr>" +
        "<th>Model</th><th>Requests</th><th>Errors</th><th>Latency</th><th>Tokens</th><th>tok/s</th>" +
        "</tr></thead><tbody>";
    for (const [name, m] of models) {
        html += `<tr>` +
            `<td>${name}</td>` +
            `<td>${m.requests ?? 0}</td>` +
            `<td>${m.errors ?? 0}</td>` +
            `<td>${m.avg_latency_ms != null ? m.avg_latency_ms.toFixed(0) + "ms" : "--"}</td>` +
            `<td>${m.tokens_generated ?? 0}</td>` +
            `<td>${m.avg_tokens_per_second != null ? m.avg_tokens_per_second.toFixed(1) : "--"}</td>` +
            `</tr>`;
    }
    html += "</tbody></table>";
    container.innerHTML = html;
}

function renderModelPie(item) {
    const perModel = item.per_model || {};
    const labels = Object.keys(perModel);
    const values = labels.map(n => perModel[n].tokens_generated || 0);
    if (!labels.length) return;

    if (charts.modelPie) charts.modelPie.destroy();
    charts.modelPie = new Chart(document.getElementById("model-pie-chart"), {
        type: "pie",
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    "#00e676", "#00bfa5", "#2979ff", "#ff9100",
                    "#ff5252", "#b388ff", "#64ffda", "#ffff00",
                ],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#e0e0e0", font: { size: 11 } } },
                title: { display: true, text: "Tokens Generated by Model", color: "#e0e0e0" },
            },
        },
    });
}

function renderModelBar(item) {
    const perModel = item.per_model || {};
    const labels = Object.keys(perModel);
    const tps = labels.map(n => perModel[n].avg_tokens_per_second || 0);
    if (!labels.length) return;

    if (charts.modelBar) charts.modelBar.destroy();
    charts.modelBar = new Chart(document.getElementById("model-bar-chart"), {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Tokens/s",
                data: tps,
                backgroundColor: "#00e676",
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#e0e0e0" } },
                title: { display: true, text: "Avg Tokens/Second", color: "#e0e0e0" },
            },
            scales: {
                x: { ticks: { color: "#9e9e9e" }, grid: { color: "#333" } },
                y: { ticks: { color: "#9e9e9e" }, grid: { color: "#333" } },
            },
        },
    });
}

async function loadCluster() {
    try {
        const res = await fetch(`${API}/api/live/cluster`);
        const data = await res.json();
        const item = Array.isArray(data) ? data[0] : data;
        if (!item) return;

        document.getElementById("cluster-total").textContent = item.nodes_total ?? "--";
        document.getElementById("cluster-online").textContent = item.nodes_online ?? "--";
        document.getElementById("cluster-vram").textContent =
            item.vram_total_gb != null ? `${item.vram_total_gb.toFixed(1)} GB` : "--";

        renderClusterNodes(item);
        renderClusterPie(item);
    } catch (e) {
        console.error("Failed to load cluster metrics", e);
    }
}

function renderClusterNodes(item) {
    const container = document.getElementById("cluster-nodes");
    const nodes = item.nodes || [];
    if (!nodes.length) { container.innerHTML = ""; return; }

    let html = "<table class='cluster-table'><thead><tr>" +
        "<th>Node</th><th>Status</th><th>Model</th><th>VRAM Used</th><th>VRAM %</th>" +
        "</tr></thead><tbody>";
    for (const n of nodes) {
        const statusClass = (n.status || "").toLowerCase() === "online" ? "online" : "offline";
        html += `<tr>` +
            `<td>${n.node_name || n.node_id || "--"}</td>` +
            `<td><span class="status-badge ${statusClass}">${n.status || "--"}</span></td>` +
            `<td>${n.model || "--"}</td>` +
            `<td>${n.gpu_memory_gb != null ? n.gpu_memory_gb.toFixed(1) + " GB" : "--"}</td>` +
            `<td>${n.gpu_memory_used_percent != null ? n.gpu_memory_used_percent.toFixed(0) + "%" : "--"}</td>` +
            `</tr>`;
    }
    html += "</tbody></table>";
    container.innerHTML = html;
}

function renderClusterPie(item) {
    const online = item.nodes_online || 0;
    const total = item.nodes_total || 0;
    const offline = total - online;

    if (charts.clusterPie) charts.clusterPie.destroy();
    charts.clusterPie = new Chart(document.getElementById("cluster-pie-chart"), {
        type: "pie",
        data: {
            labels: ["Online", "Offline"],
            datasets: [{
                data: [online, Math.max(offline, 0)],
                backgroundColor: ["#00e676", "#ff5252"],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#e0e0e0" } },
                title: { display: true, text: "Cluster Node Status", color: "#e0e0e0" },
            },
        },
    });
}

function pushHistory(key, value) {
    if (value == null) return;
    const now = new Date().toLocaleTimeString();
    const store = historyData[key];
    store.labels.push(now);
    store.data.push(value);
    if (store.labels.length > MAX_HISTORY) {
        store.labels.shift();
        store.data.shift();
    }
    updateCharts();
}

function updateCharts() {
    updateLineChart("cpu", historyData.cpu, "CPU %", "#00e676");
    updateLineChart("mem", historyData.mem, "Memory %", "#2979ff");
    updateLineChart("gpuUtil", historyData.gpuUtil, "GPU Util %", "#ff9100");
    updateLineChart("gpuMem", historyData.gpuMem, "GPU Mem (MB)", "#b388ff");
}

function updateLineChart(key, store, label, color) {
    if (store.labels.length < 2) return;
    if (!charts[key]) {
        charts[key] = new Chart(document.getElementById(`${key}-chart`), {
            type: "line",
            data: {
                labels: store.labels,
                datasets: [{
                    label,
                    data: store.data,
                    borderColor: color,
                    backgroundColor: color + "20",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: { labels: { color: "#e0e0e0", font: { size: 11 } } },
                    title: { display: true, text: label, color: "#e0e0e0" },
                },
                scales: {
                    x: { ticks: { color: "#9e9e9e", maxTicksLimit: 8 }, grid: { color: "#333" } },
                    y: { ticks: { color: "#9e9e9e" }, grid: { color: "#333" } },
                },
            },
        });
    } else {
        charts[key].data.labels = store.labels;
        charts[key].data.datasets[0].data = store.data;
        charts[key].update("none");
    }
}

document.getElementById("node-select").addEventListener("change", refreshAll);
document.getElementById("date-filter").addEventListener("change", loadDayHistory);

async function loadDayHistory() {
    const date = document.getElementById("date-filter").value;
    if (!date) return;
    try {
        const url = selectedNode()
            ? `${API}/api/history/day?date=${date}&node_id=${encodeURIComponent(selectedNode())}`
            : `${API}/api/history/day?date=${date}`;
        const res = await fetch(url);
        const data = await res.json();
        console.log("Day history:", data);
    } catch (e) {
        console.error("Failed to load day history", e);
    }
}

async function refreshAll() {
    await Promise.all([loadSystem(), loadGPU(), loadModels(), loadCluster()]);
}

async function init() {
    document.getElementById("date-filter").valueAsDate = new Date();
    await loadConfig();
    await loadNodes();
    await refreshAll();
    setInterval(refreshAll, REFRESH_MS);
}

init();
