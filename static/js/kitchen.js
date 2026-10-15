(function () {
  var box = document.getElementById("kitchen-columns");
  if (!box) return;
  var dot = document.getElementById("live-dot");
  var text = document.getElementById("live-text");

  function setLive(on) {
    dot.className =
      "bi bi-circle-fill " + (on ? "text-success" : "text-secondary");
    text.textContent = on ? "Live" : "Reconnecting...";
  }

  function refresh() {
    fetch(box.dataset.cardsUrl, { credentials: "same-origin" })
      .then(function (r) {
        return r.text();
      })
      .then(function (html) {
        box.innerHTML = html;
      });
  }

  box.addEventListener("click", function (e) {
    var btn = e.target.closest(".k-action");
    if (!btn) return;
    btn.disabled = true;
    fetch("/kitchen/" + btn.dataset.id + "/status/", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": box.dataset.csrf },
      body: new URLSearchParams({ status: btn.dataset.status }),
    }).then(refresh);
  });

  function connect() {
    var proto = location.protocol === "https:" ? "wss://" : "ws://";
    var ws = new WebSocket(proto + location.host + "/ws/orders/");
    ws.onopen = function () {
      setLive(true);
      refresh();
    };
    ws.onmessage = refresh;
    ws.onclose = function () {
      setLive(false);
      setTimeout(connect, 2000);
    };
  }
  connect();
})();
