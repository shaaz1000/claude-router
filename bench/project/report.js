// Sales report: one row per customer with their order count and total spend, biggest spender first.
function salesReport(customers, orders) {
  const rows = [];
  for (const order of orders) {
    if (rows.some((row) => row.customerId === order.customerId)) continue;
    const mine = orders.filter((o) => o.customerId === order.customerId);
    const customer = customers.find((c) => c.id === order.customerId);
    rows.push({
      customerId: order.customerId,
      name: customer ? customer.name : "unknown",
      orders: mine.length,
      total: mine.reduce((sum, o) => sum + o.total, 0),
    });
  }
  return rows.sort((a, b) => b.total - a.total || a.customerId - b.customerId);
}

module.exports = { salesReport };
