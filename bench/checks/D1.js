const assert = require("assert"); const { load, run } = require("./_lib");
run(async () => {
  const { addItem, getCart } = load("cart.js");
  await Promise.all(Array.from({ length: 40 }, (_, i) => addItem("race", { name: "item" + i, price: 1 })));
  await Promise.all([addItem("other", { name: "a", price: 3 }), addItem("other", { name: "b", price: 4 })]);
  const cart = await getCart("race"); assert.strictEqual(cart.items.length, 40, `kept ${cart.items.length} of 40 items`); assert.strictEqual(cart.subtotal, 40);
  const other = await getCart("other"); assert.strictEqual(other.items.length, 2); assert.strictEqual(other.subtotal, 7);
});
