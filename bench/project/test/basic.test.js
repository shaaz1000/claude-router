const test = require("node:test");
const assert = require("node:assert");
const { getUser, greet } = require("../api");
const { slugify, formatPrice } = require("../utils");
const { listOrders, orderSummary } = require("../orders");
const { addItem, cartSummary } = require("../cart");
const { salesReport } = require("../report");

test("greet uses the user lookup", () => {
  assert.strictEqual(greet(1), "Hello, Asha");
  assert.strictEqual(getUser(99), null);
});

test("slugify and formatPrice", () => {
  assert.strictEqual(slugify("Hello World"), "hello-world");
  assert.strictEqual(formatPrice(3), "$3.00");
});

test("orders", () => {
  assert.ok(listOrders());
  assert.strictEqual(orderSummary({ id: 2, total: 20 }), "Order #2: $20.00");
});

test("cart", async () => {
  const cart = await addItem("t1", { name: "pen", price: 2 });
  assert.strictEqual(cartSummary(cart), "1 items, subtotal $2.00, shipping $5.00");
});

test("sales report", () => {
  const rows = salesReport([{ id: 1, name: "Asha" }], [{ customerId: 1, total: 5 }, { customerId: 1, total: 7 }]);
  assert.deepStrictEqual(rows, [{ customerId: 1, name: "Asha", orders: 2, total: 12 }]);
});
