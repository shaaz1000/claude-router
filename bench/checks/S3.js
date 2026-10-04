const assert = require("assert"); const { load, run } = require("./_lib");
run(() => {
  const { formatPrice } = load("utils.js"); const { orderSummary } = load("orders.js"); const { cartSummary } = load("cart.js");
  assert.strictEqual(formatPrice(12.5), "$12.50"); assert.strictEqual(formatPrice(12.5, "USD"), "$12.50");
  assert.strictEqual(formatPrice(12.5, "EUR"), "€12.50"); assert.strictEqual(formatPrice(12.5, "GBP"), "£12.50");
  assert.strictEqual(orderSummary({ id: 2, total: 20 }), "Order #2: $20.00");
  assert.strictEqual(orderSummary({ id: 2, total: 20 }, { currency: "EUR" }), "Order #2: €20.00");
  const cart = { items: [{}, {}], subtotal: 8, shipping: 5 };
  assert.strictEqual(cartSummary(cart), "2 items, subtotal $8.00, shipping $5.00");
  assert.strictEqual(cartSummary(cart, { currency: "GBP" }), "2 items, subtotal £8.00, shipping £5.00");
});
