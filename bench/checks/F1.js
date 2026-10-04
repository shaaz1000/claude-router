const assert = require("assert"); const fs = require("fs"); const path = require("path"); const { load, run } = require("./_lib");
run(() => {
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.name === "node_modules" || e.name.startsWith(".") ? [] : e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
  for (const f of walk(process.cwd()).filter((f) => f.endsWith(".js"))) assert.ok(!fs.readFileSync(f, "utf8").includes("getUser"), `getUser still in ${path.basename(f)}`);
  const api = load("api.js");
  assert.strictEqual(typeof api.fetchUser, "function"); assert.strictEqual(api.fetchUser(2).name, "Ben"); assert.strictEqual(api.greet(1), "Hello, Asha");
});
