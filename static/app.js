

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
function zoomAt(cx, cy, factor) {
  var nw = S.vb.w * factor, nh = S.vb.h * factor;
  var dx = (cx - S.vb.x) / S.vb.w, dy = (cy - S.vb.y) / S.vb.h;
  S.vb.x = cx - dx * nw;
  S.vb.y = cy - dy * nh;
  S.vb.w = nw; S.vb.h = nh;
  clampVB();
  applyViewBox();
}

function candidates(half) {
  return [
    [half + 8, 4, "start"],
    [half + 8, -(half + 2), "start"],
    [0, -(half + 11), "middle"],
    [half + 8, half + 17, "start"],
    [0, half + 18, "middle"],
    [-(half + 8), 4, "end"],
    [-(half + 8), -(half + 2), "end"],
    [-(half + 8), half + 17, "end"]
  ];
}

function labelRect(cx, cy, cand, wtxt) {
  var dx = cand[0], dy = cand[1], anchor = cand[2];
  var left;
  if (anchor === "start") left = cx + dx;
  else if (anchor === "middle") left = cx + dx - wtxt / 2;
  else left = cx + dx - wtxt;
  var ty = cy + dy;
  return [left, ty - 10, left + wtxt, ty + 3];
}

function rectHit(a, b) {
  return a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
}
function segHitsRect(x1, y1, x2, y2, r) {

  var steps = Math.ceil(Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) / 10) + 1;
  for (var i = 0; i <= steps; i++) {
    var t = i / steps;
    var x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
    if (x > r[0] && x < r[2] && y > r[1] && y < r[3]) return true;
  }
  return false;
}

function shortCode(name) {
  var words = name.split(/\s+/);
  if (words.length >= 2) {
    return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
  }
  return name.replace(/[^A-Za-z0-9]/g, "").substring(0, 2).toUpperCase() || "??";
}

function roadSegs() {
  var out = [];
  S.roads.forEach(function (r) {
    var a = px(r.u), b = px(r.v);
    out.push([a.x, a.y, b.x, b.y]);
  });
  return out;
}

function placeLabels() {
  var placed = [];
  var placedRects = [];
  var nodeRects = [];
  S.locations.forEach(function (l) {
    var p = px(l.id);
    var half = l.id === DEPOT_ID ? DEPOT_HALF : NODE_HALF;
    nodeRects.push([p.x - half - 1, p.y - half - 1, p.x + half + 1, p.y + half + 1]);
  });

  S.plan.stops.forEach(function (sid) {
    var p = px(sid);
    if (p.x === 0 && p.y === 0) return;
    nodeRects.push([p.x + NODE_HALF - 1, p.y - NODE_HALF - 17,
                    p.x + NODE_HALF + 17, p.y - NODE_HALF + 1]);
  });
  var segs = roadSegs();

  var order = [];
  if (S.plan.result && Array.isArray(S.plan.result.stops)) {
    order.push(DEPOT_ID);
    S.plan.result.stops.forEach(function (id) { order.push(id); });
  } else {
    order.push(DEPOT_ID);
  }
  S.locations.forEach(function (l) {
    if (order.indexOf(l.id) === -1) order.push(l.id);
  });

  order.forEach(function (id) {
    var loc = locById(id);
    if (!loc) return;
    var p = px(id);
    var half = id === DEPOT_ID ? DEPOT_HALF : NODE_HALF;
    var cands = candidates(half);

    var best = null;
    var tryTexts = [loc.name.toUpperCase(), shortCode(loc.name)];
    for (var t = 0; t < tryTexts.length && !best; t++) {
      var wtxt = Math.max(20, tryTexts[t].length * CHAR_W);
      var scored = [];
      for (var i = 0; i < cands.length; i++) {
        var r = labelRect(p.x, p.y, cands[i], wtxt);
        var score = i * 0.6;
        for (var j = 0; j < placedRects.length; j++) {
          if (rectHit(r, placedRects[j].rect)) score += 100;
        }
        for (var k2 = 0; k2 < nodeRects.length; k2++) {
          if (rectHit(r, nodeRects[k2])) score += 70;
        }
        for (var m = 0; m < segs.length; m++) {
          var sg = segs[m];
          if (segHitsRect(sg[0], sg[1], sg[2], sg[3], r)) score += 20;
        }
        if (r[0] < 2 || r[2] > CANV.W - 2 || r[1] < 2 || r[3] > CANV.H - 2) score += 30;
        scored.push({ cand: cands[i], rect: r, score: score });
      }
      scored.sort(function (a, b) { return a.score - b.score; });
      if (scored[0].score < 95) {
        best = { rect: scored[0].rect, cand: scored[0].cand,
                 text: tryTexts[t], w: wtxt };
      }
    }
    if (!best) {

      best = { rect: labelRect(p.x, p.y, cands[0], 24), cand: cands[0],
               text: shortCode(loc.name), w: 24, forced: true };
    }
    placed.push({
      id: id, cx: p.x, cy: p.y, cand: best.cand, text: best.text, w: best.w,
      forced: !!best.forced
    });
    placedRects.push({ id: id, rect: best.rect });
  });
  return placed;
}

function drawMap() {
  if (!S.locations.length || !$("#map")) return;
  computeFit();
  var roads = $("#m-roads"), nodes = $("#m-nodes"), labels = $("#m-labels"),
      badges = $("#m-badges"), route = $("#m-route"), weights = $("#m-roadw");
  [roads, nodes, badges, route, weights].forEach(function (g) {
    while (g.firstChild) g.removeChild(g.firstChild);
  });

  S.roads.forEach(function (r) {
    var a = px(r.u), b = px(r.v);
    var line = svg("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y,
      "data-edge": (window.DRO_edgeKey
        ? window.DRO_edgeKey(r.u, r.v)
        : Math.min(r.u, r.v) + "-" + Math.max(r.u, r.v)) });
    var tv = svg("title", null);
    tv.textContent = locById(r.u).name + " <-> " + locById(r.v).name + " : " + r.w + " km";
    line.appendChild(tv);
    roads.appendChild(line);
  });

  if (S.showDist) {
    S.roads.forEach(function (r) {
      var a = px(r.u), b = px(r.v);
      var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      var dx = b.x - a.x, dy = b.y - a.y;
      var len = Math.max(0.001, Math.hypot(dx, dy));
      var nx = -dy / len * 9, ny = dx / len * 9;
      var t = svg("text", { x: mx + nx, y: my + ny, class: "road-w", "text-anchor": "middle" });
      t.textContent = String(r.w);
      weights.appendChild(t);
    });
  }

  var waypoints = [];
  if (S.plan.result && S.plan.result.geometry) {
    S.plan.result.geometry.forEach(function (hop) {
      var pts = [];
      hop.forEach(function (nid) {
        var p = px(nid);
        pts.push([p.x, p.y]);
      });
      waypoints.push(pts);
      route.appendChild(svg("path", {
        d: "M" + pts.map(function (pt) { return pt[0] + "," + pt[1]; }).join(" L"),
        "data-leg": waypoints.length - 1
      }));
    });

    waypoints.forEach(function (pts, li) {
      for (var i = 0; i < pts.length - 1; i++) {
        var a = pts[i], b = pts[i + 1];
        var dx = b[0] - a[0], dy = b[1] - a[1];
        var len = Math.hypot(dx, dy);
        if (len < 24) continue;
        var n = Math.max(1, Math.floor(len / 60));
        var ux = dx / len, uy = dy / len;
        for (var k = 1; k <= n; k++) {
          var t = k / (n + 1);
          var x = a[0] + dx * t, y = a[1] + dy * t;

          var size = 5;
          var f = [[x + ux * size, y + uy * size],
                   [x - ux * size * 0.6 + uy * size * 0.7, y - uy * size * 0.6 - ux * size * 0.7],
                   [x - ux * size * 0.6 - uy * size * 0.7, y - uy * size * 0.6 + ux * size * 0.7]];
          route.appendChild(svg("polygon", {
            points: f.map(function (pt) { return pt[0] + "," + pt[1]; }).join(" "),
            class: "arrowhead", fill: "#FF5A36", stroke: "#1A1A1A", "stroke-width": 0.8,
            "data-leg": li
          }));
        }
      }
    });
    if (S.legHi >= 0) {
      var hi = route.querySelector('path[data-leg="' + S.legHi + '"]');
      if (hi) hi.classList.add("leg-hi");
    }