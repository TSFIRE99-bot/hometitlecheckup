// Small helpers. Everything still works without JavaScript; this makes answers update instantly
// and remembers roadmap check marks on this device.

function store(get, key, value) {
  try { return get ? localStorage.getItem(key) : localStorage.setItem(key, value); } catch (e) { return null; }
}

// Larger text switch, remembered on this device only
(function () {
  var button = document.getElementById("big-text");
  if (!button) return;
  var root = document.documentElement;
  button.setAttribute("aria-pressed", root.classList.contains("big") ? "true" : "false");
  button.addEventListener("click", function () {
    var on = root.classList.toggle("big");
    button.setAttribute("aria-pressed", on ? "true" : "false");
    store(false, "bigText", on ? "1" : "0");
  });
})();

// Roadmap: check off steps; progress is saved in this browser only, per home and result
function initRoadmaps(scope) {
  scope.querySelectorAll("[data-roadmap]").forEach(function (map) {
    var key = "roadmap:" + map.getAttribute("data-roadmap");
    var done = {};
    try { done = JSON.parse(store(true, key) || "{}"); } catch (e) { done = {}; }
    var boxes = map.querySelectorAll("input[data-step]");
    function paint() {
      var count = 0;
      boxes.forEach(function (b) {
        b.closest(".t-step").classList.toggle("is-done", b.checked);
        if (b.checked) count++;
      });
      map.querySelector("[data-done]").textContent = count;
      map.querySelector("[data-fill]").style.width = (boxes.length ? 100 * count / boxes.length : 0) + "%";
    }
    boxes.forEach(function (b) {
      b.checked = !!done[b.getAttribute("data-step")];
      b.addEventListener("change", function (e) {
        e.stopPropagation();          // ticking a step is not an answer, so don't refresh the result
        done[b.getAttribute("data-step")] = b.checked;
        store(false, key, JSON.stringify(done));
        paint();
      });
    });
    paint();
  });
}
initRoadmaps(document);

// Forms marked data-live send their answers on every change and swap in the new result,
// so the page (and the map above it) doesn't reload. PDF buttons still submit normally.
document.querySelectorAll("form[data-live]").forEach(function (form) {
  var body = form.querySelector("[id$='-body']");
  var busy = null;
  function refresh() {
    if (busy) busy.abort();
    busy = new AbortController();
    var open = Array.prototype.map.call(body.querySelectorAll("details[id]"), function (d) { return d.open ? d.id : null; });
    body.setAttribute("aria-busy", "true");
    fetch(form.action, { method: "POST", body: new FormData(form), headers: { "X-Partial": "1" }, signal: busy.signal })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function (html) {
        body.innerHTML = html;
        body.removeAttribute("aria-busy");
        open.forEach(function (id) { var d = id && document.getElementById(id); if (d) d.open = true; });
        initRoadmaps(body);
      })
      .catch(function (e) { if (e.name !== "AbortError") form.submit(); });
  }
  form.addEventListener("change", function (e) {
    if (e.target.hasAttribute("data-step")) return;
    refresh();
  });
  // range sliders: show the number while dragging
  form.addEventListener("input", function (e) {
    if (e.target.type === "range" && e.target.previousElementSibling) e.target.previousElementSibling.textContent = e.target.value;
  });
});
