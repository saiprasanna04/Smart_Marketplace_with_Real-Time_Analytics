/* Pure shopping-cart operations shared by the browser app and Node checks. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SmartCartCore = api;
})(globalThis, function () {
  "use strict";

  function copyCart(cart) {
    return (Array.isArray(cart) ? cart : []).map((item) => ({
      product_id: String(item.product_id),
      quantity: Number(item.quantity),
    })).filter((item) => item.product_id && Number.isInteger(item.quantity) && item.quantity > 0);
  }

  function addItem(cart, product, quantity = 1) {
    if (!product || Number(product.stock) <= 0) {
      throw new Error("This product is out of stock.");
    }
    if (!Number.isInteger(quantity) || quantity < 1) {
      throw new Error("Quantity must be a positive whole number.");
    }
    const next = copyCart(cart);
    const productId = String(product.product_id);
    const existing = next.find((item) => item.product_id === productId);
    const newQuantity = (existing ? existing.quantity : 0) + quantity;
    if (newQuantity > Number(product.stock)) {
      throw new Error(`Only ${Number(product.stock)} units are currently available.`);
    }
    if (existing) existing.quantity = newQuantity;
    else next.push({ product_id: productId, quantity: newQuantity });
    return next;
  }

  function setQuantity(cart, product, quantity) {
    const productId = String(product.product_id);
    if (!Number.isInteger(quantity)) {
      throw new Error("Quantity must be a whole number.");
    }
    if (quantity <= 0) return removeItem(cart, productId);
    if (quantity > Number(product.stock)) {
      throw new Error(`Only ${Number(product.stock)} units are currently available.`);
    }
    const next = copyCart(cart);
    const existing = next.find((item) => item.product_id === productId);
    if (existing) existing.quantity = quantity;
    else next.push({ product_id: productId, quantity });
    return next;
  }

  function removeItem(cart, productId) {
    return copyCart(cart).filter((item) => item.product_id !== String(productId));
  }

  function itemCount(cart) {
    return copyCart(cart).reduce((total, item) => total + item.quantity, 0);
  }

  function summarize(cart, productsById) {
    const lines = [];
    let subtotalMinor = 0;
    let originalMinor = 0;
    for (const item of copyCart(cart)) {
      const product = productsById.get(item.product_id);
      if (!product) continue;
      const quantity = Math.min(item.quantity, Number(product.stock));
      if (quantity <= 0) continue;
      const priceMinor = Math.round(Number(product.price) * 100);
      const originalUnitMinor = Math.max(priceMinor, Math.round(Number(product.original_price ?? product.price) * 100));
      const lineSubtotalMinor = priceMinor * quantity;
      const lineOriginalMinor = originalUnitMinor * quantity;
      subtotalMinor += lineSubtotalMinor;
      originalMinor += lineOriginalMinor;
      lines.push({
        product,
        product_id: item.product_id,
        quantity,
        unit_price: priceMinor / 100,
        line_total: lineSubtotalMinor / 100,
        original_line_total: lineOriginalMinor / 100,
        savings: (lineOriginalMinor - lineSubtotalMinor) / 100,
      });
    }
    const itemCount = lines.reduce((total, line) => total + line.quantity, 0);
    const deliveryMinor = subtotalMinor >= 199900 || subtotalMinor === 0 ? 0 : 9900;
    const subtotal = subtotalMinor / 100;
    const delivery = deliveryMinor / 100;
    const savings = (originalMinor - subtotalMinor) / 100;
    return {
      lines,
      item_count: itemCount,
      subtotal,
      savings,
      delivery,
      total: (subtotalMinor + deliveryMinor) / 100,
    };
  }

  function reconcile(cart, productsById) {
    return copyCart(cart).flatMap((item) => {
      const product = productsById.get(item.product_id);
      if (!product || Number(product.stock) <= 0) return [];
      return [{
        product_id: item.product_id,
        quantity: Math.min(item.quantity, Number(product.stock)),
      }];
    });
  }

  return Object.freeze({ addItem, setQuantity, removeItem, itemCount, summarize, reconcile });
});
