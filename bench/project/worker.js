// Payment worker: moves balance between accounts. Each account has a mutex.
class Mutex {
  constructor() { this.locked = false; this.waiters = []; }
  async acquire() {
    if (!this.locked) { this.locked = true; return; }
    await new Promise((resolve) => this.waiters.push(resolve));
  }
  release() {
    const next = this.waiters.shift();
    if (next) next(); else this.locked = false;
  }
}

const accounts = { a: { balance: 100, lock: new Mutex() }, b: { balance: 100, lock: new Mutex() } };
const tick = () => new Promise((r) => setImmediate(r));

async function transfer(from, to, amount) {
  await accounts[from].lock.acquire();
  await tick();                               // simulates a database read
  await accounts[to].lock.acquire();
  try {
    accounts[from].balance -= amount;
    accounts[to].balance += amount;
  } finally {
    accounts[to].lock.release();
    accounts[from].lock.release();
  }
}

// Runs n transfers, alternating direction.
async function run(n) {
  const jobs = [];
  for (let i = 0; i < n; i++) jobs.push(i % 2 ? transfer("a", "b", 1) : transfer("b", "a", 1));
  await Promise.all(jobs);
  return accounts.a.balance + accounts.b.balance;
}

module.exports = { transfer, run, accounts };
