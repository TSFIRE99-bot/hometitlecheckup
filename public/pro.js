// HomeKeep Pro: busy states for forms. The button that submitted a form shows a spinner and, if it has
// data-busy-label, new text; a second click while the page is loading does nothing (no duplicate uploads or
// follow-ups). Buttons are never disabled, so the clicked button's name and value still reach the server.
(function () {
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form.dataset.busy === "1") { event.preventDefault(); return; }
    if (form.method.toLowerCase() !== "post") return;
    form.dataset.busy = "1";
    form.setAttribute("aria-busy", "true");
    var button = event.submitter || form.querySelector("button");
    if (!button) return;
    button.classList.add("is-busy");
    if (button.dataset.busyLabel) {
      button.dataset.label = button.textContent;
      button.textContent = button.dataset.busyLabel;
    }
  });

  // The landing page's cost calculator: the firm's own numbers, worked out here, never sent anywhere.
  document.querySelectorAll("[data-calc]").forEach(function (form) {
    var out = form.parentElement;
    function update() {
      var n = function (name) { var v = Number(form.elements[name].value); return isFinite(v) && v > 0 ? v : 0; };
      var hours = n("matters") * n("minutes") / 60;
      out.querySelector('[data-out="hours"]').textContent = hours.toLocaleString(undefined, { maximumFractionDigits: 1 });
      out.querySelector('[data-out="dollars"]').textContent = Math.round(hours * n("rate")).toLocaleString();
    }
    form.addEventListener("input", update);
    update();
  });

  // Coming back with the browser's Back button can restore a page mid-submit; reset it.
  window.addEventListener("pageshow", function () {
    document.querySelectorAll("form[aria-busy]").forEach(function (form) {
      delete form.dataset.busy;
      form.removeAttribute("aria-busy");
      form.querySelectorAll(".is-busy").forEach(function (button) {
        button.classList.remove("is-busy");
        if (button.dataset.label) button.textContent = button.dataset.label;
      });
    });
  });
})();
