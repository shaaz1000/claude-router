const assert = require("assert"); const { load, run } = require("./_lib");
run(() => {
  const { listOrders } = load("orders.js");
  const p2 = listOrders({ page: 2, pageSize: 10 });
  assert.strictEqual(p2.items.length, 10); assert.strictEqual(p2.items[0].id, 11); assert.strictEqual(p2.total, 57); assert.strictEqual(p2.page, 2); assert.strictEqual(p2.pageSize, 10);
  const last = listOrders({ page: 6, pageSize: 10 }); assert.strictEqual(last.items.length, 7);
  for (const d of [listOrders(), listOrders({})]) { assert.strictEqual(d.items.length, 20); assert.strictEqual(d.page, 1); assert.strictEqual(d.pageSize, 20); assert.strictEqual(d.items[0].id, 1); }
});
