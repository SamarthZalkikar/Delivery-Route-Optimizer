

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
    }
  };

  MV.playRoute = function (hops, reduced) {
    if (MV.mode === "map" && MV.leaf) MV.leaf.playRoute(hops, reduced);
    else if (window.playRouteSchematic) window.playRouteSchematic();
  };

  MV.hideTruck = function () {
    if (MV.mode === "map" && MV.leaf) MV.leaf.hideTruck();
  };

  MV.setFollow = function (on) {
    MV.follow = on;
    if (MV.mode === "map" && MV.leaf) MV.leaf.setFollow(on);
  };

  MV.fit = function () {
    if (MV.mode === "map" && MV.leaf) MV.leaf.fit();
    else if (window.resetZoom) window.resetZoom();
  };

  MV.syncLeaf = function () {
    if (!MV.leaf || !window.S) return;
    MV.leaf.setNodes(S.locations);
    MV.leaf.setRoads(S.roads);
    MV.leaf.setLabelMode(MV.labelMode || "all");
    if (MV.weightsOn) MV.leaf.setWeightLabels(true);
    MV.leaf.setRoute(S.plan.result ? S.plan.result.geometry : null,
                     S.plan.result ? S.plan.result.stops : S.plan.stops);
    MV.leaf.setSourceSink(MV.srcSink.src, MV.srcSink.sink);
    MV.leaf.setSlimePath(MV.slimePath.hops, MV.slimePath.on);
    if (Object.keys(MV.edgeStyles).length) MV.leaf.setEdgeStyles(MV.edgeStyles);
  };

  MV.setWeightLabels = function (on) {
    MV.weightsOn = !!on;
    if (MV.mode === "map" && MV.leaf) MV.leaf.setWeightLabels(MV.weightsOn);
  };
  MV.setLabelMode = function (mode) {
    MV.labelMode = mode;
    if (MV.mode === "map" && MV.leaf) MV.leaf.setLabelMode(mode);
  };

  MV.removeTileNote = function () {
    var n = document.getElementById("tiles-note");
    if (n) n.remove();
  };

  MV.showTileNotice = function () {

    MV.setMode("schematic");
    var host = document.getElementById("panel-map");
    if (!host || document.getElementById("tiles-note")) return;
    var note = document.createElement("div");
    note.id = "tiles-note";
    note.className = "tiles-note";
    var span = document.createElement("span");
    span.textContent = "TILES UNAVAILABLE - USING SCHEMATIC MAP";
    var btn = document.createElement("button");
    btn.id = "btn-retry-map";
    btn.className = "btn btn-sm";
    btn.setAttribute("aria-label", "Retry the real map tiles");
    btn.textContent = "RETRY MAP";
    btn.addEventListener("click", function () {
      note.remove();
      MV.leafResetTileFailures();
      MV.setMode("map");
    });
    note.appendChild(span);
    note.appendChild(btn);
    host.appendChild(note);
  };

  MV.leafResetTileFailures = function () {
    if (MV.leaf && MV.leaf.retryTiles) {
      MV.leaf.retryTiles();
    }
  };

  MV.setMode = function (mode) {
    var svgwrap = document.querySelector(".svgwrap");
    var host = document.getElementById("leaflet-host");
    if (!svgwrap || !host) return;
    MV.mode = mode;
    safeSet(STORE_KEY, mode);
    var bm = document.getElementById("btn-mode-map");
    var bs = document.getElementById("btn-mode-sch");
    if (bm) bm.setAttribute("aria-pressed", String(mode === "map"));
    if (bs) bs.setAttribute("aria-pressed", String(mode === "schematic"));
    var bfollow = document.getElementById("btn-mapfollow");
    if (bfollow) bfollow.classList.toggle("hidden", mode !== "map");
    if (mode === "map") {
      if (MV.leaf) { MV.leaf.destroy(); MV.leaf = null; }
      document.getElementById("map").classList.add("hidden");
      document.getElementById("tooltips").classList.add("hidden");
      host.classList.remove("hidden");
      MV.leaf = window.DRO_createLeafletMap(host, {
        center: CITY_CENTER,
        depotId: 0,
        isDepot: function (id) {
          return id === Number(window.DEPOT_ID || 0);
        },
        reducedMotion: window.matchMedia &&
          window.matchMedia("(prefers-reduced-motion: reduce)").matches,
        onNode: function (id) { MV.appHooks.onNode(id); },
        onSetDepot: function (id) {
          if (MV.appHooks.onSetDepot) MV.appHooks.onSetDepot(id);
        },
        onNodeHover: function (id) {
          if (MV.appHooks.onNodeHover) MV.appHooks.onNodeHover(id);
        },
        onNodeLeave: function (id) {
          if (MV.appHooks.onNodeLeave) MV.appHooks.onNodeLeave(id);
        },
        onEmptyClick: function (latlng) {
          if (MV.appHooks.onEmptyClick) MV.appHooks.onEmptyClick(latlng);
        },
        onAddLocation: function (latlng, name) {
          if (MV.appHooks.onAddLocation) MV.appHooks.onAddLocation(latlng, name);
        },
        routeStops: function () {
          return MV.appHooks.routeStops();
        },
        popupFor: function (id) { return MV.appHooks.popupFor(id); },
        onTilesUnavailable: function () { MV.showTileNotice(); }
      });
      var savedBase = safeGet("dro-map-base", "osm");
      MV.leaf.setBase(savedBase === "carto" ? "carto" : "osm");
      syncBaseButtons(savedBase === "carto" ? "carto" : "osm");
      MV.syncLeaf();
      MV.leaf.invalidate();
      MV.leaf.fit();
    } else {
      if (MV.leaf) { MV.leaf.destroy(); MV.leaf = null; }
      host.classList.add("hidden");
      document.getElementById("map").classList.remove("hidden");
      document.getElementById("tooltips").classList.remove("hidden");
      if (window.drawMap) window.drawMap();
    }
  };

  MV.dataChanged = function () {
    if (MV.mode === "map" && MV.leaf) MV.syncLeaf();
  };

  window.MV = MV;
})();
