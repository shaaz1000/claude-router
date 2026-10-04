// The original takes about 1.9 s on this input on the reference machine; a linear version takes about 7 ms.
const assert = require("assert"); const { load, run } = require("./_lib");
run(() => {
  const { salesReport } = load("report.js"); const C = 5000, N = 40000;
  const customers = Array.from({ length: C }, (_, i) => ({ id: i + 1, name: "c" + i })).filter((c) => c.id % 50 !== 0);
  const orders = Array.from({ length: N }, (_, i) => ({ customerId: ((i * 7919) % C) + 1, total: i % 97 }));
  const names = new Map(customers.map((c) => [c.id, c.name])); const m = new Map();
  for (const o of orders) { let r = m.get(o.customerId); if (!r) { r = { customerId: o.customerId, name: names.get(o.customerId) || "unknown", orders: 0, total: 0 }; m.set(o.customerId, r); } r.orders++; r.total += o.total; }
  const expected = [...m.values()].sort((a, b) => b.total - a.total || a.customerId - b.customerId);
  const t = Date.now(); const got = salesReport(customers, orders); const ms = Date.now() - t;
  assert.deepStrictEqual(got, expected, "output changed"); assert.ok(ms < 400, `still slow: ${ms} ms (limit 400 ms)`);
});
