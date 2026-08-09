(function () {
  "use strict";

  if (window.__LUMA_INSTITUTIONAL_SURFACE__) return;
  window.__LUMA_INSTITUTIONAL_SURFACE__ = true;

  var surface = String(document.body && document.body.dataset.lumaSurface || "").toLowerCase();
  var localOperator = location.protocol === "file:"
    || ["127.0.0.1", "localhost", "::1"].indexOf(location.hostname) >= 0;
  var publicReview = !localOperator;

  document.documentElement.classList.toggle("luma-public-review", publicReview);
  document.documentElement.setAttribute("data-luma-audience", publicReview ? "public-review" : "local-operator");
  window.LUMA_PUBLIC_REVIEW = publicReview;

  function makeProofline(config) {
    var rail = document.createElement("aside");
    rail.className = "lis-proofline";
    rail.setAttribute("role", "note");
    rail.setAttribute("aria-label", "Evidence and authority posture");
    rail.innerHTML = [
      "<span>", config.label, "</span>",
      '<span data-tone="', config.evidenceTone || "good", '"><small>Evidence class</small><strong>', config.evidence, "</strong></span>",
      '<span data-tone="', config.runtimeTone || "paper", '"><small>Runtime boundary</small><strong>', config.runtime, "</strong></span>",
      '<span data-tone="warn"><small>Authority</small><strong>', config.authority, "</strong></span>",
    ].join("");
    return rail;
  }

  var configs = {
    home: {
      label: "Decision fabric",
      evidence: "First-party · replayable",
      runtime: "Public review surface",
      authority: "Pilot and promotion human-gated",
    },
    mission: {
      label: "Mission truth",
      evidence: "Measured · source-labeled",
      runtime: "Observation and review",
      authority: "No automatic promotion",
    },
    quant: {
      label: "Research control",
      evidence: "Replay · paper · modeled",
      runtime: "No live order authority",
      authority: "Claims remain bounded",
    },
    grants: {
      label: "Funding evidence",
      evidence: "Discovery · draft · receipt",
      runtime: publicReview ? "Public review · read-only" : "Local operator workspace",
      authority: "Final submission human-only",
    },
    trade: {
      label: "Trading evidence",
      evidence: "Paper/shadow + historical receipts",
      runtime: "Read-only public posture",
      authority: "Live orders not authorized here",
    },
    review: {
      label: "Reviewer path",
      evidence: "First-party · source-bounded",
      runtime: "Static public review",
      authority: "Promotion and submission human-only",
    },
  };

  function insertProofline() {
    var config = configs[surface];
    if (!config || document.querySelector(".lis-proofline")) return;
    var rail = makeProofline(config);
    var anchor = null;

    if (surface === "home") anchor = document.querySelector(".home .nav");
    if (surface === "mission") anchor = document.querySelector(".stage .top-bar");
    if (surface === "grants") anchor = document.querySelector(".lc-stage .lc-topbar");
    if (surface === "trade") anchor = document.querySelector(".luma-statusbar");
    if (surface === "review") anchor = document.querySelector(".lis-review-header");

    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(rail, anchor.nextSibling);
    } else if (surface === "grants") {
      var stage = document.querySelector(".lc-stage");
      if (stage) stage.insertBefore(rail, stage.firstChild);
    }
  }

  function enforcePublicReview() {
    if (!publicReview || surface !== "grants") return;
    var mutationIds = [
      "draft-all", "opps-autopilot", "regenerate", "approve-btn", "regen-btn",
      "prepare-btn", "autofill-btn", "submitted-btn",
    ];
    mutationIds.forEach(function (id) {
      var button = document.getElementById(id);
      if (!button) return;
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      button.setAttribute("title", "Local authenticated operator action only");
    });
  }

  function repairStaticRoutes() {
    var replacements = {
      "social_pro_dashboard.html": "/proof_to_pilot.html",
      "lumaq_brain_command_center.html": "/quant_lab.html",
      "vps_growth_proof_3d.html": "/evidence/",
    };
    document.querySelectorAll("a[href]").forEach(function (link) {
      var raw = link.getAttribute("href") || "";
      var clean = raw.split("#")[0].split("?")[0].replace(/^\.\//, "");
      if (Object.prototype.hasOwnProperty.call(replacements, clean)) {
        link.setAttribute("href", replacements[clean]);
        link.setAttribute("data-route-repaired", clean);
      }
    });
  }

  function start() {
    insertProofline();
    enforcePublicReview();
    repairStaticRoutes();

    if (surface === "grants" && publicReview) {
      var observer = new MutationObserver(function () {
        enforcePublicReview();
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
