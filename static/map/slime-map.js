

(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var CANV = { W: 720, H: 504, PAD: 44 };

  window.DRO_createSlimeMap = function (host, opts) {
    opts = opts || {};
    var mode = null;
    var leaf = null;
    var svgHost = null;
    var store = {
      locs: [], roads: [],
      styles: {},
      path: null, pathOn: false,
      src: null, snk: null,
      overlay: null,
      tilesBroken: false
    };
    var byId = {};

    function edgeKey(u, v) {
      return window.DRO_edgeKey ? window.DRO_edgeKey(u, v)
        : Math.min(u, v) + "-" + Math.max(u, v);
    }
    function refreshById() {
      byId = {};
      store.locs.forEach(function (l) { byId[l.id] = l; });
    }

    function makeLeaf() {
      host.innerHTML = "";
      var eng = window.DRO_createLeafletMap(host, {
        center: opts.center,
        depotId: 0,
        isDepot: function (id) { return id === Number(window.DEPOT_ID || 0); },
        onTilesUnavailable: function () {
          store.tilesBroken = true;
          if (opts.onFallback) opts.onFallback();
        },
        onNode: opts.onNode,
        onNodeHover: opts.onNodeHover || null,
        onNodeLeave: opts.onNodeLeave || null,
        popupFor: opts.popupFor || function (id) {
          var loc = byId[id];
          return loc ? "<div class='lk-pop'><strong>" + loc.name + "</strong></div>" : "";
        },
        routeStops: function () { return []; }
      });
      return eng;
    }

    function makeSvg() {
      host.innerHTML = "";
      svgHost = document.createElementNS(NS, "svg");
      svgHost.setAttribute("viewBox", "0 0 " + CANV.W + " " + CANV.H);
      svgHost.setAttribute("class", "slime-svg");
      var under = document.createElementNS(NS, "rect");
      under.setAttribute("width", CANV.W);
      under.setAttribute("height", CANV.H);
      under.setAttribute("class", "slime-svg-bg");
      var gRoad = document.createElementNS(NS, "g");
      var gOverlay = document.createElementNS(NS, "g");
      var gPath = document.createElementNS(NS, "g");
      var gNodes = document.createElementNS(NS, "g");
      var gBadges = document.createElementNS(NS, "g");
      [under, gRoad, gOverlay, gPath, gNodes, gBadges].forEach(function (n) {
        svgHost.appendChild(n);
      });
      host.appendChild(svgHost);

      var fit = null;
      function computeFit() {
        var xs = [], ys = [];
        store.locs.forEach(function (l) { xs.push(l.x); ys.push(l.y); });
        if (!xs.length) { fit = null; return; }
        var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs);
        var miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
        var w = Math.max(1, maxx - minx), h = Math.max(1, maxy - miny);
        var s = Math.min((CANV.W - 2 * CANV.PAD) / w,
                         (CANV.H - 2 * CANV.PAD) / h);
        fit = { s: s, ox: (CANV.W - w * s) / 2 - minx * s,
                oy: (CANV.H - h * s) / 2 - miny * s };
      }
      function pt(id) {
        var l = byId[id];
        if (!l || !fit) return { x: -20, y: -20 };
        return { x: l.x * fit.s + fit.ox, y: l.y * fit.s + fit.oy };
      }
      function tag(name, attrs) {
        var n = document.createElementNS(NS, name);
        Object.keys(attrs || {}).forEach(function (k) {
          n.setAttribute(k, attrs[k]);
        });
        return n;
      }

      var roadLines = {};
      var nodeRects = {};

      function rebuildRoads() {
        while (gRoad.firstChild) gRoad.removeChild(gRoad.firstChild);
        roadLines = {};
        store.roads.forEach(function (r) {
          var a = pt(r.u), b = pt(r.v);
          var line = tag("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y,
            class: "slime-road" });
          var t = tag("title", null);
          t.textContent = byId[r.u].name + " <-> " + byId[r.v].name +
            " : " + r.w + " KM";
          line.appendChild(t);
          gRoad.appendChild(line);
          roadLines[edgeKey(r.u, r.v)] = line;
        });
        repaintStyles();
      }
      function repaintStyles() {
        Object.keys(roadLines).forEach(function (key) {
          var line = roadLines[key];
          var st = store.styles[key];
          line.setAttribute("stroke", st && st.color ? st.color : "#7A746C");
          line.setAttribute("stroke-width", st && st.width ? st.width : 1.5);
        });
      }
      function rebuildNodes() {
        while (gNodes.firstChild) gNodes.removeChild(gNodes.firstChild);
        nodeRects = {};
        store.locs.forEach(function (l) {
          var depot = l.id === Number(window.DEPOT_ID || 0);
          var r = tag("rect", {
            x: pt(l.id).x - 7, y: pt(l.id).y - 7,
            width: 14, height: 14,
            "class": "slime-node" + (depot ? " slime-node-depot" : ""),
            tabindex: "0", role: "button",
            "aria-label": l.name
          });
          r.addEventListener("click", function () {
            if (opts.onNode) opts.onNode(l.id);
          });
          r.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
              if (e.preventDefault) e.preventDefault();
              if (opts.onNode) opts.onNode(l.id);
            }
          });
          var t = tag("title", null);
          t.textContent = l.name;
          r.appendChild(t);
          gNodes.appendChild(r);
          nodeRects[l.id] = r;
        });
        paintEndpoints();
      }
      function paintEndpoints() {
        Object.keys(nodeRects).forEach(function (id) {
          var r = nodeRects[id];
          var cls = "slime-node";
          if (id === Number(window.DEPOT_ID || 0)) cls += " slime-node-depot";
          if (id === store.src) cls += " slime-node-src";
          if (id === store.snk) cls += " slime-node-snk";

          r.setAttribute("class", cls);
        });
      }
      function paintPath() {
        while (gPath.firstChild) gPath.removeChild(gPath.firstChild);
        if (!store.pathOn || !store.path || store.path.length < 2) return;
        var pts = store.path.map(function (id) { return pt(id); });
        gPath.appendChild(tag("polyline", {
          points: pts.map(function (p) { return p.x + "," + p.y; }).join(" "),
          "class": "slime-svg-path"
        }));
      }
      function paintOverlay() {
        while (gOverlay.firstChild) gOverlay.removeChild(gOverlay.firstChild);
        if (!store.overlay || !store.overlay.length) return;
        store.overlay.forEach(function (pr) {
          var a = pt(pr[0]), b = pt(pr[1]);
          if (a.x < 0 || b.x < 0) return;
          gOverlay.appendChild(tag("line", {
            x1: a.x, y1: a.y, x2: b.x, y2: b.y,
            "class": "slime-svg-overlay"
          }));
        });
      }

      engineApi.svg = {
        setData: function () { computeFit(); rebuildRoads(); rebuildNodes(); paintPath(); paintOverlay(); },
        setEdgeStyles: function (styles) { store.styles = styles || {}; repaintStyles(); },
        setSlimePath: function (hops, on) { store.path = hops; store.pathOn = !!on; paintPath(); },
        setSourceSink: function (src, snk) {
          store.src = src; store.snk = snk; paintEndpoints();
          while (gBadges.firstChild) gBadges.removeChild(gBadges.firstChild);
          if (src !== null && byId[src]) {
            gBadges.appendChild(tag("text", {
              x: pt(src).x + 10, y: pt(src).y - 10, "class": "slime-badge"
            })).textContent = "SRC";
          }
          if (snk !== null && byId[snk]) {
            gBadges.appendChild(tag("text", {
              x: pt(snk).x + 10, y: pt(snk).y - 10, "class": "slime-badge"
            })).textContent = "SNK";
          }
        },
        setOverlay: function (pairs) { store.overlay = pairs; paintOverlay(); },
        fit: function () { computeFit(); rebuildRoads(); rebuildNodes(); },
        invalidate: function () {   },
        destroy: function () { host.innerHTML = ""; svgHost = null; }
      };
    }

    function applyStore() {
      if (mode === "map" && leaf) {
        leaf.setNodes(store.locs);
        leaf.setRoads(store.roads);
        leaf.setEdgeStyles(store.styles);
        leaf.setSlimePath(store.path, store.pathOn);
        leaf.setSourceSink(store.src, store.snk);
        leaf.setOverlay(store.overlay);
        leaf.fit();
        return;
      }
      if (mode === "schematic" && engineApi.svg) {
        engineApi.svg.setData();
        engineApi.svg.setEdgeStyles(store.styles);
        engineApi.svg.setSourceSink(store.src, store.snk);
        engineApi.svg.setSlimePath(store.path, store.pathOn);
        engineApi.svg.setOverlay(store.overlay);
      }
    }

    var engineApi = { svg: null };

    var api = {
      setMode: function (m) {
        var want = (m === "schematic") ? "schematic" : "map";
        if (mode === want) return;
        if (leaf) { leaf.destroy(); leaf = null; }
        if (svgHost) { svgHost.remove(); svgHost = null; }
        engineApi.svg = null;
        mode = want;
        if (mode === "map") {
          leaf = makeLeaf();
        } else {
          makeSvg();
        }
        applyStore();
      },
      setData: function (locs, roads) {
        store.locs = locs || [];
        store.roads = roads || [];
        refreshById();
        applyStore();
      },
      setEdgeStyles: function (styles) {
        store.styles = styles || {};
        if (leaf) leaf.setEdgeStyles(store.styles);
        if (engineApi.svg) engineApi.svg.setEdgeStyles(store.styles);
      },
      setSlimePath: function (hops, on) {
        store.path = hops; store.pathOn = !!on;
        if (leaf) leaf.setSlimePath(store.path, store.pathOn);
        if (engineApi.svg) engineApi.svg.setSlimePath(store.path, store.pathOn);
      },
      setSourceSink: function (src, snk) {
        store.src = src; store.snk = snk;
        if (leaf) leaf.setSourceSink(store.src, store.snk);
        if (engineApi.svg) engineApi.svg.setSourceSink(store.src, store.snk);
      },
      setOverlay: function (pairs) {
        store.overlay = pairs || null;
        if (leaf) leaf.setOverlay(store.overlay);
        if (engineApi.svg) engineApi.svg.setOverlay(store.overlay);
      },
      fit: function () {
        if (leaf) leaf.fit();
        if (engineApi.svg) engineApi.svg.fit();
      },
      invalidate: function () {
        if (leaf) leaf.invalidate();
      },
      destroy: function () {
        if (leaf) { leaf.destroy(); leaf = null; }
        if (svgHost) { svgHost.remove(); svgHost = null; }
        engineApi.svg = null;
        mode = null;
        host.innerHTML = "";
      },
      tilesBroken: function () { return store.tilesBroken; },
      mode: function () { return mode; }
    };
    return api;
  };
})();
