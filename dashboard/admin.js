"use strict";

const state = { data: null, toastTimer: null, editingId: null };
const el = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function money(value) { return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value) || 0); }
function toast(message) {
  const node = el("toast"); node.textContent = message; node.classList.add("show");
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => node.classList.remove("show"), 2600);
}
async function request(url, options = {}) {
  const response = await fetch(url, options); const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}
async function post(url, body) { return request(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); }

function renderStorefront() {
  const analytics = state.data.storefront;
  const orders = analytics.recent_orders || [];
  const metrics = [
    ["Catalogue products", analytics.product_count, "Current storefront catalogue"],
    ["Categories", analytics.category_count, "Distinct catalogue categories"],
    ["Available stock", analytics.available_stock, `${analytics.out_of_stock_count} products out of stock`],
    ["Demo orders", analytics.order_count, "Persisted local demo orders"],
    ["Demo sales", money(analytics.sales_inr), "Totals from saved demo orders"],
  ];
  el("storefront-metrics").innerHTML = metrics.map(([label, value, note]) => `<article class="metric"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong><span>${escapeHtml(note)}</span></article>`).join("");
  const categories = analytics.category_distribution;
  const maximum = Math.max(...categories.map((row) => Number(row.count)), 1);
  el("category-chart").innerHTML = categories.map((row) => `<div class="category-bar-row"><span>${escapeHtml(row.category)}</span><div><i style="width:${Number(row.count) / maximum * 100}%"></i></div><strong>${Number(row.count)}</strong></div>`).join("");
  el("order-rows").innerHTML = orders.slice(0, 8).map((order) => `<tr><td><strong>${escapeHtml(order.order_id)}</strong><small>${escapeHtml(String(order.created_at).replace("T", " ").replace("Z", ""))}</small></td><td>${escapeHtml(order.customer.full_name)}</td><td>${Number(order.item_count)}</td><td>${money(order.total)}</td><td><span class="order-status-chip">${escapeHtml(order.status)}</span></td></tr>`).join("") || `<tr><td colspan="5">No demo orders have been recorded.</td></tr>`;
}
function renderAlgorithmMetrics() {
  const { catalogue, analytics } = state.data;
  const eventData = analytics.event_data;
  const simulatedSales = analytics.session7.daily_sales.reduce((sum, day) => sum + Number(day.sales_inr), 0);
  const metrics = [
    ["Algorithm catalogue", catalogue.products.length, "Current versioned product rows"],
    ["Simulated events", eventData.total_events, `${eventData.anonymous_user_count} anonymous demo IDs`],
    ["Fixture sales", money(simulatedSales), "Session 7 purchase-event fixture"],
    ["Description views", eventData.view_event_count, `Catalogue ${catalogue.version_id}`],
  ];
  el("metrics").innerHTML = metrics.map(([label, value, note]) => `<article class="metric"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong><span>${escapeHtml(note)}</span></article>`).join("");
  el("catalogue-version").textContent = catalogue.version_id;
}
function renderProducts(filter = "") {
  const products = state.data.catalogue.products.filter((product) => `${product.product_id} ${product.title} ${product.brand || ""} ${product.description} ${product.category}`.toLowerCase().includes(filter.toLowerCase()));
  el("product-rows").innerHTML = products.map((product) => `<tr data-product="${escapeHtml(product.product_id)}">
    <td><strong>${escapeHtml(product.product_id)} · ${escapeHtml(product.title)}</strong><small>${escapeHtml(product.brand || "")}</small></td>
    <td>${escapeHtml(product.category)}</td><td>${money(product.price)}</td><td>${Number(product.stock)}</td>
    <td><form class="stock-editor" data-stock-form="${escapeHtml(product.product_id)}"><input name="stock" type="number" min="0" step="1" value="${Number(product.stock)}" aria-label="New stock for ${escapeHtml(product.product_id)}"/><button type="submit">Save</button></form></td>
    <td class="admin-actions"><button type="button" data-edit-product="${escapeHtml(product.product_id)}">Edit</button><button type="button" data-delete-product="${escapeHtml(product.product_id)}">Delete</button></td></tr>`).join("") || `<tr><td colspan="6">No products match this filter.</td></tr>`;
  el("product-rows").querySelectorAll("[data-stock-form]").forEach((form) => form.addEventListener("submit", updateStock));
}
function renderSalesChart() {
  const days = state.data.analytics.session7.daily_sales;
  const maximum = Math.max(...days.map((day) => Number(day.sales_inr)), 1);
  el("sales-chart").innerHTML = days.map((day) => {
    const height = Math.max(4, Number(day.sales_inr) / maximum * 100);
    const label = new Date(`${day.day}T00:00:00`).getDate();
    return `<div class="sales-bar" style="height:${height}%" title="${escapeHtml(day.day)} · ${money(day.sales_inr)} · ${day.purchase_count} purchases"><span>${label}</span></div>`;
  }).join("");
  const demo = state.data.analytics.session7;
  el("sales-output").innerHTML = `<strong class="ok">${escapeHtml(demo.sales_query.label)}:</strong> ${money(demo.sales_query.sales_inr)} · Fenwick oracle ${demo.sales_oracle_passed ? "passed" : "failed"}. Range stock adjustment: ${Number(demo.stock_adjustment.before_total)} → ${Number(demo.stock_adjustment.after_total)} units; segment tree oracle ${demo.stock_adjustment.oracle_passed ? "passed" : "failed"}.`;
}
function renderSessionStatus() {
  el("session-status").innerHTML = Array.from({ length: 6 }, (_, index) => {
    const number = index + 7; const passed = Boolean(state.data.analytics[`session${number}`].acceptance_passed);
    return `<div class="status"><strong>Session ${number}</strong><span>${passed ? "Acceptance checks passed" : "Acceptance check failed"}</span></div>`;
  }).join("");
}
function render() {
  renderStorefront(); renderAlgorithmMetrics(); renderProducts(); renderSalesChart(); renderSessionStatus();
  loadSalesRange(2, 9).catch((error) => { el("sales-output").textContent = error.message; });
  loadDistinctRange(0, 20).catch((error) => { el("distinct-output").textContent = error.message; });
}
async function reload() { state.data = await request("/api/admin/data"); render(); }
async function updateStock(event) {
  event.preventDefault(); const form = event.currentTarget; const productId = form.dataset.stockForm; const stock = Number(new FormData(form).get("stock"));
  try { const result = await post("/api/admin/stock", { product_id: productId, stock }); await reload(); toast(`${productId} saved in catalogue ${result.version_id}.`); }
  catch (error) { toast(error.message); }
}
async function compressImage(file) {
  if (!file) return null;
  const bitmap = await createImageBitmap(file); const scale = Math.min(1, 1000 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas"); canvas.width = Math.max(1, Math.round(bitmap.width * scale)); canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height); bitmap.close();
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/webp", .82));
  if (!blob || blob.size > 880000) throw new Error("Choose a smaller product photo; uploads are limited to 900 KB.");
  return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(new Error("Could not read selected photo.")); reader.readAsDataURL(blob); });
}
function resetProductEditor() {
  state.editingId = null; const form = el("product-editor"); form.reset(); form.elements.product_id.readOnly = false;
  form.elements.rating.value = "4.0"; form.elements.popularity.value = "0"; form.elements.specifications.value = "{}";
  el("editor-title").textContent = "Add product"; el("product-save").textContent = "Add to catalogue";
}
function selectProduct(productId) {
  const product = state.data.catalogue.products.find((row) => String(row.product_id) === productId); if (!product) return;
  const form = el("product-editor"); form.elements.product_id.value = product.product_id; form.elements.product_id.readOnly = true;
  for (const key of ["title", "brand", "description", "category", "price", "original_price", "stock", "rating", "popularity"]) form.elements[key].value = product[key] ?? "";
  form.elements.created_at.value = String(product.created_at || "").slice(0, 10);
  form.elements.specifications.value = JSON.stringify(product.specifications || {}, null, 2); form.elements.image_file.value = "";
  state.editingId = productId; el("editor-title").textContent = `Edit ${productId}`; el("product-save").textContent = "Save product";
  form.scrollIntoView({ behavior: "smooth", block: "center" });
}
async function saveProduct(event) {
  event.preventDefault(); const form = event.currentTarget; const values = Object.fromEntries(new FormData(form).entries()); delete values.image_file;
  for (const key of ["price", "rating", "popularity"]) values[key] = Number(values[key] || 0);
  values.stock = Number(values.stock);
  if (values.original_price === "") {
    if (state.editingId) values.original_price = null; else delete values.original_price;
  } else values.original_price = Number(values.original_price);
  try { values.specifications = JSON.parse(values.specifications || "{}"); }
  catch (_error) { toast("Specifications must be valid JSON."); return; }
  try {
    const uploaded = await compressImage(form.elements.image_file.files[0]); if (uploaded) values.image_data = uploaded;
    const productId = state.editingId;
    const result = productId
      ? await request(`/api/admin/products/${encodeURIComponent(productId)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) })
      : await post("/api/admin/products", values);
    resetProductEditor(); await reload(); toast(`${productId ? "Product updated" : "Product added"} in catalogue ${result.version_id}.`);
  } catch (error) { toast(error.message); }
}
async function deleteProduct(productId) {
  const product = state.data.catalogue.products.find((row) => String(row.product_id) === productId);
  if (!product || !window.confirm(`Delete ${product.title} (${productId}) from the persistent catalogue?`)) return;
  try { const result = await request(`/api/admin/products/${encodeURIComponent(productId)}`, { method: "DELETE" }); if (state.editingId === productId) resetProductEditor(); await reload(); toast(`Product deleted from catalogue ${result.version_id}.`); }
  catch (error) { toast(error.message); }
}
function productAction(event) {
  const edit = event.target.closest("[data-edit-product]"); if (edit) selectProduct(edit.dataset.editProduct);
  const remove = event.target.closest("[data-delete-product]"); if (remove) deleteProduct(remove.dataset.deleteProduct);
}
async function checkDuplicate(event) {
  event.preventDefault(); const description = new FormData(event.currentTarget).get("description");
  try {
    const result = await post("/api/admin/duplicate-check", { description });
    el("duplicate-output").innerHTML = `<strong class="${result.is_duplicate ? "bad" : "ok"}">${result.is_duplicate ? "Exact description already listed" : "No exact duplicate found"}</strong><br/>Fingerprint ${escapeHtml(result.fingerprint)} · ${Number(result.exact_comparisons)} exact candidate checks · Product IDs: ${escapeHtml(result.duplicate_product_ids.join(", ") || "none")}`;
  } catch (error) { el("duplicate-output").textContent = error.message; }
}
async function loadSalesRange(start, end) {
  const result = await request(`/api/analytics/range?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  el("sales-output").innerHTML = `<strong class="${result.oracle_passed ? "ok" : "bad"}">[${result.start}, ${result.end_exclusive}):</strong> ${money(result.sales_inr)} · direct-sum oracle ${result.oracle_passed ? "passed" : "failed"}.`;
}
async function loadDistinctRange(start, end) {
  const result = await request(`/api/analytics/distinct?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  el("distinct-output").innerHTML = `<strong class="${result.oracle_passed ? "ok" : "bad"}">${Number(result.distinct_products)} distinct product IDs</strong> in ${Number(result.end_exclusive - result.start)} view events · ${Number(result.pointer_moves)} window moves · oracle ${result.oracle_passed ? "passed" : "failed"}.`;
}
async function rangeSubmit(event) {
  event.preventDefault(); const values = new FormData(event.currentTarget);
  try { await loadSalesRange(values.get("start"), values.get("end")); } catch (error) { el("sales-output").textContent = error.message; }
}
async function distinctSubmit(event) {
  event.preventDefault(); const values = new FormData(event.currentTarget);
  try { await loadDistinctRange(values.get("start"), values.get("end")); } catch (error) { el("distinct-output").textContent = error.message; }
}
async function substringSubmit(event) {
  event.preventDefault(); const values = new FormData(event.currentTarget); const params = new URLSearchParams(values);
  try {
    const result = await request(`/api/search/substring?${params}`);
    const items = result.results.map((row) => `${row.document_id}${row.offset === undefined ? ` (${row.occurrences} occurrences)` : ` @ ${row.offset}`}`);
    el("substring-output").innerHTML = `<strong>${items.length} document matches</strong> · ${escapeHtml(result.catalogue_version_id)} · ${escapeHtml(result.algorithm)}<br/>${escapeHtml(items.join(", ") || "No match")}`;
  } catch (error) { el("substring-output").textContent = error.message; }
}

el("catalogue-filter").addEventListener("input", (event) => renderProducts(event.target.value));
el("product-editor").addEventListener("submit", saveProduct);
el("product-rows").addEventListener("click", productAction);
document.querySelector("[data-product-reset]").addEventListener("click", resetProductEditor);
el("duplicate-check").addEventListener("submit", checkDuplicate);
el("sales-range").addEventListener("submit", rangeSubmit);
el("distinct-range").addEventListener("submit", distinctSubmit);
el("substring-search").addEventListener("submit", substringSubmit);
reload().catch((error) => { document.querySelector("main").innerHTML = `<section class="panel"><h1>Admin data could not load</h1><p>${escapeHtml(error.message)}</p></section>`; });
