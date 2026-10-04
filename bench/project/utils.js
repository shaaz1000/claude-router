// Lowercases, turns every run of characters outside a-z and 0-9 into one dash, trims dashes.
function slugify(text) {
  return String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function formatPrice(amount) {
  return `$${Number(amount).toFixed(2)}`;
}

module.exports = { slugify, formatPrice };
