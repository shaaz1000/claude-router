const assert = require("assert"); const { load, run } = require("./_lib");
run(async () => {
  const { run: work, accounts } = load("worker.js");
  const total = await Promise.race([work(400), new Promise((_, rej) => setTimeout(() => rej(new Error("deadlock: run(400) did not finish in 3 s")), 3000))]);
  assert.strictEqual(total, 200); assert.strictEqual(accounts.a.balance + accounts.b.balance, 200);
});
