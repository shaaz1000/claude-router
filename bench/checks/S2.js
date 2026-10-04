const assert = require("assert"); const { load, run } = require("./_lib");
run(() => {
  const { applyCoupon } = load("cart.js"); assert.strictEqual(typeof applyCoupon, "function");
  const cart = () => ({ id: "x", items: [{ price: 100 }], subtotal: 100, shipping: 5 });
  const a = applyCoupon(cart(), "SAVE10"); assert.strictEqual(a.subtotal, 90); assert.strictEqual(a.shipping, 5);
  const b = applyCoupon(cart(), "FREESHIP"); assert.strictEqual(b.shipping, 0); assert.strictEqual(b.subtotal, 100);
  assert.throws(() => applyCoupon(cart(), "NOPE"), Error);
});
