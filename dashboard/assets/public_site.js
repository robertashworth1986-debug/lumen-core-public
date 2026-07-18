(function () {
  "use strict";

  document.documentElement.classList.add("js");

  function setText(selector, value) {
    document.querySelectorAll(selector).forEach(function (node) {
      node.textContent = value;
    });
  }

  function setTone(selector, tone) {
    document.querySelectorAll(selector).forEach(function (node) {
      node.classList.remove("good", "warn", "bad");
      node.classList.add(tone);
    });
  }

  function renderFabricStatus(detail) {
    var mode = String(detail && detail.mode || "OFFLINE").toUpperCase();
    var freshness = String(detail && detail.freshness || "OFFLINE").toUpperCase();
    var modeTone = mode === "LIVE" || mode === "PAPER" ? "warn" :
      mode === "SHADOW" || mode === "DISARMED" ? "good" : "bad";
    var freshnessTone = freshness === "DATA FRESH" ? "good" :
      freshness === "DATA STALE" ? "warn" : "bad";

    setText("[data-runtime-state]", mode);
    setTone("[data-runtime-state]", modeTone);
    setText("[data-freshness-state]", freshness);
    setTone("[data-freshness-state]", freshnessTone);

    var snapshot = detail && detail.snapshot;
    var generated = snapshot && snapshot.generated_utc;
    setText(
      "[data-runtime-note]",
      generated
        ? "Public runtime snapshot " + String(generated) + ". Evidence claims remain bounded by their capsule."
        : "Runtime telemetry is unavailable. Static public proof and review materials remain available."
    );
  }

  window.addEventListener("luma:fabric-status", function (event) {
    renderFabricStatus(event.detail || {});
  });

  document.querySelectorAll("[data-current-year]").forEach(function (node) {
    node.textContent = String(new Date().getUTCFullYear());
  });

  document.querySelectorAll("[data-copy-text]").forEach(function (button) {
    button.addEventListener("click", async function () {
      var value = button.getAttribute("data-copy-text") || "";
      var original = button.textContent;
      try {
        await navigator.clipboard.writeText(value);
        button.textContent = "Copied";
      } catch (_) {
        button.textContent = "Copy failed";
      }
      setTimeout(function () {
        button.textContent = original;
      }, 1800);
    });
  });

  setTimeout(function () {
    document.querySelectorAll("[data-runtime-state]").forEach(function (node) {
      if (node.textContent.trim() === "CHECKING") {
        node.textContent = "STATIC REVIEW";
        node.classList.remove("warn", "bad");
        node.classList.add("good");
      }
    });
  }, 6500);
}());
