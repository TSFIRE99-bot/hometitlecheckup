// Small helpers. Everything still works without JavaScript; this just makes answers update instantly.

// Larger text switch, remembered on this device only
(function () {
  var button = document.getElementById("big-text");
  if (!button) return;
  var root = document.documentElement;
  button.setAttribute("aria-pressed", root.classList.contains("big") ? "true" : "false");
  button.addEventListener("click", function () {
    var on = root.classList.toggle("big");
    button.setAttribute("aria-pressed", on ? "true" : "false");
    try { localStorage.setItem("bigText", on ? "1" : "0"); } catch (e) {}
  });
})();

// Forms marked data-live send their answers on every change and swap in the new result,
// so the page (and the map above it) doesn't reload. PDF buttons still submit normally.
document.querySelectorAll("form[data-live]").forEach(function (form) {
  var body = form.querySelector("[id$='-body']");
  var busy = null;
  function refresh() {
    if (busy) busy.abort();
    busy = new AbortController();
    var open = Array.prototype.map.call(body.querySelectorAll("details[id]"), function (d) { return d.open ? d.id : null; });
    fetch(form.action, { method: "POST", body: new FormData(form), headers: { "X-Partial": "1" }, signal: busy.signal })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function (html) {
        body.innerHTML = html;
        open.forEach(function (id) { var d = id && document.getElementById(id); if (d) d.open = true; });
      })
      .catch(function (e) { if (e.name !== "AbortError") form.submit(); });
  }
  form.addEventListener("change", refresh);
  // range sliders: show the number while dragging
  form.addEventListener("input", function (e) {
    if (e.target.type === "range" && e.target.previousElementSibling) e.target.previousElementSibling.textContent = e.target.value;
  });
});
