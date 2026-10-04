const { formatPrice } = require("./utils");

const orders = Array.from({ length: 57 }, (_, i) => ({ id: i + 1, customerId: (i % 5) + 1, total: (i + 1) * 10 }));

// Returns every order.
function listOrders() {
  return orders;
}

function orderSummary(order) {
  return `Order #${order.id}: ${formatPrice(order.total)}`;
}

module.exports = { listOrders, orderSummary };
