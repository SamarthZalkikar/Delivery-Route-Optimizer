

"use strict";

var CANV = { W: 720, H: 504, PAD: 48 };
var NODE_HALF = 9;
var DEPOT_HALF = 14;
var CHAR_W = 7.8, LBL_H = 13;
var REDUCED = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)").matches : false;

var S = {
  locations: [],
  roads: [],
  plan: {
    depot: 0,
    stops: [],
    result: null,
    stale: false
  },
  drivers: [],
  labelsMode: "all",
  showDist: false,
  legHi: -1,
  fit: { s: 1, ox: 0, oy: 0 },
  vb: { x: 0, y: 0, w: CANV.W, h: CANV.H }
};
var DEPOT_ID = 0;
var PRIORITY_LABEL = { 1: ["E", "badge-express", "EXPRESS"],
                      2: ["S", "badge-standard", "STANDARD"],
                      3: ["Y", "badge-economy", "ECONOMY"] };

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }
function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}
function svg(tag, attrs) {
  var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (var k in attrs) n.setAttribute(k, attrs[k]);
  return n;
}

var loaderTick = null;
function loader(on) {
  var box = $("#loader");
  if (!box) return;
  if (on) {
    box.classList.remove("hidden");
    box.setAttribute("aria-hidden", "false");
    var filled = 0;
    if (loaderTick) clearInterval(loaderTick);
    loaderTick = setInterval(function () {
      filled = (filled + 1) % 12;
      var bar = "";
      for (var i = 0; i < 11; i++) bar += i < filled ? "#" : ".";
      $("#loader-bar").textContent = "[" + bar + "]";
    }, 140);
  } else {
    if (loaderTick) clearInterval(loaderTick);
    loaderTick = null;
    box.classList.add("hidden");
    box.setAttribute("aria-hidden", "true");
  }
}

function toast(title, body, isError) {
  var root = $("#toast-root");
  var d = el("div", "toast" + (isError ? " error" : ""));
  d.setAttribute("role", isError ? "alertdialog" : "dialog");
  d.setAttribute("aria-label", title);
  var t = el("div", "t-title", (isError ? "! ERROR" : "OK") + ": " + title);
  var b = el("div", "t-body", body);
  var a = el("div", "t-actions");
  var ok = el("button", "btn btn-ok", "OK");
  ok.addEventListener("click", function () { root.removeChild(d); });
  a.appendChild(ok);
  d.appendChild(t); d.appendChild(b); d.appendChild(a);
  root.appendChild(d);
  ok.focus();
  setTimeout(function () { if (d.parentNode) root.removeChild(d); }, isError ? 9000 : 4000);
}

function api(path, opts) {
  opts = opts || {};
  return new Promise(function (resolve, reject) {
    loader(true);
    var init = { method: opts.method || "GET",
                 headers: { "Accept": "application/json" } };
    if (opts.body !== undefined && opts.method !== "GET") {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    fetch(path, init).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, body: j }; });
    }).then(function (res) {
      loader(false);
      if (res.ok) resolve(res.body);
      else reject(res.body.error || ("HTTP " + res.status));
    }).catch(function (e) {
      loader(false);
      reject(typeof e === "string" ? e : "network down");
    });
  });
}

function savePrefs() {
  try {
    localStorage.setItem("dro-prefs", JSON.stringify({
      stops: S.plan.stops, labelsMode: S.labelsMode,
      showDist: S.showDist, engine: $("#opt-engine") ? $("#opt-engine").value : "auto",
      prioFirst: $("#prio-first") ? $("#prio-first").checked : false
    }));
  } catch (e) {   }
}
function loadPrefs() {
  try {
    var p = JSON.parse(localStorage.getItem("dro-prefs") || "null");
    if (!p) return;
    if (Array.isArray(p.stops)) {
      S.plan.stops = p.stops.filter(function (id) {
        return typeof id === "number" && id > DEPOT_ID;
      });
    }
    if (p.labelsMode === "all" || p.labelsMode === "route" || p.labelsMode === "off") {
      S.labelsMode = p.labelsMode;
    }
    if (typeof p.showDist === "boolean") S.showDist = p.showDist;
    S._pEngine = p.engine; S._pPrio = p.prioFirst;
  } catch (e) {   }
}

var TABS = {
  dispatch: { key: "dispatch", title: "DISPATCH",   panel: "tab-dispatch",
              onShow: null, init: null, inited: true },
  orders:   { key: "orders",   title: "ORDERS",     panel: "tab-orders",
              onShow: null, init: null, inited: true },
  network:  { key: "network",  title: "NETWORK",    panel: "tab-network",
              onShow: null, init: null, inited: true },
  lab:      { key: "lab",      title: "ALGOS LAB",  panel: "tab-lab",
              onShow: null, init: null, inited: true },
  slime:    { key: "slime",    title: "SLIME LAB",  panel: "tab-slime",
              onShow: slimeOnShow, init: labInit, inited: false },
  dsamap:   { key: "dsamap",   title: "DSA MAP",    panel: "tab-dsamap",
              onShow: null, init: null, inited: true }
};
var ACTIVE_TAB = "dispatch";
var TAB_HASH_ALIAS = {
  "slime-lab": "slime", "algos-lab": "lab", "dsa-map": "dsamap",
  dispatch: "dispatch", orders: "orders", network: "network",
  lab: "lab", slime: "slime", dsamap: "dsamap"
};
var _errTrap = null;

function tabFromHash() {
  var h = (window.location.hash || "").replace(/^#/, "").toLowerCase();
  return TAB_HASH_ALIAS[h] || null;
}