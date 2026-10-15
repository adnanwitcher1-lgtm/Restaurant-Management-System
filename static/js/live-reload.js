// Reloads the page when orders change in this branch (used on the Orders list).
(function () {
  var proto = location.protocol === "https:" ? "wss://" : "ws://";
  function connect() {
    var ws = new WebSocket(proto + location.host + "/ws/orders/");
    ws.onmessage = function () {
      location.reload();
    };
    ws.onclose = function () {
      setTimeout(connect, 3000);
    };
  }
  connect();
})();
