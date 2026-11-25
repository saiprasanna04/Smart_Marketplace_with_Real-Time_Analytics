const test = require("node:test");
const assert = require("node:assert/strict");
const Cart = require("../storefront/assets/cart-core.js");

const product = { product_id: "P1001", title: "Sample", price: 12.5, stock: 4 };

test("adding merges quantities and counts cart units", () => {
  const first = Cart.addItem([], product, 2);
  const second = Cart.addItem(first, product, 1);
  assert.deepEqual(second, [{ product_id: "P1001", quantity: 3 }]);
  assert.equal(Cart.itemCount(second), 3);
});

test("quantity changes enforce stock and remove on decrement to zero", () => {
  const cart = Cart.addItem([], product, 1);
  assert.throws(() => Cart.addItem(cart, product, 4), /Only 4 units/);
  assert.deepEqual(Cart.setQuantity(cart, product, 2), [{ product_id: "P1001", quantity: 2 }]);
  assert.deepEqual(Cart.setQuantity(cart, product, 0), []);
});

test("summary calculates subtotal and total from catalogue prices", () => {
  const cart = Cart.addItem([], product, 3);
  const summary = Cart.summarize(cart, new Map([[product.product_id, product]]));
  assert.equal(summary.item_count, 3);
  assert.equal(summary.subtotal, 37.5);
  assert.equal(summary.delivery, 99);
  assert.equal(summary.total, 136.5);
});

test("summary calculates sale savings without floating point drift and waives delivery above the threshold", () => {
  const sale = { ...product, price: 1999.99, original_price: 2499.99 };
  const summary = Cart.summarize([{ product_id: sale.product_id, quantity: 1 }], new Map([[sale.product_id, sale]]));
  assert.equal(summary.savings, 500);
  assert.equal(summary.delivery, 0);
  assert.equal(summary.total, 1999.99);
});

test("reconcile drops missing products and clamps quantity to stock", () => {
  const products = new Map([[product.product_id, { ...product, stock: 2 }]]);
  const cart = [
    { product_id: "P1001", quantity: 4 },
    { product_id: "MISSING", quantity: 2 },
  ];
  assert.deepEqual(Cart.reconcile(cart, products), [{ product_id: "P1001", quantity: 2 }]);
});
