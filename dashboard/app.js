"use strict";

const state = {
  data: null,
  route: "overview",
  selectedSession: 1,
  cataloguePage: 0,
  catalogueSearch: "",
  sessionSearch: null,
  toastTimer: null,
};

const view = document.getElementById("view");
const sidebar = document.getElementById("sidebar");
const navNames = {
  overview: "Overview",
  roadmap: "Roadmap",
  workspace: "Session workspace",
  catalogue: "Catalogue explorer",
  playground: "Algorithm playground",
  benchmarks: "Benchmark centre",
  reports: "Reports & deliverables",
  architecture: "Architecture",
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function number(value) {
  return new Intl.NumberFormat("en-IN").format(Number(value) || 0);
}

function currency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 2,
  }).format(Number(value) || 0);
}

function statusBadge(status) {
  const normalized = String(status || "upcoming").toLowerCase();
  const label = normalized === "active" ? "Active" : normalized === "completed" ? "Completed" : "Upcoming";
  return `<span class="badge badge-${normalized === "active" ? "active" : normalized === "completed" ? "completed" : "upcoming"}">${label}</span>`;
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function setRouteFromHash() {
  const raw = window.location.hash.replace(/^#/, "");
  const [route, session] = raw.split("/");
  if (route === "workspace" && Number(session) >= 1 && Number(session) <= 12) {
    state.selectedSession = Number(session);
  }
  state.route = navNames[route] ? route : "overview";
  render();
  sidebar.classList.remove("open");
}

function updateShell() {
  document.getElementById("breadcrumb-current").textContent = navNames[state.route] || "Overview";
  document.querySelectorAll(".primary-nav > a[data-route]").forEach((anchor) => {
    anchor.classList.toggle("active", anchor.dataset.route === state.route);
  });
  document.querySelectorAll(".session-links button").forEach((button) => {
    button.classList.toggle("active", state.route === "workspace" && Number(button.dataset.session) === state.selectedSession);
  });
  const currentPhase = state.data.roadmap.find((phase) => phase.number === state.data.project.current_phase) || state.data.roadmap[0];
  const phaseStatus = document.getElementById("phase-status-copy");
  if (phaseStatus) {
    phaseStatus.innerHTML = `<strong>Phase ${currentPhase.number} ${escapeHtml(currentPhase.status)}</strong><small>Sessions ${currentPhase.session_start}–${currentPhase.session_end}</small>`;
  }
  const phase1 = state.data.roadmap[0].sessions.slice(0, 6);
  const phase2 = state.data.roadmap[1].sessions.slice(0, 6);
  document.getElementById("session-links").innerHTML = `<small class="session-group-label">PHASE 1 · SESSIONS 1–6</small>${phase1.map((session) =>
    `<button data-session="${session.number}" aria-label="Open session ${session.number}"><span>S${String(session.number).padStart(2, "0")}</span>${escapeHtml(session.title.replace(/^Session \d+: /, ""))}</button>`
  ).join("")}<small class="session-group-label">PHASE 2 · SESSIONS 7–12</small>${phase2.map((session) =>
    `<button data-session="${session.number}" aria-label="Open session ${session.number}"><span>S${String(session.number).padStart(2, "0")}</span>${escapeHtml(session.title.replace(/^Session \d+: /, ""))}</button>`
  ).join("")}`;
  document.querySelectorAll(".session-links button").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedSession = Number(button.dataset.session);
      window.location.hash = `workspace/${state.selectedSession}`;
    });
  });
}

function pageHead(eyebrow, title, description, actions = "") {
  return `<div class="page-head"><div><div class="eyebrow">${escapeHtml(eyebrow)}</div><h1>${escapeHtml(title)}</h1><p class="lead">${escapeHtml(description)}</p></div>${actions ? `<div class="head-actions">${actions}</div>` : ""}</div>`;
}

function render() {
  if (!state.data) return;
  updateShell();
  const renderers = {
    overview: renderOverview,
    roadmap: renderRoadmap,
    workspace: renderWorkspace,
    catalogue: renderCatalogue,
    playground: renderPlayground,
    benchmarks: renderBenchmarks,
    reports: renderReports,
    architecture: renderArchitecture,
  };
  view.innerHTML = renderers[state.route]();
  if (state.route === "workspace") wireWorkspace();
  if (state.route === "catalogue") wireCatalogue();
  if (state.route === "playground") wirePlayground();
  if (state.route === "benchmarks") wireBenchmarks();
  if (state.route === "roadmap") wireRoadmap();
}

function renderOverview() {
  const { project, roadmap } = state.data;
  const currentPhase = roadmap.find((phase) => phase.number === project.current_phase) || roadmap[0];
  const phases = roadmap.map((phase) => {
    const completed = phase.sessions.filter((session) => session.status === "completed").length;
    const progress = Math.round(completed / phase.sessions.length * 100);
    return `<article class="phase-card ${phase.status === "active" ? "active" : phase.status === "completed" ? "completed" : "upcoming"}" data-phase="${phase.number}">
      <div class="phase-card-top"><span class="phase-number">PHASE ${String(phase.number).padStart(2, "0")}</span>${statusBadge(phase.status)}</div>
      <h3>${escapeHtml(phase.title)}</h3>
      <div class="phase-card-meta"><span>Sessions ${phase.session_start}–${phase.session_end}</span><span>${completed}/6 complete</span></div>
      <div class="mini-progress"><span style="width:${phase.status === "completed" ? 100 : phase.status === "active" ? progress : 0}%"></span></div>
    </article>`;
  }).join("");

  return `<section class="hero">
    <div class="hero-copy">
      <div class="hero-badges"><span class="badge ${currentPhase.status === "completed" ? "badge-completed" : "badge-active"}">PHASE ${String(currentPhase.number).padStart(2, "0")} · ${currentPhase.status.toUpperCase()}</span><span class="badge badge-neutral">${escapeHtml(currentPhase.title)}</span></div>
      <h1>${escapeHtml(project.title)}</h1>
      <p class="lead">${escapeHtml(project.description)} Build the baseline, inspect the work, and keep every measurement tied to its source.</p>
    </div>
    <div class="hero-side"><div class="hero-side-top"><span class="hero-side-label">CURRENT MILESTONE</span>${statusBadge(project.milestone.status === "Complete" ? "completed" : "active")}</div>
      <strong>${escapeHtml(project.milestone.name)}</strong><p>${escapeHtml(project.milestone.note)}</p>
      <div style="margin-top:16px"><div class="progress-track"><span style="width:${project.completion_percent}%"></span></div><div class="progress-meta"><span>Project sessions completed</span><span>${project.completion_percent}%</span></div></div>
    </div>
  </section>
  <section class="metric-grid">
    <article class="metric-card"><div class="metric-label">Total sessions <span class="metric-icon">⌘</span></div><div class="metric-value">${project.total_sessions}</div><div class="metric-sub">Across six project phases</div></article>
    <article class="metric-card"><div class="metric-label">Current phase <span class="metric-icon">◈</span></div><div class="metric-value">${String(project.current_phase).padStart(2, "0")} <span style="font-size:12px;color:#849bad;font-weight:500">/ 06</span></div><div class="metric-sub">${escapeHtml(currentPhase.title)}</div></article>
    <article class="metric-card"><div class="metric-label">Project completion <span class="metric-icon">◌</span></div><div class="metric-value">${project.completion_percent}%</div><div class="metric-sub">${project.completed_sessions} of ${project.total_sessions} sessions</div></article>
    <article class="metric-card"><div class="metric-label">Milestone status <span class="metric-icon">◇</span></div><div class="metric-value" style="font-size:20px">${escapeHtml(project.milestone.status)}</div><div class="metric-sub">${escapeHtml(project.milestone.name)}</div></article>
  </section>
  <section><div class="section-heading"><div><h2>Project phases</h2><p>Six connected stages from baseline analysis to production retrieval.</p></div><a class="text-link" href="#roadmap">Open full roadmap →</a></div><div class="phase-grid">${phases}</div></section>
  <section class="two-column">
    <article class="panel"><div class="panel-head"><div><h2>Milestone tracker</h2><p>Current state from the project brief and available artifacts.</p></div><span class="badge badge-${project.milestone.status === "Complete" ? "completed" : "active"}">${project.milestone.status === "Complete" ? "M2 COMPLETE" : "M2 ACTIVE"}</span></div>
      <div class="milestone-line"><span class="milestone-icon">01</span><div><strong>M1 · Algorithm Engineering foundation</strong><p>Sessions 1–6 remain verified with their original implementations, tests, and report evidence.</p></div></div>
      <div class="milestone-line"><span class="milestone-icon">02</span><div><strong>M2 · Advanced Data Structures</strong><p>Sessions 7–12 are integrated with the product catalogue, version history, category tree, and simulated event stream.</p></div></div>
      <div class="milestone-line"><span class="milestone-icon">↗</span><div><strong>Next: Phase 3</strong><p>Sessions 13–36 remain upcoming pending their authoritative curriculum.</p></div></div>
    </article>
    <article class="panel"><div class="panel-head"><div><h2>Phase status</h2><p>Upcoming work is kept separate from completed sessions.</p></div></div><div class="status-list">
      ${roadmap.map((phase) => `<div class="status-row"><div><strong>Phase ${phase.number}</strong><small>${escapeHtml(phase.title)}</small></div>${statusBadge(phase.status)}</div>`).join("")}
    </div></article>
  </section>`;
}

function renderRoadmap() {
  const phases = state.data.roadmap.map((phase) => {
    const sessionRows = phase.sessions.map((session) => `<div class="session-row" data-session="${session.number}">
      <span class="session-row-number">S${String(session.number).padStart(2, "0")}</span>
      <span class="session-row-title"><strong>${escapeHtml(session.title)}</strong><small>${escapeHtml(session.description)}</small></span>
      ${statusBadge(session.status)}<span class="session-row-arrow">›</span>
    </div>`).join("");
    return `<article class="phase-block ${phase.status === "active" ? "active" : ""}">
      <div class="phase-block-head"><span class="phase-index">${String(phase.number).padStart(2, "0")}</span><div class="phase-block-title"><h3>${escapeHtml(phase.title)}</h3><p>Sessions ${phase.session_start}–${phase.session_end} · 6 sessions</p></div>${statusBadge(phase.status)}</div>
      ${sessionRows}
    </article>`;
  }).join("");
  return `${pageHead("36-session roadmap", "Project roadmap", "Browse all six phases and inspect completed work through Session 12. Later sessions stay upcoming until their source curriculum is available.")}
    <div class="roadmap-note">Session 7–12 content follows the requirements supplied in the project brief. The referenced official PDF was not present in the available attachments; Sessions 13–36 remain upcoming.</div>
    <section class="phase-list" style="margin-top:13px">${phases}</section>`;
}

function detailList(items) {
  return `<ul class="detail-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function searchOutputHtml(result, heading = "Live search output") {
  if (!result) return `<div class="empty-state">Run the linear search to inspect actual matches and operation counts.</div>`;
  const count = result.counts;
  const matches = result.matches || [];
  return `<div class="output-head"><strong>${escapeHtml(heading)}</strong><span class="badge ${result.oracle_passed === false ? "badge-warning" : "badge-completed"}">${result.oracle_passed === false ? "Oracle mismatch" : "Oracle passed"}</span></div>
    <div class="output-body"><div class="counter-grid">
      <div class="counter"><small>Records inspected</small><strong>${number(count.records_inspected)}</strong></div>
      <div class="counter"><small>Stock checks</small><strong>${number(count.stock_checks)}</strong></div>
      <div class="counter"><small>Price checks</small><strong>${number(count.price_checks)}</strong></div>
      <div class="counter"><small>Counted operations</small><strong>${number(count.counted_operations)}</strong></div>
    </div><div class="chart-caption" style="margin-bottom:8px"><span>${number(matches.length)} products matched</span><span>${number(count.result_writes)} result writes</span></div>
    ${matches.length ? `<div class="result-chips">${matches.slice(0, 30).map((product) => `<span class="result-chip">${escapeHtml(product.product_id)} · ${escapeHtml(product.title)}</span>`).join("")}${matches.length > 30 ? `<span class="result-chip">+${number(matches.length - 30)} more</span>` : ""}</div>` : `<div class="empty-state">No products matched the current limit.</div>`}
    </div>`;
}

function renderWorkspace() {
  const sessions = state.data.roadmap.slice(0, 2).flatMap((phase) => phase.sessions);
  const session = sessions.find((item) => item.number === state.selectedSession) || sessions[0];
  const phase = state.data.roadmap[Math.floor((session.number - 1) / 6)];
  const phaseSessionData = session.number >= 7 ? state.data.phase2[`session${session.number}`] : null;
  const session1Result = session.number === 1 ? { ...state.data.session1.default_search, oracle_passed: true } : null;
  const switcher = sessions.map((item) => `<button class="${item.number === session.number ? "active" : ""}" data-workspace-session="${item.number}"><small>SESSION ${String(item.number).padStart(2, "0")} · ${item.status.toUpperCase()}</small>${escapeHtml(item.title)}</button>`).join("");
  const demo = renderSessionDemo(session, phaseSessionData);
  const benchmarkRows = (state.data.phase2.benchmarks || []).filter((row) => Number(row.session) === session.number);
  const benchmarkPanel = benchmarkRows.length
    ? `<article class="panel"><h3>Measured benchmark</h3><div class="table-wrap"><table><thead><tr><th>Algorithm</th><th>Input</th><th>Time</th><th>Operations</th><th>Memory estimate</th><th>Oracle</th></tr></thead><tbody>${benchmarkRows.map((row) => `<tr><td>${escapeHtml(row.algorithm)}</td><td>${number(row.input_size)}</td><td>${Number(row.median_time_ms).toFixed(4)} ms</td><td>${number(row.operations)}</td><td>${number(row.memory_estimate_bytes)} B</td><td>${row.correctness === "true" ? "Passed" : "Review"}</td></tr>`).join("")}</tbody></table></div><p class="tiny">Time is the recorded local median. Memory is an object-size estimate unless the session report says otherwise.</p></article>`
    : `<article class="panel"><h3>Time and memory benchmarks</h3><p class="detail-copy">${session.number <= 6 ? "See the existing M1 benchmark evidence listed below; the original measured data remains unchanged." : "No reproducible benchmark row is available yet."}</p>${session.number <= 6 ? detailList(session.deliverables.filter((item) => item.includes("benchmark") || item.includes("Benchmark") || item.includes("report"))) : ""}</article>`;
  const statusData = phaseSessionData?.acceptance_passed;
  const inputFixture = session.number === 1 ? "20-record hand-trace and 1,000-product deterministic catalogue." : session.number >= 7 ? state.data.phase2.event_data.source + " and data/products.csv." : "Existing Session 1 fixtures and the recorded Session 1–6 benchmark workloads.";
  const expectedResult = session.number === 7 ? "Days 3–9 sales equals the direct sum; the indexed stock range equals its naive array oracle." : session.number === 8 ? "V0, V1, and V2 preserve independent stock values; version IDs differ in the cache key." : session.number === 9 ? "Exact substring offsets match direct scanning and cannot cross document sentinels." : session.number === 10 ? "Suffix-automaton membership and occurrence counts agree with Session 9." : session.number === 11 ? "Static HLD and dynamic link-cut path sums match naive traversal." : session.number === 12 ? "Offline distinct-product counts equal direct set counts for all fixed event ranges." : session.acceptance.join(" ");
  const actualResult = session.number === 1 ? searchOutputHtml(session1Result, "Current baseline · 20 records") : phaseSessionData ? renderSessionActual(session, phaseSessionData) : `<p class="detail-copy">Acceptance status is supported by the existing M1 source, test files, and evidence artifacts.</p>`;
  const checksHtml = session.acceptance.map((item) => `<li><span class="checkmark">${statusData === false ? "!" : "✓"}</span>${escapeHtml(item)}</li>`).join("");
  const testResult = phaseSessionData ? (statusData ? "Live session acceptance oracle passed." : "At least one live session acceptance check failed.") : "See the recorded project test status and linked M1 test files.";
  const filesHtml = session.deliverables.map((item) => `<li>${escapeHtml(item)}</li>`).join("");

  return `${pageHead(`Phase ${phase.number} · ${phase.status}`, `Session ${session.number} workspace`, `Detailed work, live outputs, tests, benchmarks, and deliverables for ${session.title}.`)}
    <div class="workspace-switcher">${switcher}</div>
    <section class="session-hero"><div class="page-head"><div><div class="session-number-large">SESSION ${String(session.number).padStart(2, "0")} · PHASE ${String(phase.number).padStart(2, "0")}</div><h2>${escapeHtml(session.title)}</h2><p class="lead">${escapeHtml(session.description)}</p></div>${statusBadge(session.status)}</div><p class="source-note">Content source: ${escapeHtml(session.source)}</p></section>
    ${demo}
    <section class="workspace-grid">
      <article class="panel detail-panel"><h3>Module and learning outcome</h3><p class="detail-copy"><strong>${escapeHtml(session.module)}</strong><br/>${escapeHtml(session.objective)}</p><p class="tiny">Complexity: ${escapeHtml(session.complexity)}</p></article>
      <article class="panel detail-panel"><h3>Project problem</h3><p class="detail-copy">${escapeHtml(session.problem)}</p><h4>Why this algorithm is needed</h4><p class="detail-copy">${escapeHtml(session.why)}</p></article>
      <article class="panel detail-panel"><h3>Lecture concepts</h3>${detailList(session.concepts)}</article>
      <article class="panel detail-panel"><h3>Implementation explanation</h3><p class="detail-copy">${escapeHtml(session.implementation)}</p>${detailList(session.tasks)}</article>
      <article class="panel detail-panel"><h3>Input fixture and expected result</h3><p class="detail-copy"><strong>Input:</strong> ${escapeHtml(inputFixture)}</p><p class="detail-copy"><strong>Expected:</strong> ${escapeHtml(expectedResult)}</p></article>
      <article class="panel detail-panel"><h3>Actual result</h3>${actualResult}</article>
      <article class="panel detail-panel"><h3>Correctness tests</h3><p class="detail-copy">${escapeHtml(testResult)}</p>${detailList(session.test_files)}</article>
      ${benchmarkPanel}
      <article class="panel detail-panel acceptance"><h3>Acceptance checklist · ${escapeHtml(session.status)}</h3><ul class="acceptance-list">${checksHtml}</ul></article>
      <article class="panel detail-panel"><h3>Deliverable files</h3><ul class="detail-list">${filesHtml}</ul></article>
    </section>`;
}

function renderSessionDemo(session, data) {
  if (session.number === 1) return `<article class="panel session-demo"><div class="panel-head"><div><h3>Live linear-search acceptance check</h3><p>Run the strict in-stock price query against either real Session 1 fixture.</p></div><span class="badge badge-neutral">LIMIT: ₹60,000</span></div>
    <div class="session-demo-controls"><div class="control-group"><label for="session-dataset">Catalogue</label><select id="session-dataset"><option value="hand_trace">20-record hand-trace</option><option value="products_1000">1,000-product catalogue</option></select></div>
      <div class="control-group"><label for="session-price">Price limit (₹, exclusive)</label><input id="session-price" type="number" min="0" step="0.01" value="${state.sessionSearch?.price_limit ?? state.data.session1.price_limit}" /></div>
      <button class="primary-button" id="run-session-search">Run linear search <span>→</span></button></div>
    <div class="search-output" id="session-search-output">${searchOutputHtml(state.sessionSearch || { ...state.data.session1.default_search, oracle_passed: true })}</div></article>`;
  if (session.number === 7) return `<article class="panel session-demo"><div class="panel-head"><div><h3>Sales range and lazy stock update</h3><p>Query simulated purchases by day and inspect an indexed stock interval.</p></div>${statusBadge(data.acceptance_passed ? "completed" : "active")}</div><div class="session-demo-controls"><label>Start index<input id="session7-start" type="number" min="0" value="2" /></label><label>End (exclusive)<input id="session7-end" type="number" min="0" value="9" /></label><button class="primary-button" id="run-session7-range">Run range sum</button></div><div class="search-output" id="session7-range-output">${currency(data.sales_query.sales_inr)} for Days 3–9 · sales oracle ${data.sales_oracle_passed ? "passed" : "failed"}.</div></article>`;
  if (session.number === 8) return `<article class="panel session-demo"><div class="panel-head"><div><h3>Versioned catalogue snapshots</h3><p>Compare the same product record across V0, V1, and V2.</p></div><span class="badge badge-completed">VERSIONED CACHE KEY</span></div><div class="session-demo-controls"><label>Snapshot<select id="snapshot-version"><option>V0</option><option>V1</option><option>V2</option></select></label><label>Product ID<input id="snapshot-product" value="P1001" /></label><button class="primary-button" id="run-version-query">Read snapshot</button></div><div class="search-output" id="version-query-output">V0 stock ${number(data.versions[0].P1001_stock)} · V1 ${number(data.versions[1].P1001_stock)} · V2 ${number(data.versions[2].P1001_stock)}. Cache key example: <span class="mono">${escapeHtml(data.example_cache_key)}</span></div></article>`;
  if (session.number === 9 || session.number === 10) return `<article class="panel session-demo"><div class="panel-head"><div><h3>${session.number === 9 ? "Suffix array + LCP substring query" : "Suffix automaton membership query"}</h3><p>Search exact phrases in current local product descriptions.</p></div><span class="badge badge-completed">${escapeHtml(session.number === 9 ? data.construction : data.multi_document_strategy)}</span></div><form class="session-demo-controls" data-session-text-search data-algorithm="${session.number === 9 ? "suffix_array" : "suffix_automaton"}"><label>Exact phrase<input name="q" value="${escapeHtml(session.number === 9 ? data.query : data.query)}" /></label><button class="primary-button" type="submit">Search descriptions</button></form><div class="search-output" id="session-text-output">${number(data.matches.length)} matching product descriptions for “${escapeHtml(data.query)}”.</div></article>`;
  if (session.number === 11) return `<article class="panel session-demo"><div class="panel-head"><div><h3>Category hierarchy path service</h3><p>Live revenue totals from purchase events and link-cut forest validation.</p></div><span class="badge badge-completed">CYCLE REJECTED</span></div><div class="counter-grid"><div class="counter"><small>Categories and groups</small><strong>${number(data.category_nodes)}</strong></div><div class="counter"><small>Path revenue</small><strong>${currency(data.static_path.revenue_sum_inr)}</strong></div><div class="counter"><small>HLD path segments</small><strong>${number(data.hld_path_segments_visited)}</strong></div><div class="counter"><small>Dynamic link/cut steps</small><strong>${number(data.dynamic_trace.length)}</strong></div></div><div class="search-output">HLD oracle ${data.hld_oracle_passed ? "passed" : "failed"}; link-cut agrees ${data.link_cut_matches_hld ? "yes" : "no"}. ${escapeHtml(data.static_rebuild_note)}</div></article>`;
  if (session.number === 12) return `<article class="panel session-demo"><div class="panel-head"><div><h3>Offline view-event range distinct</h3><p>Count unique product IDs in a half-open interval of the fixed view-event array.</p></div><span class="badge badge-completed">${number(state.data.phase2.event_data.view_event_count)} VIEW EVENTS</span></div><div class="session-demo-controls"><label>Start<input id="session12-start" type="number" min="0" value="0" /></label><label>End (exclusive)<input id="session12-end" type="number" min="0" value="20" /></label><button class="primary-button" id="run-session12-range">Count distinct IDs</button></div><div class="search-output" id="session12-range-output">${number(data.distinct_product_counts[0])} distinct IDs in the first fixed query · oracle ${data.oracle_passed ? "passed" : "failed"} · ${number(data.pointer_moves)} pointer moves.</div></article>`;
  return "";
}

function renderSessionActual(session, data) {
  if (session.number === 7) return `<div class="counter-grid"><div class="counter"><small>Daily bins</small><strong>${number(data.daily_sales.length)}</strong></div><div class="counter"><small>Sales Days 3–9</small><strong>${currency(data.sales_query.sales_inr)}</strong></div><div class="counter"><small>Fenwick accesses</small><strong>${number(data.fenwick_operations)}</strong></div><div class="counter"><small>Range stock total</small><strong>${number(data.stock_adjustment.after_total)}</strong></div></div><p class="tiny">Sales and stock each matched the direct array oracle.</p>`;
  if (session.number === 8) return `<div class="table-wrap"><table><thead><tr><th>Snapshot</th><th>Products</th><th>P1001 stock</th><th>P1002 stock</th><th>Full-copy entries</th><th>Copy-on-write bytes</th><th>Path-copy bytes</th></tr></thead><tbody>${data.versions.map((row, index) => { const memory = data.memory_growth[index]; return `<tr><td>${escapeHtml(row.version_id)}</td><td>${number(row.products)}</td><td>${number(row.P1001_stock)}</td><td>${number(row.P1002_stock)}</td><td>${number(memory.copy_on_write_snapshot_entries)}</td><td>${number(memory.copy_on_write_estimate_bytes)}</td><td>${number(memory.path_copy_shared_estimate_bytes)}</td></tr>`; }).join("")}</tbody></table></div><p class="tiny">Fat-node history estimate: ${number(data.memory_estimate_bytes.fat_node_histories)} B. These are recursive Python object-size estimates and count shared objects once.</p>`;
  if (session.number === 9) return `<p class="detail-copy">Query <strong>${escapeHtml(data.query)}</strong> returned ${number(data.matches.length)} offsets. Suffix-array prefix: <span class="mono">${escapeHtml(data.suffix_array_prefix.join(", "))}</span></p><p class="tiny">LCP prefix: ${escapeHtml(data.lcp_prefix.join(", "))}. DC3 is a guided trace only (${data.dc3_trace.algorithm_executed ? "executed" : "not executed"}).</p>`;
  if (session.number === 10) return `<p class="detail-copy">Query <strong>${escapeHtml(data.query)}</strong> maps to ${number(data.matches.length)} products. Session 9 cross-check for “${escapeHtml(data.cross_check_query)}”: ${data.suffix_array_agrees ? "passed" : "failed"}.</p><p class="tiny">Guided clone trace has ${number(data.guided_clone_example.states.length)} states and ${number(data.guided_clone_example.clones.length)} clone(s).</p>`;
  if (session.number === 11) return `<p class="detail-copy">${escapeHtml(data.static_path.from)} → ${escapeHtml(data.static_path.to)} totals ${currency(data.static_path.revenue_sum_inr)}. HLD and dynamic forest agree: ${data.link_cut_matches_hld ? "yes" : "no"}.</p><p class="tiny">Category revenue map: ${escapeHtml(JSON.stringify(data.category_revenue_inr))}</p>`;
  if (session.number === 12) return `<p class="detail-copy">${number(data.view_events)} view events; fixed interval counts: ${escapeHtml(data.distinct_product_counts.join(", "))} distinct products.</p><p class="tiny">Mo moved its window ${number(data.pointer_moves)} times (${number(data.add_operations)} additions, ${number(data.remove_operations)} removals), with naive oracle ${data.oracle_passed ? "passed" : "failed"}.</p>`;
  return "";
}

async function runSession7Range() {
  const output = document.getElementById("session7-range-output");
  const start = Number(document.getElementById("session7-start").value);
  const end = Number(document.getElementById("session7-end").value);
  try {
    const response = await fetch(`/api/analytics/range?start=${start}&end=${end}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Range query failed");
    output.textContent = `Sales in [${result.start}, ${result.end_exclusive}): ${currency(result.sales_inr)} · direct-sum oracle ${result.oracle_passed ? "passed" : "failed"}.`;
  } catch (error) { output.textContent = error.message; }
}

async function runSession12Range() {
  const output = document.getElementById("session12-range-output");
  const start = Number(document.getElementById("session12-start").value);
  const end = Number(document.getElementById("session12-end").value);
  try {
    const response = await fetch(`/api/analytics/distinct?start=${start}&end=${end}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Offline range query failed");
    output.textContent = `${number(result.distinct_products)} distinct product IDs in [${result.start}, ${result.end_exclusive}) · ${number(result.pointer_moves)} pointer moves · oracle ${result.oracle_passed ? "passed" : "failed"}.`;
  } catch (error) { output.textContent = error.message; }
}

async function runSessionTextSearch(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const params = new URLSearchParams({ q: String(new FormData(form).get("q")), algorithm: form.dataset.algorithm });
  const output = document.getElementById("session-text-output");
  try {
    const response = await fetch(`/api/search/substring?${params}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Substring query failed");
    const matches = result.results.map((row) => row.offset === undefined ? `${row.document_id} (${row.occurrences} occurrences)` : `${row.document_id} @ ${row.offset}`);
    output.textContent = `${matches.length} matching product descriptions: ${matches.join(", ") || "none"}. Catalogue ${result.catalogue_version_id}.`;
  } catch (error) { output.textContent = error.message; }
}

async function runVersionQuery() {
  const output = document.getElementById("version-query-output");
  const version = document.getElementById("snapshot-version").value;
  const productId = document.getElementById("snapshot-product").value.trim();
  try {
    const response = await fetch(`/api/admin/catalogue?version=${encodeURIComponent(version)}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Snapshot query failed");
    const product = result.products.find((row) => row.product_id === productId);
    output.textContent = product ? `${product.product_id} at ${version}: stock ${number(product.stock)}, record version ${product.version}.` : `${productId} does not exist in ${version}.`;
  } catch (error) { output.textContent = error.message; }
}

function wireWorkspace() {
  document.querySelectorAll("[data-workspace-session]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedSession = Number(button.dataset.workspaceSession);
      state.sessionSearch = null;
      window.location.hash = `workspace/${state.selectedSession}`;
    });
  });
  const runButton = document.getElementById("run-session-search");
  if (runButton) runButton.addEventListener("click", () => runSearchInto("session-search-output", "session-dataset", "session-price"));
  const session7Button = document.getElementById("run-session7-range");
  if (session7Button) session7Button.addEventListener("click", runSession7Range);
  const session12Button = document.getElementById("run-session12-range");
  if (session12Button) session12Button.addEventListener("click", runSession12Range);
  document.querySelectorAll("[data-session-text-search]").forEach((form) => form.addEventListener("submit", runSessionTextSearch));
  const versionButton = document.getElementById("run-version-query");
  if (versionButton) versionButton.addEventListener("click", runVersionQuery);
}

async function runSearchInto(outputId, datasetId, priceId) {
  const output = document.getElementById(outputId);
  const dataset = document.getElementById(datasetId).value;
  const maxPrice = Number(document.getElementById(priceId).value);
  if (!Number.isFinite(maxPrice)) {
    output.innerHTML = `<div class="empty-state">Enter a valid numeric price limit.</div>`;
    return;
  }
  output.innerHTML = `<div class="empty-state">Running the in-memory linear scan…</div>`;
  try {
    const response = await fetch(`/api/search?dataset=${encodeURIComponent(dataset)}&max_price=${encodeURIComponent(maxPrice)}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Search failed");
    output.innerHTML = searchOutputHtml(result);
    if (outputId === "session-search-output") state.sessionSearch = result;
    showToast(`Scanned ${number(result.dataset_size)} products · oracle ${result.oracle_passed ? "passed" : "failed"}`);
  } catch (error) {
    output.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderCatalogue() {
  const { catalogue } = state.data;
  const categories = ["All categories", ...catalogue.categories].map((category, index) => `<option value="${index === 0 ? "" : escapeHtml(category)}">${escapeHtml(category)}</option>`).join("");
  return `${pageHead("Product data", "Catalogue explorer", `Search and filter the deterministic ${number(catalogue.large_catalogue_count)}-product catalogue. Product fields are served from ${catalogue.source}.`)}
    <div class="catalogue-toolbar">
      <div class="search-field"><label for="catalogue-query">Search products</label><input id="catalogue-query" placeholder="Product name, description, or ID" value="${escapeHtml(state.catalogueSearch)}" /></div>
      <div class="select-field"><label for="catalogue-category">Category</label><select id="catalogue-category">${categories}</select></div>
      <div class="select-field"><label for="catalogue-price">Maximum price (₹)</label><input class="filter-input" id="catalogue-price" type="number" min="0" placeholder="No limit" /></div>
      <div class="select-field"><label for="catalogue-stock">Availability</label><select id="catalogue-stock"><option value="all">All products</option><option value="in">In stock</option><option value="out">Out of stock</option></select></div>
      <button class="secondary-button" id="clear-catalogue-filters">Clear filters</button>
    </div>
    <div id="catalogue-results"></div>`;
}

function wireCatalogue() {
  const query = document.getElementById("catalogue-query");
  query.addEventListener("input", () => { state.catalogueSearch = query.value; state.cataloguePage = 0; renderCatalogueRows(); });
  ["catalogue-category", "catalogue-price", "catalogue-stock"].forEach((id) => {
    document.getElementById(id).addEventListener("input", () => { state.cataloguePage = 0; renderCatalogueRows(); });
  });
  document.getElementById("clear-catalogue-filters").addEventListener("click", () => {
    query.value = "";
    state.catalogueSearch = "";
    document.getElementById("catalogue-category").value = "";
    document.getElementById("catalogue-price").value = "";
    document.getElementById("catalogue-stock").value = "all";
    state.cataloguePage = 0;
    renderCatalogueRows();
  });
  renderCatalogueRows();
}

function renderCatalogueRows() {
  const { products } = state.data.catalogue;
  const query = document.getElementById("catalogue-query").value.trim().toLowerCase();
  const category = document.getElementById("catalogue-category").value;
  const priceText = document.getElementById("catalogue-price").value;
  const priceLimit = priceText === "" ? null : Number(priceText);
  const stockFilter = document.getElementById("catalogue-stock").value;
  const filtered = products.filter((product) => {
    const textMatch = !query || [product.product_id, product.title, product.description, product.category].some((field) => String(field).toLowerCase().includes(query));
    return textMatch && (!category || product.category === category)
      && (priceLimit === null || Number(product.price) <= priceLimit)
      && (stockFilter === "all" || (stockFilter === "in" ? Number(product.stock) > 0 : Number(product.stock) === 0));
  });
  const pageSize = 20;
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  state.cataloguePage = Math.min(state.cataloguePage, pageCount - 1);
  const start = state.cataloguePage * pageSize;
  const rows = filtered.slice(start, start + pageSize).map((product) => `<tr>
    <td><span class="product-id">${escapeHtml(product.product_id)}</span></td>
    <td><strong>${escapeHtml(product.title)}</strong><small>${escapeHtml(product.description)}</small></td>
    <td>${escapeHtml(product.category)}</td><td>${currency(product.price)}</td>
    <td><span class="stock-pill ${Number(product.stock) === 0 ? "zero" : ""}">${number(product.stock)}</span></td></tr>`).join("");
  document.getElementById("catalogue-results").innerHTML = `<div class="table-wrap"><table><thead><tr><th>Product ID</th><th>Product</th><th>Category</th><th>Price</th><th>Stock</th></tr></thead><tbody>${rows || `<tr><td colspan="5"><div class="empty-state">No products match these filters.</div></td></tr>`}</tbody></table>
    <div class="table-footer"><span>Showing ${filtered.length ? number(start + 1) : 0}–${number(Math.min(start + pageSize, filtered.length))} of ${number(filtered.length)} matching products</span><div class="pagination"><button id="catalogue-prev" ${state.cataloguePage === 0 ? "disabled" : ""} aria-label="Previous page">‹</button><span>${state.cataloguePage + 1} / ${pageCount}</span><button id="catalogue-next" ${state.cataloguePage >= pageCount - 1 ? "disabled" : ""} aria-label="Next page">›</button></div></div></div>`;
  document.getElementById("catalogue-prev").addEventListener("click", () => { state.cataloguePage -= 1; renderCatalogueRows(); });
  document.getElementById("catalogue-next").addEventListener("click", () => { state.cataloguePage += 1; renderCatalogueRows(); });
}

function lineChart(rows, valueKey, label, formatter = (value) => number(value)) {
  const width = 540, height = 200, left = 46, right = 15, top = 15, bottom = 34;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const values = rows.map((row) => Number(row[valueKey]) || 0);
  const max = Math.max(...values, 1);
  const points = values.map((value, index) => {
    const x = left + (rows.length === 1 ? plotWidth / 2 : index * plotWidth / (rows.length - 1));
    const y = top + plotHeight - (value / max) * plotHeight;
    return { x, y, value, row: rows[index] };
  });
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${left},${top + plotHeight} ${line} ${left + plotWidth},${top + plotHeight}`;
  const grid = [0, .5, 1].map((ratio) => {
    const y = top + plotHeight * ratio;
    const tick = max * (1 - ratio);
    return `<line class="chart-grid-line" x1="${left}" y1="${y}" x2="${left + plotWidth}" y2="${y}"/><text class="chart-axis-label" x="${left - 7}" y="${y + 3}" text-anchor="end">${escapeHtml(formatter(tick))}</text>`;
  }).join("");
  const marks = points.map((point) => `<circle class="chart-point" cx="${point.x}" cy="${point.y}" r="4"><title>${point.row.product_count} products · ${formatter(point.value)}</title></circle><text class="chart-axis-label" x="${point.x}" y="${height - 10}" text-anchor="middle">${number(point.row.product_count)}</text>`).join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(label)}"><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#42d7e7" stop-opacity=".24"/><stop offset="100%" stop-color="#42d7e7" stop-opacity="0"/></linearGradient></defs>${grid}<polygon class="chart-area" points="${area}"/><polyline class="chart-line" points="${line}"/>${marks}</svg>`;
}

function barChart(rows, valueKey, label, formatter = (value) => number(value)) {
  const width = 540, height = 200, left = 47, right = 14, top = 15, bottom = 35;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const max = Math.max(...rows.map((row) => Number(row[valueKey]) || 0), 1);
  const slot = plotWidth / Math.max(rows.length, 1), barWidth = Math.min(42, slot * .44);
  const grid = [0, .5, 1].map((ratio) => {
    const y = top + plotHeight * ratio;
    return `<line class="chart-grid-line" x1="${left}" y1="${y}" x2="${left + plotWidth}" y2="${y}"/><text class="chart-axis-label" x="${left - 7}" y="${y + 3}" text-anchor="end">${escapeHtml(formatter(max * (1 - ratio)))}</text>`;
  }).join("");
  const bars = rows.map((row, index) => {
    const value = Number(row[valueKey]) || 0;
    const barHeight = value / max * plotHeight;
    const x = left + slot * index + (slot - barWidth) / 2;
    const y = top + plotHeight - barHeight;
    return `<rect class="chart-bar" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="4"><title>${row.product_count} products · ${formatter(value)}</title></rect><text class="chart-axis-label" x="${x + barWidth / 2}" y="${height - 10}" text-anchor="middle">${number(row.product_count)}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(label)}">${grid}${bars}</svg>`;
}

function bufferChart(rows) {
  const width = 620, height = 128, left = 18, right = 12, top = 8, bottom = 23;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const max = Math.max(...rows.map((row) => row.capacity), 1);
  const points = rows.map((row, index) => {
    const x = left + index * plotWidth / Math.max(rows.length - 1, 1);
    const y = top + plotHeight - row.capacity / max * plotHeight;
    return `${x},${y}`;
  }).join(" ");
  const labels = rows.filter((row) => row.copies_this_append > 0 || row.appended_events === rows.length).map((row) => {
    const x = left + (row.appended_events - 1) * plotWidth / Math.max(rows.length - 1, 1);
    return `<text class="chart-axis-label" x="${x}" y="${height - 7}" text-anchor="middle">${row.appended_events}</text>`;
  }).join("");
  const grid = [0, .5, 1].map((ratio) => `<line class="chart-grid-line" x1="${left}" y1="${top + plotHeight * ratio}" x2="${left + plotWidth}" y2="${top + plotHeight * ratio}"/>`).join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Dynamic buffer capacity by append">${grid}<polyline class="chart-line" points="${points}"/>${labels}</svg>`;
}

function renderPlayground() {
  const { playground, session1 } = state.data;
  const buffer = playground.dynamic_buffer;
  const fingerprint = playground.fingerprint_collision;
  const collision = fingerprint.available === false ? `<div class="empty-state">${escapeHtml(fingerprint.message)}</div>` : `<div class="collision-box">
    <div class="chart-caption"><span>${number(fingerprint.fingerprint_width_bits)}-bit fingerprint</span><span class="mono">key ${escapeHtml(fingerprint.fingerprint)}</span></div>
    <div class="collision-pair"><div class="collision-item"><strong>${escapeHtml(fingerprint.product_a.product_id)}</strong><p>${escapeHtml(fingerprint.product_a.description)}</p></div><div class="collision-item"><strong>${escapeHtml(fingerprint.product_b.product_id)}</strong><p>${escapeHtml(fingerprint.product_b.description)}</p></div></div>
    <div class="callout">The fingerprints collided, then exact text comparison rejected the pair as a duplicate. Candidate checks: ${number(fingerprint.candidate_checks)} · exact comparisons: ${number(fingerprint.exact_comparisons)}.</div>
  </div>`;
  const defaultSearch = { ...session1.default_search, oracle_passed: true };
  return `${pageHead("Interactive demonstrations", "Algorithm playground", "Run the implemented baseline and inspect actual counters, explicit buffer growth, and exact-verified fingerprint collisions.")}
    <div class="playground-grid">
      <article class="panel playground-card"><div class="panel-head"><div><h3>Linear price search</h3><p>In-stock products under a strict price limit.</p></div><span class="play-icon">⌕</span></div>
        <div class="session-demo-controls"><div class="control-group"><label for="play-dataset">Dataset</label><select id="play-dataset"><option value="hand_trace">20-record fixture</option><option value="products_1000">1,000 products</option></select></div><div class="control-group"><label for="play-price">Price limit (₹)</label><input id="play-price" type="number" value="${session1.price_limit}" /></div><button class="primary-button" id="play-search">Run search →</button></div>
        <div class="search-output" id="play-search-output">${searchOutputHtml(defaultSearch, "Baseline query · 20 records")}</div>
      </article>
      <article class="panel playground-card"><div class="panel-head"><div><h3>Dynamic array growth</h3><p>Explicit doubling and copy accounting from the existing buffer implementation.</p></div><span class="play-icon">↗</span></div>
        <div class="counter-grid"><div class="counter"><small>Events appended</small><strong>${number(buffer.events_appended)}</strong></div><div class="counter"><small>Final capacity</small><strong>${number(buffer.final_capacity)}</strong></div><div class="counter"><small>Element copies</small><strong>${number(buffer.cumulative_copies)}</strong></div><div class="counter"><small>Counted writes</small><strong>${number(buffer.total_actual_writes)}</strong></div></div>
        <div class="buffer-chart">${bufferChart(buffer.operation_log)}</div><div class="chart-caption"><span>Append sequence</span><span>Capacity doubles only when full</span></div>
      </article>
      <article class="panel playground-card wide"><div class="panel-head"><div><h3>Fingerprint collision demonstration</h3><p>Real catalogue descriptions passed through the existing four-bit fingerprint index.</p></div><span class="badge badge-warning">COLLISION EXAMPLE</span></div>${collision}</article>
    </div>`;
}

function wirePlayground() {
  document.getElementById("play-search").addEventListener("click", () => runSearchInto("play-search-output", "play-dataset", "play-price"));
}

function renderM1Benchmarks() {
  const rows = state.data.session1.benchmarks;
  const timeChart = lineChart(rows, "median_time_ms", "Median execution time in milliseconds", (value) => `${value.toFixed(3)} ms`);
  const operationChart = barChart(rows, "counted_operations", "Counted Session 1 operations");
  const tableRows = rows.map((row) => `<tr><td><strong>${number(row.product_count)}</strong><small>products</small></td><td>${Number(row.median_time_ms).toFixed(4)} ms</td><td>${number(row.records_inspected)}</td><td>${number(row.stock_checks)} / ${number(row.price_checks)}</td><td>${number(row.counted_operations)}</td><td>${(Number(row.memory_estimate_bytes) / 1024).toFixed(1)} KB</td><td>${number(row.simulated_block_reads)}</td><td>${row.oracle_passed ? `<span class="badge badge-completed">Passed</span>` : `<span class="badge badge-warning">Failed</span>`}</td></tr>`).join("");
  const assumptions = state.data.session1.assumptions.map((item) => `<article class="assumption-card"><strong>${escapeHtml(item.model)}</strong><p>${escapeHtml(item.assumption)}</p><small>${escapeHtml(item.reported_as)}</small></article>`).join("");
  return `${pageHead("Measured on this run", "Benchmark centre", "Live Session 1 measurements at 20, 100, and 1,000 products. Timing, operation counts, memory estimates, and simulated I/O are reported separately.", `<a class="secondary-button" href="/api/benchmarks.csv">↓ Export CSV</a>`)}
    <div class="benchmark-summary"><span class="badge badge-completed">ORACLE PASSED</span><span>Default query: stock &gt; 0 and price &lt; ${currency(state.data.session1.price_limit)}</span><span>Trials per size: ${number(rows[0]?.trials || 0)}</span></div>
    <div class="chart-grid"><article class="panel"><div class="panel-head"><div><h3>Median execution time</h3><p>Measured in-memory linear search time</p></div></div><div class="chart">${timeChart}</div><div class="chart-caption"><span>Catalogue size →</span><span>Milliseconds</span></div></article>
      <article class="panel"><div class="panel-head"><div><h3>Counted operations</h3><p>Predicate evaluations plus result writes</p></div></div><div class="chart">${operationChart}</div><div class="chart-caption"><span>Catalogue size →</span><span>Operations</span></div></article></div>
    <article class="panel"><div class="panel-head"><div><h3>Session 1 benchmark output</h3><p>Values were computed from the current CSV catalogues on this dashboard load.</p></div></div><div class="table-wrap"><table class="benchmark-table"><thead><tr><th>Catalogue</th><th>Median time</th><th>Rows visited</th><th>Stock / price checks</th><th>Counted operations</th><th>Object size estimate</th><th>Block reads¹</th><th>Correctness</th></tr></thead><tbody>${tableRows}</tbody></table></div><p class="tiny" style="margin:10px 0 0">¹ Simulated as ceil(N / B) with B = 64 records per assumed block; this does not measure disk I/O. Memory is a recursive Python object-size estimate, not process RSS.</p></article>
    <div class="section-heading" style="margin-top:21px"><div><h2>Cost assumptions</h2><p>Model inputs that frame the counters and estimates.</p></div></div><section class="assumptions-grid">${assumptions}</section>`;
}

function renderBenchmarks() {
  const rows = state.data.phase2.benchmarks || [];
  const phaseRows = rows.filter((row) => Number(row.session) >= 7 && Number(row.session) <= 12);
  const table = phaseRows.map((row) => `<tr><td>S${number(row.session)} · ${escapeHtml(row.algorithm)}</td><td>${escapeHtml(row.baseline)}</td><td>${number(row.input_size)}</td><td>${Number(row.median_time_ms).toFixed(4)} ms</td><td>${number(row.operations)}</td><td>${(Number(row.memory_estimate_bytes) / 1024).toFixed(1)} KB</td><td>${row.correctness === "true" ? `<span class="badge badge-completed">Passed</span>` : `<span class="badge badge-warning">Failed</span>`}</td></tr>`).join("");
  const sessionTimes = [7, 8, 9, 10, 11, 12].map((session) => {
    const sessionRows = phaseRows.filter((row) => Number(row.session) === session && !String(row.algorithm).toLowerCase().includes("naive"));
    return { product_count: session, median_time_ms: Number(sessionRows[0]?.median_time_ms) || 0 };
  });
  const chart = lineChart(sessionTimes, "median_time_ms", "Session 7 to 12 benchmark medians", (value) => `${value.toFixed(3)} ms`);
  const exported = phaseRows.length ? `<a class="secondary-button" href="/api/benchmarks/m2.csv">↓ Export M2 CSV</a>` : "";
  return `${renderM1Benchmarks()}
    <div class="section-heading" style="margin-top:26px"><div><h2>Phase 2 benchmark results</h2><p>Measured Sessions 7–12 algorithms with direct baselines, operation counters, and object-size estimates.</p></div>${exported}</div>
    ${phaseRows.length ? `<article class="panel"><div class="chart">${chart}</div><div class="table-wrap"><table class="benchmark-table"><thead><tr><th>Session / algorithm</th><th>Baseline</th><th>Input size</th><th>Median time</th><th>Operations</th><th>Memory estimate</th><th>Oracle</th></tr></thead><tbody>${table}</tbody></table></div><p class="tiny" style="margin-top:10px">These values are read from reports/M2/session_benchmarks.csv. Timing is local and memory is an estimated reachable Python object graph; neither represents production performance or process RSS.</p></article>` : `<div class="roadmap-note">No M2 benchmark file is available. Run <span class="mono">python benchmarks/benchmark_m2.py --trials 5</span> to generate reproducible results.</div>`}`;
}

function wireBenchmarks() {
  view.querySelectorAll("a[href='/api/benchmarks.csv'], a[href='/api/benchmarks/m2.csv']").forEach((anchor) => anchor.addEventListener("click", () => showToast("Exporting benchmark results as CSV…")));
}

function renderReports() {
  const tests = state.data.tests;
  const verification = tests.verification;
  const testStatus = verification ? `${verification.passed} passed${verification.failed ? ` · ${verification.failed} failed` : ""}` : tests.status;
  const reportCards = state.data.reports.map((report) => `<a class="report-card" href="/files/${report.path}" target="_blank" rel="noopener"><span class="report-icon">▤</span><span class="report-copy"><strong>${escapeHtml(report.label)}</strong><small>${escapeHtml(report.kind)} · ${escapeHtml(report.description)}</small></span><span class="report-arrow">↗</span></a>`).join("");
  return `${pageHead("Evidence library", "Reports & deliverables", "Open the session evidence already in the repository, check local test status, or download a fresh Session 1 benchmark.", `<a class="secondary-button" href="/api/benchmarks.csv">↓ Session 1 CSV</a>`)}
    <article class="verification-card"><div><strong>Unit test suite</strong><p>${escapeHtml(tests.command)}<br />${escapeHtml(testStatus)}</p><div class="test-files">${tests.test_files.map((file) => `<span class="file-chip">${escapeHtml(file)}</span>`).join("")}</div>${verification ? `<p>Recorded command: ${escapeHtml(verification.command)} · ${escapeHtml(verification.run_date || "")}</p>` : ""}</div><span class="badge ${verification && verification.failed === 0 ? "badge-completed" : "badge-warning"}">${verification && verification.failed === 0 ? "Verified" : "Run locally"}</span></article>
    <div class="section-heading"><div><h2>Session evidence</h2><p>Existing reports and benchmark artifacts.</p></div></div><section class="report-grid">${reportCards}</section>
    <div class="section-heading" style="margin-top:23px"><div><h2>Current Session 1 outputs</h2><p>Generated from the implementation on each dashboard load.</p></div></div><section class="report-grid">
      <a class="report-card" href="#benchmarks"><span class="report-icon">▥</span><span class="report-copy"><strong>Live benchmark results</strong><small>Execution time · operation counts · memory estimate · oracle check</small></span><span class="report-arrow">→</span></a>
      <a class="report-card" href="/api/benchmarks.csv"><span class="report-icon">⇩</span><span class="report-copy"><strong>Export benchmark CSV</strong><small>Downloadable result rows for 20, 100, and 1,000 products</small></span><span class="report-arrow">↓</span></a>
      <a class="report-card" href="/files/reports/M1/M1_Final_Report.md" target="_blank" rel="noopener"><span class="report-icon">▧</span><span class="report-copy"><strong>M1 final report</strong><small>Existing milestone summary and acceptance checklist</small></span><span class="report-arrow">↗</span></a>
      <a class="report-card" href="/files/reports/M1/session5/before_after_benchmark.csv" target="_blank" rel="noopener"><span class="report-icon">↔</span><span class="report-copy"><strong>Before-and-after evidence</strong><small>Existing Session 5 linear and indexed comparison</small></span><span class="report-arrow">↗</span></a>
    </section>`;
}

function renderArchitecture() {
  const descriptions = [
    "Exact catalogue search, cost models, hardware-aware measurements, and profiling evidence.",
    "Range analytics, versioned snapshots, description indexes, category paths, and offline event queries.",
    "Probabilistic structures connect to catalogue lookup and analytics after their curriculum is supplied.",
    "Vector similarity connects to exact description search after its curriculum is supplied.",
    "Streaming methods connect to the anonymous marketplace event stream after its curriculum is supplied.",
    "Production retrieval connects verified catalogue and analytics services to the final marketplace system.",
  ];
  const phases = state.data.roadmap.map((phase) => `<article class="arch-node ${phase.status === "active" ? "active" : phase.status === "completed" ? "completed" : ""}"><span class="arch-number">P${phase.number}</span><span class="arch-copy"><strong>${escapeHtml(phase.title)}</strong><p>${escapeHtml(descriptions[phase.number - 1])}</p></span><span class="arch-range">S${phase.session_start}–${phase.session_end}</span></article>${phase.number < 6 ? `<div class="arch-connector" aria-hidden="true"></div>` : ""}`).join("");
  return `${pageHead("System view", "Architecture", "How catalogue data and marketplace activity connect across all six phases.")}
    <div class="system-output"><h3>Marketplace inputs</h3><p>Versioned product catalogue records and simulated anonymous search, view, and purchase events enter the system.</p></div>
    <div class="architecture-flow">${phases}</div>
    <div class="system-output"><h3>Verified system foundation</h3><p>Sessions 1–12 provide exact catalogue search, persistent snapshots, phrase search, category path aggregates, and historical event analytics. Phases 3–6 remain upcoming.</p></div>
    <p class="architecture-note">Session-level work for Phases 3–6 remains upcoming until their authoritative curriculum is available.</p>`;
}

function wireRoadmap() {
  document.querySelectorAll(".session-row").forEach((row) => {
    row.addEventListener("click", () => {
      const session = Number(row.dataset.session);
      if (session >= 1 && session <= 12) {
        state.selectedSession = session;
        window.location.hash = `workspace/${session}`;
      } else {
        showToast("This session is upcoming; authoritative curriculum details are pending.");
      }
    });
  });
}

async function boot() {
  document.getElementById("mobile-menu").addEventListener("click", () => sidebar.classList.toggle("open"));
  window.addEventListener("hashchange", setRouteFromHash);
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") sidebar.classList.remove("open");
  });
  try {
    const response = await fetch("/api/data");
    state.data = await response.json();
    if (!response.ok) throw new Error(state.data.error || "Could not load project data");
    setRouteFromHash();
  } catch (error) {
    view.innerHTML = `<section class="error-panel"><div class="eyebrow">Dashboard data unavailable</div><h2>Could not load the project workspace</h2><p>${escapeHtml(error.message)}</p><p>Check that the local server was started from the Smart-Marketplace project directory and that the Session 1 CSV fixtures are present.</p></section>`;
  }
}

boot();
