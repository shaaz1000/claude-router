// Answer check: the reply text is passed in the file named by BENCH_REPLY. The working copy must be unchanged.
const assert = require("assert"); const fs = require("fs"); const { load, run } = require("./_lib");
run(() => {
  const expected = "cr-me-br-l-e-co";
  assert.strictEqual(load("utils.js").slugify("Crème Brûlée & Co."), expected, "utils.js was changed");
  assert.ok(fs.readFileSync(process.env.BENCH_REPLY, "utf8").includes(expected), "reply does not contain " + expected);
});
