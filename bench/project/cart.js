const { formatPrice } = require("./utils");

// Simulated database: every read and write is asynchronous and returns a copy.
const rows = new Map();
const delay = () => new Promise((resolve) => setImmediate(resolve));
const db = {
  async load(id) { await delay(); return JSON.parse(JSON.stringify(rows.get(id) || { id, items: [], subtotal: 0, shipping: 5 })); },
  async save(id, cart) { await delay(); rows.set(id, JSON.parse(JSON.stringify(cart))); },
};

async function addItem(cartId, item) {
  const cart = await db.load(cartId);
  cart.items.push(item);
  cart.subtotal += item.price;
  await db.save(cartId, cart);
  return cart;
}

async function getCart(cartId) {
  return db.load(cartId);
}

function cartSummary(cart) {
  return `${cart.items.length} items, subtotal ${formatPrice(cart.subtotal)}, shipping ${formatPrice(cart.shipping)}`;
}

module.exports = { addItem, getCart, cartSummary };
