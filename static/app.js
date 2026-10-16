

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

function storedTab() {
  try {
    var v = localStorage.getItem("dro-tab");
    return TABS[v] ? v : null;
  } catch (e) { return null; }
}

function setTab(which) {
  var t = TABS[which] || TABS.dispatch;
  ACTIVE_TAB = t.key;
  $$(".tab").forEach(function (b) {
    var active = b.id === "tabbtn-" + t.key;
    b.classList.toggle("active", active);
    b.setAttribute("aria-selected", active ? "true" : "false");
  });
  Object.keys(TABS).forEach(function (id) {
    var p = $("#" + TABS[id].panel);
    if (!p) return;
    var show = id === t.key;
    p.classList.toggle("hidden", !show);
    p.classList.toggle("is-active", show);
  });
  try { localStorage.setItem("dro-tab", t.key); } catch (e) {   }
  clearTabError();
  try {
    if (!t.inited && t.init) { t.inited = true; t.init(); }
  } catch (e) { showTabError(t, e); return; }
  try {
    if (t.onShow) t.onShow();
  } catch (e) { showTabError(t, e); }
}

function showTabError(tab, err) {
  var msg = (err && err.message) ? err.message : String(err);
  if (window.console) console.error("[tab: " + tab.key + "]", err && err.stack || msg);
  var sec = $("#" + tab.panel);
  if (!sec) return;
  clearTabError();
  var d = document.createElement("div");
  d.className = "panel col-12 tab-error";
  var title = document.createElement("div");
  title.className = "panel-title";
  title.innerHTML = "<span>! ERROR - " + tab.title +
    " FAILED TO LOAD</span><span class=\"winbtns\">[ _ ][ X ]</span>";
  var body = document.createElement("div");
  body.className = "panel-body";
  var msgBox = document.createElement("div");
  msgBox.className = "empty-state";
  msgBox.textContent = msg.toUpperCase();
  var retry = document.createElement("button");
  retry.className = "btn";
  retry.textContent = "RETRY";
  retry.addEventListener("click", function () {
    tab.inited = false;
    setTab(tab.key);
  });
  body.appendChild(msgBox);
  body.appendChild(retry);
  d.appendChild(title);
  d.appendChild(body);
  sec.insertBefore(d, sec.firstChild);
}

function clearTabError() {
  $$(".tab-error").forEach(function (el) { el.remove(); });
}

function setLoading(on) {
  $$("[data-loading]").forEach(function (el) {
    el.classList.toggle("hidden", !on);
  });
}

function locById(id) {
  for (var i = 0; i < S.locations.length; i++) {
    if (S.locations[i].id === id) return S.locations[i];
  }
  return null;
}

function computeFit() {
  var xs = [], ys = [];
  S.locations.forEach(function (l) { xs.push(l.x); ys.push(l.y); });
  var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs);
  var miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
  var w = Math.max(1, maxx - minx), h = Math.max(1, maxy - miny);
  var s = Math.min((CANV.W - 2 * CANV.PAD) / w, (CANV.H - 2 * CANV.PAD) / h);
  var ox = (CANV.W - w * s) / 2 - minx * s;
  var oy = (CANV.H - h * s) / 2 - miny * s;
  S.fit = { s: s, ox: ox, oy: oy };
}

function px(id) {
  var l = locById(id);
  if (!l) return { x: 0, y: 0 };
  return { x: S.fit.ox + l.x * S.fit.s, y: S.fit.oy + l.y * S.fit.s };
}

function applyViewBox() {
  $("#map").setAttribute("viewBox",
    S.vb.x + " " + S.vb.y + " " + S.vb.w + " " + S.vb.h);
}
function clampVB() {
  S.vb.w = Math.max(160, Math.min(CANV.W, S.vb.w));
  S.vb.h = Math.max(112, Math.min(CANV.H, S.vb.h));
  S.vb.x = Math.max(0, Math.min(CANV.W - S.vb.w, S.vb.x));
  S.vb.y = Math.max(0, Math.min(CANV.H - S.vb.h, S.vb.y));
}
function resetZoom() {
  S.vb = { x: 0, y: 0, w: CANV.W, h: CANV.H };
  applyViewBox();
}