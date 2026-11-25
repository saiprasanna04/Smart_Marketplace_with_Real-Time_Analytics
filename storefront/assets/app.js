"use strict";

const CART_KEY = "smart-cart-v2";
const WISHLIST_KEY = "smart-wishlist-v1";
const root = document.getElementById("storefront-view");
const state = { products: [], cart: [], wishlist: [], categories: [], requestId: 0, toastTimer: null };

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}
function money(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value) || 0);
}
function discountRate(product) {
  const original = Number(product.original_price || product.price);
  return original > Number(product.price) ? Math.round((original - Number(product.price)) / original * 100) : 0;
}
function readList(key) {
  try { const value = JSON.parse(localStorage.getItem(key) || "[]"); return Array.isArray(value) ? value : []; }
  catch (_error) { return []; }
}
function saveCart() { localStorage.setItem(CART_KEY, JSON.stringify(state.cart)); }
function saveWishlist() { localStorage.setItem(WISHLIST_KEY, JSON.stringify(state.wishlist)); }
function productMap() { return new Map(state.products.map((product) => [String(product.product_id), product])); }
function cartSummary() { return window.SmartCartCore.summarize(state.cart, productMap()); }
function updateCounts() {
  const summary = cartSummary();
  const cartCount = document.getElementById("cart-count");
  const wishlistCount = document.getElementById("wishlist-count");
  if (cartCount) cartCount.textContent = String(summary.item_count);
  if (wishlistCount) wishlistCount.textContent = String(state.wishlist.length);
}
function toast(message) {
  const node = document.getElementById("store-toast");
  node.textContent = message; node.classList.add("show");
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => node.classList.remove("show"), 2600);
}
async function request(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}
async function requestProducts(filters = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value !== "" && value !== null && value !== undefined && value !== false) params.set(key, value === true ? "true" : String(value));
  return request(`/api/marketplace/products?${params}`);
}
async function requestProduct(productId) { return (await request(`/api/marketplace/products/${encodeURIComponent(productId)}`)).product; }
function mergeProducts(products) {
  const byId = productMap();
  for (const product of products || []) byId.set(String(product.product_id), product);
  state.products = [...byId.values()];
}
function navigate(path) {
  const target = new URL(path, location.origin);
  history.pushState({}, "", `${target.pathname}${target.search}${target.hash}`);
  document.getElementById("main-nav")?.classList.remove("open");
  document.getElementById("mobile-nav-toggle")?.setAttribute("aria-expanded", "false");
  renderRoute(); window.scrollTo({ top: 0, behavior: "smooth" });
  if (target.hash) setTimeout(() => document.getElementById(target.hash.slice(1))?.scrollIntoView({ behavior: "smooth" }), 80);
}
function routeInfo() {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/products") return { page: "products" };
  if (path === "/categories") return { page: "categories" };
  if (path === "/deals") return { page: "deals" };
  if (path === "/cart") return { page: "cart" };
  if (path === "/wishlist") return { page: "wishlist" };
  if (path === "/checkout") return { page: "checkout" };
  if (path === "/orders") return { page: "orders" };
  if (path.startsWith("/order-confirmation/")) return { page: "confirmation", orderId: decodeURIComponent(path.slice("/order-confirmation/".length)) };
  if (path.startsWith("/product/") || path.startsWith("/products/")) return { page: "details", productId: decodeURIComponent(path.startsWith("/product/") ? path.slice("/product/".length) : path.slice("/products/".length)) };
  return { page: "home" };
}
function setActiveNav(page) {
  const activePath = { home: "/", products: "/products", details: "/products", categories: "/categories", deals: "/deals", orders: "/orders" }[page];
  document.querySelectorAll(".main-nav a").forEach((link) => link.classList.toggle("active", link.getAttribute("href") === activePath));
  document.querySelector(".cart-link")?.classList.toggle("active", page === "cart");
  document.querySelector(".wishlist-link")?.classList.toggle("active", page === "wishlist");
}
async function renderRoute() {
  const route = routeInfo(); setActiveNav(route.page); updateCounts();
  const requestId = ++state.requestId;
  try {
    if (route.page === "home") await renderHome();
    else if (route.page === "products") await renderProducts();
    else if (route.page === "categories") await renderCategories();
    else if (route.page === "deals") await renderDeals();
    else if (route.page === "details") await renderDetails(route.productId);
    else if (route.page === "cart") renderCart();
    else if (route.page === "wishlist") renderWishlist();
    else if (route.page === "checkout") renderCheckout();
    else if (route.page === "orders") await renderOrders();
    else if (route.page === "confirmation") await renderConfirmation(route.orderId);
  } catch (error) {
    if (requestId !== state.requestId) return;
    root.innerHTML = `<section class="error-panel"><h2>We couldn't load this page</h2><p>${escapeHtml(error.message)}</p><button class="button-secondary" type="button" data-go-home>Return home</button></section>`;
  }
  updateCounts();
}

function imageFor(product, extraClass = "") {
  const image = escapeHtml(product.image || "");
  const alt = escapeHtml(product.title);
  const fallback = state.products.find((row) => row.category === product.category && row.product_id !== product.product_id)?.image
    || state.products.find((row) => row.product_id !== product.product_id)?.image || product.image || "";
  return `<div class="product-art ${extraClass}"><img data-product-image data-fallback="${escapeHtml(fallback)}" src="${image}" alt="${alt}" loading="lazy" decoding="async"/><span class="art-tag">${escapeHtml(product.category)}</span></div>`;
}
function productCard(product) {
  const inStock = Number(product.stock) > 0;
  const sale = discountRate(product);
  const wished = state.wishlist.includes(String(product.product_id));
  const moveToCart = routeInfo().page === "wishlist" ? `<button class="wishlist-move" type="button" data-move-to-cart="${escapeHtml(product.product_id)}">Move to cart</button>` : "";
  return `<article class="product-card" data-product-card="${escapeHtml(product.product_id)}">
    <a class="product-image-link" href="/product/${encodeURIComponent(product.product_id)}" data-nav aria-label="View ${escapeHtml(product.title)}">${imageFor(product)}${sale ? `<span class="sale-tag">${sale}% off</span>` : ""}</a>
    <div class="product-info"><div class="product-category">${escapeHtml(product.category)}</div><h3 class="product-title">${escapeHtml(product.title)}</h3><div class="product-brand">${escapeHtml(product.brand || "Marketplace selection")}</div>
      <p class="product-description">${escapeHtml(product.description)}</p><div class="product-rating" aria-label="Demo rating ${Number(product.rating || 0).toFixed(1)} out of 5">★ <strong>${Number(product.rating || 0).toFixed(1)}</strong> <small>sample rating</small></div>
      <div class="product-purchase"><div><div class="product-price">${money(product.price)}</div>${sale ? `<del class="original-price">${money(product.original_price)}</del>` : ""}<span class="stock-status ${inStock ? "" : "out"}">${inStock ? `${Number(product.stock)} available in demo inventory` : "Currently unavailable"}</span></div></div>
      <div class="product-actions">${moveToCart}<button class="button-primary" type="button" data-add-to-cart="${escapeHtml(product.product_id)}" ${inStock ? "" : "disabled"}>Add to cart</button><a class="button-secondary" href="/product/${encodeURIComponent(product.product_id)}" data-nav>Details</a><button class="button-icon wishlist-toggle ${wished ? "selected" : ""}" type="button" data-wishlist-toggle="${escapeHtml(product.product_id)}" aria-label="${wished ? "Remove from" : "Add to"} wishlist" title="${wished ? "Remove from" : "Add to"} wishlist">${wished ? "♥" : "♡"}</button></div>
    </div></article>`;
}
function productSection(title, subtitle, products, href = "/products") {
  return `<section class="content-section"><div class="section-heading"><div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(subtitle)}</p></div><a class="section-link" href="${href}" data-nav>View all →</a></div>${products.length ? `<div class="product-grid">${products.map(productCard).join("")}</div>` : `<div class="empty-state"><strong>No products available</strong><p>This section will update when the catalogue has matching products.</p></div>`}</section>`;
}
function categoryCards(categories, products) {
  return categories.map((category) => {
    const product = products.find((row) => row.category === category);
    const count = products.filter((row) => row.category === category).length;
    return `<a class="category-card" href="/products?category=${encodeURIComponent(category)}" data-nav ${product ? `style="--category-photo:url('${escapeHtml(product.image)}')"` : ""}><span class="category-count">${count} ${count === 1 ? "product" : "products"}</span><strong>${escapeHtml(category)}</strong><span class="category-arrow">Explore →</span></a>`;
  }).join("");
}
async function renderHome() {
  const all = await requestProducts({ sort: "featured" });
  const products = all.products || [];
  const popularityRanked = [...products].sort((left, right) =>
    Number(right.popularity || 0) - Number(left.popularity || 0)
      || String(left.product_id).localeCompare(String(right.product_id))
  );
  const home = {
    categories: all.categories || [...new Set(products.map((product) => String(product.category)))].sort(),
    trending: popularityRanked.slice(0, 4),
    best_sellers: popularityRanked.slice(4, 8),
    recent: [...products].sort((left, right) => String(right.created_at || "").localeCompare(String(left.created_at || ""))).slice(0, 4),
    deals: [...products].filter((product) => discountRate(product) > 0).sort((left, right) => discountRate(right) - discountRate(left)).slice(0, 4),
  };
  mergeProducts(products); state.categories = home.categories;
  const featured = products.find((product) => product.product_id === "P1016") || home.trending[0];
  root.innerHTML = `<section class="home-hero"><div class="hero-copy"><div class="hero-kicker">SMART CART · THOUGHTFUL EVERYDAY FINDS</div><h1>Good choices,<br/><span>delivered simply.</span></h1><p class="hero-description">Explore a carefully organised demo catalogue with useful products across work, home, style and everyday life.</p>
      <form class="header-search hero-search" data-search-form><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.3"/><path d="m15.5 15.5 4.2 4.2"/></svg><input name="query" type="search" list="search-suggestions" placeholder="Search products, brands and categories" autocomplete="off"/><button type="submit">Search catalogue</button></form>
      <div class="hero-trust"><span>32 locally photographed demo products</span><span>·</span><span>Simulated inventory and checkout</span></div></div>
      ${featured ? `<a class="hero-visual" href="/product/${encodeURIComponent(featured.product_id)}" data-nav aria-label="View ${escapeHtml(featured.title)}"><div class="hero-orbit"></div>${imageFor(featured, "hero-product")}<div class="hero-float top"><span>Featured find</span><strong>${escapeHtml(featured.title)}</strong></div><div class="hero-float bottom"><span>Demo price</span><strong>${money(featured.price)}</strong></div></a>` : ""}</section>
    <section class="content-section" id="categories"><div class="section-heading"><div><h2>Shop by category</h2><p>Find your next useful everyday item.</p></div><a class="section-link" href="/categories" data-nav>All categories →</a></div><div class="category-grid">${categoryCards(home.categories, all.products)}</div></section>
    ${productSection("Trending in the catalogue", "Products with the strongest sample popularity signals.", home.trending)}
    ${productSection("Popular picks", "More products ranked by their sample catalogue popularity scores.", home.best_sellers)}
    ${productSection("Recently added", "Newest catalogue entries, based on their recorded sample dates.", home.recent)}
    ${productSection("Special offers", "Demo catalogue prices compared with their listed original prices.", home.deals, "/deals")}`;
  installSuggestions();
}
async function renderCategories() {
  const payload = await requestProducts({ sort: "featured" }); mergeProducts(payload.products);
  root.innerHTML = `<div class="catalogue-heading"><div><div class="hero-kicker">Browse collections</div><h1>All categories</h1><p>Each category links to live catalogue filters.</p></div></div><div class="category-grid category-grid-large">${categoryCards(payload.categories, payload.products)}</div>`;
}
function filtersFromUrl() {
  const params = new URLSearchParams(location.search);
  return { query: params.get("query") || "", category: params.get("category") || "", brand: params.get("brand") || "", min_price: params.get("min_price") || "", max_price: params.get("max_price") || "", min_rating: params.get("min_rating") || "", in_stock: params.get("in_stock") === "true", sort: params.get("sort") || (params.has("query") ? "relevance" : "featured") };
}
function filtersForm(filters, categories, brands) {
  return `<aside class="filter-panel"><h2>Refine products</h2><form id="filters-form"><label class="filter-field">Category<select name="category">${[`<option value="">All categories</option>`, ...categories.map((item) => `<option ${filters.category === item ? "selected" : ""} value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)].join("")}</select></label>
    <label class="filter-field">Brand<select name="brand">${[`<option value="">All brands</option>`, ...brands.map((item) => `<option ${filters.brand === item ? "selected" : ""} value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)].join("")}</select></label>
    <fieldset class="filter-group"><legend>Price range · ₹</legend><div class="price-range-fields"><input name="min_price" type="number" min="0" step="1" placeholder="Min" value="${escapeHtml(filters.min_price)}" aria-label="Minimum price"/><input name="max_price" type="number" min="0" step="1" placeholder="Max" value="${escapeHtml(filters.max_price)}" aria-label="Maximum price"/></div></fieldset>
    <label class="filter-field">Minimum sample rating<select name="min_rating"><option value="">Any rating</option>${[3, 4, 4.5].map((value) => `<option value="${value}" ${filters.min_rating === String(value) ? "selected" : ""}>${value}+ sample rating</option>`).join("")}</select></label>
    <label class="filter-option"><input name="in_stock" type="checkbox" ${filters.in_stock ? "checked" : ""}/> In stock only</label>
    <button class="button-primary filter-apply" type="submit">Apply filters</button><button class="button-secondary clear-filters" type="button" data-reset-filters>Reset filters</button></form></aside>`;
}
async function renderProducts() {
  const filters = filtersFromUrl();
  const payload = await requestProducts(filters); mergeProducts(payload.products); state.categories = payload.categories;
  const cards = payload.products.map(productCard).join("");
  root.innerHTML = `<div class="catalogue-heading"><div><div class="hero-kicker">THE SMART CART COLLECTION</div><h1>Shop all products</h1><p>Search actual catalogue records and filter by price, rating, stock, brand or category.</p></div></div>
    <div class="catalogue-layout">${filtersForm(filters, payload.categories, payload.brands)}<section class="catalogue-results"><div class="catalogue-toolbar"><div class="results-count"><strong>${payload.total}</strong> ${payload.total === 1 ? "product" : "products"}${filters.query ? `<small>matching “${escapeHtml(filters.query)}”</small>` : ""}</div><label class="sort-control">Sort by <select id="sort-filter"><option value="featured" ${filters.sort === "featured" ? "selected" : ""}>Featured</option><option value="relevance" ${filters.sort === "relevance" ? "selected" : ""}>Most relevant</option><option value="price_asc" ${filters.sort === "price_asc" ? "selected" : ""}>Price: low to high</option><option value="price_desc" ${filters.sort === "price_desc" ? "selected" : ""}>Price: high to low</option><option value="newest" ${filters.sort === "newest" ? "selected" : ""}>Newest</option><option value="popular" ${filters.sort === "popular" ? "selected" : ""}>Popularity</option></select></label></div>
      ${cards ? `<div class="product-grid">${cards}</div>` : `<div class="empty-state"><strong>No matching products</strong><p>Try another search or reset your filters.</p><button class="button-secondary" type="button" data-reset-filters>Reset filters</button></div>`}</section></div>`;
  installSuggestions();
}
async function renderDeals() {
  const payload = await requestProducts({ sort: "discount_desc" }); mergeProducts(payload.products);
  const products = payload.products.filter((product) => discountRate(product) > 0);
  root.innerHTML = `<div class="catalogue-heading"><div><div class="hero-kicker">CURRENT DEMO OFFERS</div><h1>Special offers</h1><p>Discounts are calculated from the sample original and catalogue prices.</p></div></div>${products.length ? `<div class="product-grid">${products.map(productCard).join("")}</div>` : `<div class="empty-state"><strong>No active offers</strong><p>Products with a listed reduction will appear here.</p></div>`}`;
}
async function renderDetails(productId) {
  const product = await requestProduct(productId); mergeProducts([product]);
  const inStock = Number(product.stock) > 0;
  const specs = product.specifications && typeof product.specifications === "object" ? Object.entries(product.specifications) : [];
  const related = state.products.filter((row) => row.category === product.category && row.product_id !== product.product_id).slice(0, 4);
  root.innerHTML = `<a class="back-link" href="/products" data-nav>← Back to products</a><section class="detail-layout"><div class="detail-art">${imageFor(product)}</div><div class="detail-copy"><div class="breadcrumb"><a href="/" data-nav>Home</a> / ${escapeHtml(product.category)}</div><div class="product-category">${escapeHtml(product.category)}</div><h1>${escapeHtml(product.title)}</h1><p class="detail-brand">${escapeHtml(product.brand || "Marketplace selection")}</p><p class="detail-description">${escapeHtml(product.description)}</p><div class="product-rating detail-rating">★ <strong>${Number(product.rating || 0).toFixed(1)}</strong> <small>sample rating; no customer reviews are represented</small></div>
      <div class="detail-price">${money(product.price)} ${discountRate(product) ? `<del>${money(product.original_price)}</del><span class="discount-pill">${discountRate(product)}% off</span>` : ""}</div><ul class="detail-meta"><li><span>Demo inventory status</span><strong class="stock-status ${inStock ? "" : "out"}">${inStock ? "Available" : "Out of stock"}</strong></li><li><span>Available units</span><strong>${Number(product.stock)}</strong></li><li><span>Product ID</span><strong>${escapeHtml(product.product_id)}</strong></li></ul>
      <div class="detail-buy"><div class="quantity-control"><button type="button" data-detail-quantity="-1" aria-label="Decrease quantity">−</button><input id="detail-quantity" type="number" min="1" max="${Math.max(1, Number(product.stock))}" value="1" aria-label="Quantity"/><button type="button" data-detail-quantity="1" aria-label="Increase quantity">+</button></div><button class="button-primary" type="button" data-add-to-cart="${escapeHtml(product.product_id)}" data-use-detail-quantity ${inStock ? "" : "disabled"}>Add to cart</button><button class="button-icon wishlist-toggle ${state.wishlist.includes(product.product_id) ? "selected" : ""}" type="button" data-wishlist-toggle="${escapeHtml(product.product_id)}" aria-label="Toggle wishlist">${state.wishlist.includes(product.product_id) ? "♥" : "♡"}</button></div></div></section>
    ${specs.length ? `<section class="content-section spec-section"><div class="section-heading"><div><h2>Specifications</h2><p>Product details from the local catalogue record.</p></div></div><dl class="spec-grid">${specs.map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl></section>` : ""}
    ${productSection("More in this category", "Related products from the local catalogue.", related)}`;
}
function renderCart() {
  const summary = cartSummary();
  if (!summary.lines.length) {
    state.cart = []; saveCart();
    root.innerHTML = `<div class="cart-page-head"><h1>Your cart</h1><p>Your locally saved shopping list.</p></div><section class="cart-empty"><span class="cart-empty-icon"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 6h3l2.5 14h15l3-10H8"/><circle cx="12" cy="25" r="1.7"/><circle cx="22" cy="25" r="1.7"/></svg></span><h2>Your cart is empty</h2><p>Browse the catalogue and add something useful for your everyday.</p><a class="button-primary" href="/products" data-nav>Continue shopping</a></section>`; return;
  }
  root.innerHTML = `<div class="cart-page-head"><div class="hero-kicker">YOUR PICKS, TOGETHER</div><h1>Your cart</h1><p>${summary.item_count} ${summary.item_count === 1 ? "item" : "items"} · saved in this browser</p></div><div class="cart-layout"><section class="cart-items"><div class="cart-table-head"><span>Product</span><span>Quantity</span><span>Subtotal</span></div>${summary.lines.map((line) => `<article class="cart-row"><div class="cart-product">${imageFor(line.product)}<div class="cart-product-copy"><strong>${escapeHtml(line.product.title)}</strong><small>${escapeHtml(line.product.category)} · ${money(line.unit_price)} each</small></div></div><div class="quantity-stepper"><button type="button" data-cart-change="-1" data-product-id="${escapeHtml(line.product_id)}" aria-label="Decrease quantity">−</button><span>${line.quantity}</span><button type="button" data-cart-change="1" data-product-id="${escapeHtml(line.product_id)}" aria-label="Increase quantity">+</button></div><div class="cart-line-total"><span>${money(line.line_total)}</span><button class="remove-item" type="button" data-cart-remove="${escapeHtml(line.product_id)}" aria-label="Remove ${escapeHtml(line.product.title)}">Remove</button></div></article>`).join("")}</section>
    <aside class="cart-summary"><h2>Order summary</h2><div class="summary-line"><span>Items (${summary.item_count})</span><strong>${money(summary.subtotal)}</strong></div>${summary.savings ? `<div class="summary-line"><span>Catalogue savings</span><strong class="savings-value">−${money(summary.savings)}</strong></div>` : ""}<div class="summary-line"><span>Delivery</span><strong>${summary.delivery ? money(summary.delivery) : "Free"}</strong></div><p class="delivery-note">${summary.subtotal >= 1999 ? "Free delivery on this demo order." : `Free delivery on orders above ${money(1999)}.`}</p><div class="summary-divider"></div><div class="summary-line summary-total"><span>Total</span><strong>${money(summary.total)}</strong></div><p class="payment-note">Demo checkout only. No payment is processed and no card details are requested.</p><a class="button-primary continue-shopping" href="/checkout" data-nav>Continue to checkout</a><a class="button-secondary continue-shopping" href="/products" data-nav>Continue shopping</a></aside></div>`;
}
function renderWishlist() {
  const products = state.wishlist.map((id) => productMap().get(id)).filter(Boolean);
  root.innerHTML = `<div class="catalogue-heading"><div><div class="hero-kicker">SAVED FOR LATER</div><h1>Your wishlist</h1><p>Saved in this browser and ready to move to your cart.</p></div></div>${products.length ? `<div class="product-grid">${products.map(productCard).join("")}</div>` : `<section class="cart-empty"><h2>Your wishlist is empty</h2><p>Save products with the heart button to find them here later.</p><a class="button-primary" href="/products" data-nav>Explore products</a></section>`}`;
}
function renderCheckout() {
  const summary = cartSummary();
  if (!summary.lines.length) { root.innerHTML = `<section class="cart-empty"><h1>Your cart is empty</h1><p>Add products before checkout.</p><a class="button-primary" href="/products" data-nav>Browse products</a></section>`; return; }
  root.innerHTML = `<div class="catalogue-heading"><div><div class="hero-kicker">DEMO CHECKOUT</div><h1>Delivery details</h1><p>This local workflow records a simulated order. It does not process payments.</p></div></div><div class="checkout-layout"><form id="checkout-form" class="checkout-form"><h2>Where should we deliver?</h2><div class="checkout-fields"><label>Full name<input name="full_name" autocomplete="name" required maxlength="100"/></label><label>Phone number<input name="phone" autocomplete="tel" required maxlength="30"/></label><label class="field-wide">Delivery address<input name="address" autocomplete="street-address" required maxlength="240"/></label><label>City<input name="city" autocomplete="address-level2" required maxlength="80"/></label><label>Postal code<input name="postal_code" autocomplete="postal-code" required maxlength="20"/></label></div><fieldset class="payment-options"><legend>Demo payment method</legend><label><input type="radio" name="payment_method" value="cash_on_delivery" checked/> Cash on delivery (simulated)</label><label><input type="radio" name="payment_method" value="demo"/> Demo order (no payment)</label></fieldset><p class="privacy-note">Please use sample details. This project stores demo order information locally and does not request card data.</p><button class="button-primary" type="submit">Place demo order · ${money(summary.total)}</button></form><aside class="cart-summary"><h2>Order summary</h2>${summary.lines.map((line) => `<div class="summary-line"><span>${escapeHtml(line.product.title)} × ${line.quantity}</span><strong>${money(line.line_total)}</strong></div>`).join("")}<div class="summary-divider"></div><div class="summary-line"><span>Subtotal</span><strong>${money(summary.subtotal)}</strong></div>${summary.savings ? `<div class="summary-line"><span>Savings</span><strong class="savings-value">−${money(summary.savings)}</strong></div>` : ""}<div class="summary-line"><span>Delivery</span><strong>${summary.delivery ? money(summary.delivery) : "Free"}</strong></div><div class="summary-line summary-total"><span>Total</span><strong>${money(summary.total)}</strong></div><a class="button-secondary continue-shopping" href="/cart" data-nav>Back to cart</a></aside></div>`;
}
function dateText(value) { const date = new Date(value); return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(date); }
function orderCard(order, confirmation = false) {
  return `<article class="order-card"><div class="order-head"><div><small>ORDER ID</small><strong>${escapeHtml(order.order_id)}</strong></div><span class="order-status">${escapeHtml(order.status)}</span></div><p class="order-date">Placed ${dateText(order.created_at)} · ${order.item_count} items</p><div class="order-lines">${order.items.map((line) => `<div><span>${escapeHtml(line.title)} × ${Number(line.quantity)}</span><strong>${money(line.line_total)}</strong></div>`).join("")}</div><div class="order-total"><span>Total (demo)</span><strong>${money(order.total)}</strong></div>${confirmation ? `<p class="payment-note">Order confirmed locally using ${escapeHtml(order.payment_method)}. No payment was taken.</p>` : ""}</article>`;
}
async function renderOrders() {
  const { orders } = await request("/api/orders");
  root.innerHTML = `<div class="catalogue-heading"><div><div class="hero-kicker">LOCAL ORDER HISTORY</div><h1>Your orders</h1><p>Orders from this application instance are stored in its local data folder.</p></div></div>${orders.length ? `<div class="orders-list">${orders.map((order) => orderCard(order)).join("")}</div>` : `<section class="cart-empty"><h2>No demo orders yet</h2><p>Place a sample order to see it listed here.</p><a class="button-primary" href="/products" data-nav>Shop products</a></section>`}`;
}
async function renderConfirmation(orderId) {
  const { order } = await request(`/api/orders/${encodeURIComponent(orderId)}`);
  root.innerHTML = `<section class="confirmation-panel"><span class="confirmation-check">✓</span><div class="hero-kicker">ORDER RECORDED LOCALLY</div><h1>Thank you, ${escapeHtml(order.customer.full_name)}</h1><p>Your demo order is confirmed. No payment was processed.</p>${orderCard(order, true)}<div class="confirmation-actions"><a class="button-primary" href="/orders" data-nav>View order history</a><a class="button-secondary" href="/products" data-nav>Continue shopping</a></div></section>`;
}

function syncSearchFields(query) {
  document.querySelectorAll('input[name="query"]').forEach((input) => { if (document.activeElement !== input) input.value = query; });
}
function submitSearch(query) { const clean = query.trim(); navigate(clean ? `/products?query=${encodeURIComponent(clean)}` : "/products"); }
function installSuggestions() {
  let list = document.getElementById("search-suggestions");
  if (!list) { list = document.createElement("datalist"); list.id = "search-suggestions"; document.body.appendChild(list); }
  document.querySelectorAll('input[name="query"]').forEach((input) => input.setAttribute("list", "search-suggestions"));
}
let suggestionTimer;
async function loadSuggestions(query) {
  clearTimeout(suggestionTimer);
  suggestionTimer = setTimeout(async () => {
    try {
      const payload = await request(`/api/marketplace/suggestions?q=${encodeURIComponent(query)}`);
      const list = document.getElementById("search-suggestions");
      list.innerHTML = payload.suggestions.map((item) => `<option value="${escapeHtml(item.title)}">${escapeHtml(item.brand)} · ${escapeHtml(item.category)}</option>`).join("");
    } catch (_error) { /* Suggestions enhance search; submit still uses the live search API. */ }
  }, 140);
}
function applyFilters(form) {
  const current = new URLSearchParams(location.search);
  const params = new URLSearchParams();
  for (const key of ["query"]) if (current.get(key)) params.set(key, current.get(key));
  const data = new FormData(form);
  for (const key of ["category", "brand", "min_price", "max_price", "min_rating"]) if (data.get(key)) params.set(key, data.get(key));
  if (form.elements.in_stock.checked) params.set("in_stock", "true");
  const sort = document.getElementById("sort-filter")?.value || "featured";
  if (sort !== "featured") params.set("sort", sort);
  navigate(`/products${params.size ? `?${params}` : ""}`);
}
function addProduct(productId, quantity = 1) {
  const product = productMap().get(String(productId));
  if (!product) { toast("That product is no longer available."); return; }
  try { state.cart = window.SmartCartCore.addItem(state.cart, product, quantity); saveCart(); updateCounts(); toast(`${product.title} added to your cart.`); }
  catch (error) { toast(error.message); }
}
function toggleWishlist(productId) {
  const id = String(productId);
  state.wishlist = state.wishlist.includes(id) ? state.wishlist.filter((item) => item !== id) : [...state.wishlist, id];
  saveWishlist(); updateCounts();
  if (routeInfo().page === "wishlist") renderWishlist(); else {
    document.querySelectorAll(`[data-wishlist-toggle="${CSS.escape(id)}"]`).forEach((button) => {
      const selected = state.wishlist.includes(id); button.classList.toggle("selected", selected); button.textContent = selected ? "♥" : "♡";
      button.setAttribute("aria-label", `${selected ? "Remove from" : "Add to"} wishlist`);
    });
  }
  toast(state.wishlist.includes(id) ? "Saved to your wishlist." : "Removed from your wishlist.");
}
async function placeOrder(form) {
  const customer = Object.fromEntries(new FormData(form).entries());
  const items = state.cart.map((line) => ({ product_id: line.product_id, quantity: line.quantity }));
  const button = form.querySelector('[type="submit"]'); button.disabled = true; button.textContent = "Saving demo order…";
  try {
    const result = await request("/api/orders", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ customer, items }) });
    state.cart = []; saveCart();
    const refreshed = await requestProducts({ sort: "featured" }); mergeProducts(refreshed.products);
    navigate(`/order-confirmation/${encodeURIComponent(result.order.order_id)}`);
  } catch (error) { toast(error.message); button.disabled = false; button.textContent = `Place demo order · ${money(cartSummary().total)}`; }
}
function handleClick(event) {
  const target = event.target.closest("button, a"); if (!target) return;
  if (target.matches("a[data-nav]")) { event.preventDefault(); navigate(target.getAttribute("href")); return; }
  if (target.id === "mobile-nav-toggle") {
    const nav = document.getElementById("main-nav"); const open = nav.classList.toggle("open"); target.setAttribute("aria-expanded", String(open)); return;
  }
  if (target.dataset.addToCart) { addProduct(target.dataset.addToCart, target.hasAttribute("data-use-detail-quantity") ? Math.max(1, Number(document.getElementById("detail-quantity")?.value) || 1) : 1); return; }
  if (target.dataset.wishlistToggle) { toggleWishlist(target.dataset.wishlistToggle); return; }
  if (target.dataset.detailQuantity) { const input = document.getElementById("detail-quantity"); input.value = String(Math.max(1, Math.min(Number(input.max) || 1, (Number(input.value) || 1) + Number(target.dataset.detailQuantity)))); return; }
  if (target.dataset.cartChange) {
    const product = productMap().get(target.dataset.productId); const item = state.cart.find((line) => line.product_id === target.dataset.productId);
    if (!product || !item) return;
    try { state.cart = window.SmartCartCore.setQuantity(state.cart, product, item.quantity + Number(target.dataset.cartChange)); saveCart(); renderCart(); updateCounts(); }
    catch (error) { toast(error.message); }
    return;
  }
  if (target.dataset.cartRemove) { state.cart = window.SmartCartCore.removeItem(state.cart, target.dataset.cartRemove); saveCart(); renderCart(); updateCounts(); toast("Item removed from your cart."); return; }
  if (target.hasAttribute("data-move-to-cart")) { addProduct(target.dataset.moveToCart); toggleWishlist(target.dataset.moveToCart); return; }
  if (target.hasAttribute("data-reset-filters")) { navigate("/products"); return; }
  if (target.hasAttribute("data-go-home")) navigate("/");
}
function handleSubmit(event) {
  const form = event.target;
  if (form.matches("[data-search-form]") || form.id === "header-search" || form.id === "mobile-search") { event.preventDefault(); submitSearch(form.querySelector('input[name="query"]').value); return; }
  if (form.id === "filters-form") { event.preventDefault(); applyFilters(form); return; }
  if (form.id === "checkout-form") { event.preventDefault(); placeOrder(form); }
}
function handleChange(event) {
  if (event.target.id === "sort-filter") { const form = document.getElementById("filters-form"); if (form) applyFilters(form); }
}
function handleInput(event) { if (event.target.matches('input[name="query"]')) loadSuggestions(event.target.value.trim()); }
function handleImageError(event) {
  const image = event.target;
  if (!(image instanceof HTMLImageElement) || !image.hasAttribute("data-product-image")) return;
  const fallback = image.dataset.fallback;
  if (fallback && !image.dataset.fallbackTried && image.src !== new URL(fallback, location.origin).href) {
    image.dataset.fallbackTried = "true"; image.src = fallback;
  } else {
    image.closest(".product-art")?.classList.add("image-error");
  }
}
async function boot() {
  try {
    const initial = await requestProducts({ sort: "featured" }); state.products = initial.products; state.categories = initial.categories;
    state.cart = window.SmartCartCore.reconcile(readList(CART_KEY), productMap()); saveCart();
    state.wishlist = readList(WISHLIST_KEY).map(String).filter((id) => productMap().has(id)); saveWishlist();
    document.addEventListener("click", handleClick); document.addEventListener("submit", handleSubmit); document.addEventListener("change", handleChange); document.addEventListener("input", handleInput);
    document.addEventListener("error", handleImageError, true);
    addEventListener("popstate", renderRoute); await renderRoute();
  } catch (error) { root.innerHTML = `<section class="error-panel"><h2>Smart Cart couldn't connect</h2><p>${escapeHtml(error.message)}</p><p>Restart the application from the Smart-Marketplace project directory and try again.</p></section>`; }
}
boot();
