

(function () {
  "use strict";

  var STORE_KEY = "dro-map-mode";
  var CITY_CENTER = [21.1458, 79.0882];

  function safeGet(key, fallback) {
    try { return window.localStorage.getItem(key) || fallback; }
    catch (e) { return fallback; }
  }
  function safeSet(key, val) {
    try { window.localStorage.setItem(key, val); }
    catch (e) {   }
  }

  var MV = {
    mode: safeGet(STORE_KEY, "map") === "schematic" ? "schematic" : "map",
    leaf: null,
    edgeStyles: {},
    srcSink: { src: null, sink: null },
    slimePath: { hops: null, on: false },
    follow: false,
    appHooks: { onNode: function () {}, popupFor: function () { return ""; },
                routeStops: function () { return []; } }
  };

  MV.afterSchematicRedraw = function () {
    if (MV.mode !== "schematic") return;

    var roads = document.querySelectorAll("#m-roads line");
    for (var i = 0; i < roads.length; i++) {
      var key = roads[i].getAttribute("data-edge");
      var s = key && MV.edgeStyles[key];
      if (s) {
        roads[i].style.stroke = s.color;
        roads[i].style.strokeWidth = s.width;
      } else {
        roads[i].style.stroke = "";
        roads[i].style.strokeWidth = "";
      }
    }

    if (window.svg && window.px && window.locById) {
      MV.renderSvgBadges(document.getElementById("m-badges-extra"));
    }

    MV.renderSvgSlime();

    MV.highlightLeg(S.legHi);
  };

  MV.renderSvgBadges = function (g) {
    if (!g) return;
    while (g.firstChild) g.removeChild(g.firstChild);
    [["src", "S", "slime-badge-src"], ["sink", "T", "slime-badge-dst"]]
      .forEach(function (pair) {
        var id = MV.srcSink[pair[0]];
        if (id === null || id === undefined) return;
        var p = window.px(id);
        var t = window.svg("text", {
          x: p.x, y: p.y - 13, "text-anchor": "middle",
          "class": "slabel " + pair[3]
        });
        t.textContent = pair[1];
        g.appendChild(t);
      });
  };

  MV.renderSvgSlime = function () {
    var g = document.getElementById("m-slime");
    if (!g) return;
    while (g.firstChild) g.removeChild(g.firstChild);
    if (!MV.slimePath.on || !MV.slimePath.hops ||
        MV.slimePath.hops.length < 2 || !window.px) return;
    var pts = MV.slimePath.hops.map(function (id) { return window.px(id); });
    var d = "M" + pts.map(function (p) { return p.x + "," + p.y; }).join(" L");
    g.appendChild(window.svg("path", { d: d, "class": "slime-path" }));
  };

  MV.setEdgeStyles = function (styles) {
    MV.edgeStyles = styles || {};
    if (MV.mode === "map" && MV.leaf) MV.leaf.setEdgeStyles(MV.edgeStyles);
    else MV.afterSchematicRedraw();
  };

  MV.clearEdgeStyles = function () {
    MV.edgeStyles = {};
    if (MV.mode === "map" && MV.leaf) MV.leaf.clearEdgeStyles();
    else MV.afterSchematicRedraw();
  };

  MV.setSourceSink = function (src, sink) {
    MV.srcSink = { src: src, sink: sink };
    if (MV.mode === "map" && MV.leaf) MV.leaf.setSourceSink(src, sink);
    else MV.afterSchematicRedraw();
  };

  MV.setSlimePath = function (hops, on) {
    MV.slimePath = { hops: hops, on: on };
    if (MV.mode === "map" && MV.leaf) MV.leaf.setSlimePath(hops, on);
    else MV.renderSvgSlime();
  };

  MV.setBase = function (which) {
    if (MV.mode === "map" && MV.leaf && MV.leaf.setBase) {
      MV.leaf.setBase(which);
      safeSet("dro-map-base", which);
      syncBaseButtons(which);
    }
  };

  function syncBaseButtons(which) {
    var b = document.getElementById("btn-tiles-osm");
    var c = document.getElementById("btn-tiles-carto");
    if (b) b.classList.toggle("active", which === "osm");
    if (c) c.classList.toggle("active", which === "carto");
  }

  MV.highlightLeg = function (idx) {
    if (MV.mode === "map" && MV.leaf) MV.leaf.highlightLeg(idx);
    else {
      $$("#m-route path[data-leg]").forEach(function (p) {
        p.classList.toggle("leg-hi", parseInt(p.getAttribute("data-leg"), 10) === idx);
      });