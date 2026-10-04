// Shared by the hidden checks. Each check runs with the task's working copy as cwd and exits 0 on pass.
const path = require("path");
exports.load = (name) => require(path.join(process.cwd(), name));
exports.run = async (fn) => {
  const timer = setTimeout(() => { console.log("FAIL: timed out"); process.exit(1); }, 8000);
  try { await fn(); clearTimeout(timer); console.log("PASS"); process.exit(0); }
  catch (e) { clearTimeout(timer); console.log("FAIL:", e && e.message ? e.message.split("\n")[0] : e); process.exit(1); }
};
