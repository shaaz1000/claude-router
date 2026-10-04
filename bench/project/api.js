const users = [{ id: 1, name: "Asha" }, { id: 2, name: "Ben" }];

function getUser(id) {
  return users.find((u) => u.id === id) || null;
}

function greet(id) {
  const user = getUser(id);
  return user ? `Hello, ${user.name}` : "Hello, guest";
}

module.exports = { getUser, greet };
