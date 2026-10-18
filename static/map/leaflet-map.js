

(function () {
  "use strict";

  function edgeKey(u, v) {
    return Math.min(u, v) + "-" + Math.max(u, v);
  }
  window.DRO_edgeKey = edgeKey;

  var TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  var TILE_MAX_ZOOM = 18;
  var ROAD_COLOR = "#1A1A1A";

  function createLeafletMap(host, hooks) {
    var map = L.map(host, {
      zoomControl: false,
      attributionControl: true,
      preferCanvas: false
    });
    map.setView(hooks.center, 14);

    var osmLayer = L.tileLayer(TILE, {
      maxZoom: TILE_MAX_ZOOM,
      attribution: "(c) OpenStreetMap contributors"
    });
    var cartoLayer = L.tileLayer(
      "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        maxZoom: TILE_MAX_ZOOM, subdomains: "abcd",
        attribution: "(c) OpenStreetMap contributors (c) CARTO"
      });

    var active = "osm";
    osmLayer.addTo(map);
    map.addControl(L.control.scale({ metric: true, imperial: false }));

    var tileErrStreak = 0;
    var fallbackFired = false;
    function onTileError() {
      tileErrStreak += 1;
      if (tileErrStreak >= 5 && !fallbackFired) {
        fallbackFired = true;
        if (hooks.onTilesUnavailable) hooks.onTilesUnavailable();
      }
    }
    osmLayer.on("tileerror", onTileError);
    cartoLayer.on("tileerror", onTileError);
    osmLayer.on("tileload", function () { tileErrStreak = 0; });
    cartoLayer.on("tileload", function () { tileErrStreak = 0; });

    function fallbackActive() { return fallbackFired; }
    function retry() {
      tileErrStreak = 0;
      fallbackFired = false;
    }

    function setBase(which) {
      if (which === active) return;
      map.removeLayer(active === "carto" ? cartoLayer : osmLayer);
      active = which;
      (which === "carto" ? cartoLayer : osmLayer).addTo(map);
    }

    if (hooks.zoomControl !== false) {
      L.control.zoom({ position: "bottomright" }).addTo(map);
    }

    var roadLayer = L.layerGroup().addTo(map);
    var slimeLayer = L.layerGroup().addTo(map);
    var overlayLayer = L.layerGroup().addTo(map);
    var routeLayer = L.layerGroup().addTo(map);
    var arrowLayer = L.layerGroup().addTo(map);
    var badgeLayer = L.layerGroup().addTo(map);
    var truckLayer = L.layerGroup().addTo(map);
    var nodeLayer = L.layerGroup().addTo(map);

    var nodeMarkers = {};
    var lineByEdge = {};
    var legLines = [];
    var byId = {};
    var routeLegsLatLng = [];
    var selLookup = {};
    var depotId = hooks.depotId || 0;
    var isDepotFn = hooks.isDepot || function (id) { return id === depotId; };
    var permLabels = {};
    var labelMode = "all";
    var weightLabelsOn = false;
    var hoveredNodeId = null;

    function iconBox(cls, size, html) {
      return L.divIcon({
        className: "lk-wrap",
        html: '<div class="' + cls + '">' + (html || "") + '</div>',
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2]
      });
    }

    function syncOverlays() {

      arrowLayer.clearLayers();
      routeLegsLatLng.forEach(function (chain) {
        for (var i = 0; i < chain.length - 1; i++) {
          var a = map.latLngToLayerPoint(chain[i]);
          var b = map.latLngToLayerPoint(chain[i + 1]);
          var dx = b.x - a.x, dy = b.y - a.y;
          var len = Math.hypot(dx, dy);
          if (len < 40) continue;
          var n = Math.floor(len / 70);
          var ux = dx / len, uy = dy / len;
          for (var k = 1; k <= n; k++) {
            var p = L.point(a.x + dx * (k / (n + 1)),
                            a.y + dy * (k / (n + 1)));
            var ang = Math.atan2(uy, ux) * 180 / Math.PI + 90;
            L.marker(map.layerPointToLatLng(p), {
              icon: L.divIcon({
                className: "lk-wrap",
                html: '<div class="lk-arrow" style="transform:rotate(' +
                  ang.toFixed(1) + 'deg)"></div>',
                iconSize: [10, 8], iconAnchor: [5, 6]
              }),
              interactive: false, keyboard: false
            }).addTo(arrowLayer);
          }
        }
      });

      badgeLayer.clearLayers();
      var stops = hooks.routeStops ? hooks.routeStops() : [];
      stops.forEach(function (id, i) {
        var node = byId[id];
        if (!node) return;
        var pt = map.latLngToLayerPoint([node.lat, node.lng]);
        var bpt = map.layerPointToLatLng(pt.add([11, -11]));
        L.marker(bpt, {
          icon: L.divIcon({
            className: "lk-wrap",
            html: '<div class="lk-nb">' + (i + 1) + '</div>',
            iconSize: [15, 15], iconAnchor: [7.5, 7.5]
          }),
          interactive: false, keyboard: false
        }).addTo(badgeLayer);
      });
    }
    map.on("zoomend", syncOverlays);
    map.on("moveend", function () { if (hooks.onFollow) hooks.onFollow(truckLL); });

    function labelPriority(node) {
      if (isDepotFn(node.id)) return 0;
      if (selLookup[node.id]) return 1;
      if (hoveredNodeId === node.id) return 2;
      return 3;
    }

    function refreshLabels() {
      var nodes = Object.keys(byId).map(function (k) { return byId[k]; });
      if (labelMode === "off") {
        Object.keys(permLabels).forEach(function (id) {
          if (nodeMarkers[id]) nodeMarkers[id].unbindTooltip();
          delete permLabels[id];
        });
        return;
      }
      var zoom = map.getZoom();

      var restOK = labelMode === "all" && zoom >= 15;
      var candidates = nodes.filter(function (n) {
        return isDepotFn(n.id) || selLookup[n.id] ||
               hoveredNodeId === n.id || restOK;
      });

      var pts = candidates.map(function (n) {
        return { n: n, p: map.latLngToContainerPoint([n.lat, n.lng]) };
      });
      var placed = [];

      for (var i = 1; i < pts.length; i++) {
        var cur = pts[i], j = i - 1;
        while (j >= 0 && labelPriority(pts[j].n) > labelPriority(cur.n)) {
          pts[j + 1] = pts[j]; j--;
        }
        pts[j + 1] = cur;
      }
      var dirs = ["right", "left", "top", "bottom"];
      pts.forEach(function (c) {
        var name = c.n.name.toUpperCase();
        var w = name.length * 7.2 + 10, h = 16;
        var best = null;

        var dirsTry = dirs.slice();
        dirsTry.reverse();
        dirsTry.forEach(function (dir) {
          if (best) return;
          var x = c.p.x, y = c.p.y;
          if (dir === "right") x += 12;
          else if (dir === "left") x -= (w + 12);
          else if (dir === "top") { x -= w / 2; y -= 26; }
          else { x -= w / 2; y += 16; }
          var rect = { l: x, t: y, r: x + w, b: y + h, n: c.n };

          for (var k = 0; k < placed.length; k++) {
            var o = placed[k];
            if (rect.l < o.r && rect.r > o.l && rect.t < o.b && rect.b > o.t) {
              return;
            }
          }
          best = { dir: dir, rect: rect };
        });
        if (!best) return;
        var m = nodeMarkers[c.n.id];
        if (m && !permLabels[c.n.id]) {
          m.bindTooltip(c.n.name, {
            permanent: true, direction: best.dir, className: "lk-perm",
            offset: L.point(0, 0)
          });
          permLabels[c.n.id] = true;
        } else if (m) {

        }
        placed.push(best.rect);
      });

      Object.keys(permLabels).forEach(function (id) {
        var still = placed.some(function (r) { return String(r.n.id) === id; });
        if (!still && nodeMarkers[id]) {
          nodeMarkers[id].unbindTooltip();
          delete permLabels[id];
        }
      });
    }
    map.on("zoomend", refreshLabels);

    function setNodes(locs) {
      nodeLayer.clearLayers();
      nodeMarkers = {};
      permLabels = {};
      byId = {};
      locs.forEach(function (loc) {
        byId[loc.id] = loc;
      });
      locs.forEach(function (loc) {
        var isDepot = isDepotFn(loc.id);
        var icon = isDepot
          ? iconBox("lk-depot", 28, "H")
          : iconBox("lk-loc" + (selLookup[loc.id] ? " lk-sel" : ""), 18);
        var m = L.marker([loc.lat, loc.lng], {
          icon: icon, keyboard: true, title: loc.name,
          zIndexOffset: isDepot ? 600 : 400
        });
        m.on("click", function () { hooks.onNode(loc.id); });
        m.on("mouseover", function () {
          hoveredNodeId = loc.id;
          refreshLabels();
          if (hooks.onNodeHover) hooks.onNodeHover(loc.id);
        });
        m.on("mouseout", function () {
          if (hoveredNodeId === loc.id) hoveredNodeId = null;
          refreshLabels();
          if (hooks.onNodeLeave) hooks.onNodeLeave(loc.id);
        });
        m.on("popupopen", function (e) {
          e.popup.setContent(hooks.popupFor(loc.id));
          wirePopupActs(e.popup._contentNode, loc.id);
        });
        m.bindPopup("", { autoPan: true, closeButton: true });
        m.addTo(nodeLayer);
        nodeMarkers[loc.id] = m;
      });
      refreshLabels();
    }

    function wirePopupActs(root, id) {
      root.querySelectorAll("[data-act]").forEach(function (b) {
        b.addEventListener("click", function () {
          map.closePopup();
          if (b.getAttribute("data-act") === "stop") hooks.onNode(id);
          else if (b.getAttribute("data-act") === "depot" && hooks.onSetDepot) {
            hooks.onSetDepot(id);
          }
        });
      });
    }

    function setRoads(roads) {
      roadLayer.clearLayers();
      slimeLayer.clearLayers();
      lineByEdge = {};
      roads.forEach(function (r) {
        var a = byId[r.u], b = byId[r.v];
        var line = L.polyline([[a.lat, a.lng], [b.lat, b.lng]], {
          color: ROAD_COLOR, weight: 2, opacity: 1, className: "lk-road"
        });
        line._htext = a.name + " <-> " + b.name + " : " + r.w + " km";
        line._w = r.w;
        line.bindTooltip(line._htext, { sticky: true });
        line.on("click", function () { hooks.onNode(r.u); });
        line.addTo(roadLayer);
        lineByEdge[edgeKey(r.u, r.v)] = line;
      });
      if (weightLabelsOn) applyWeightLabels();
    }

    function applyWeightLabels() {
      Object.keys(lineByEdge).forEach(function (key) {
        var line = lineByEdge[key];
        if (weightLabelsOn) {
          line.bindTooltip(line._w + " km", {
            permanent: true, direction: "right",
            className: "lk-perm lk-roadw", offset: L.point(6, 0)
          });
        } else {
          line.unbindTooltip();
          line.bindTooltip(line._htext, { sticky: true });
        }
      });
    }

    function setWeightLabels(on) {
      weightLabelsOn = !!on;
      applyWeightLabels();
    }

    function setLabelMode(mode) {
      labelMode = (mode === "route" || mode === "off") ? mode : "all";
      refreshLabels();
    }

    function setRoute(hops, selIds) {
      selLookup = {};
      (selIds || []).forEach(function (id) { selLookup[id] = true; });
      routeLayer.clearLayers();
      legLines = [];
      routeLegsLatLng = [];
      if (hops && hops.length) {
        hops.forEach(function (chain, idx) {
          if (chain.length < 2) return;
          var latlngs = chain.map(function (nid) {
            return [byId[nid].lat, byId[nid].lng];
          });
          routeLegsLatLng.push(latlngs);
          L.polyline(latlngs, { color: "#1A1A1A", weight: 8,
                                lineCap: "square" }).addTo(routeLayer);
          var orange = L.polyline(latlngs, { color: "#FF5A36", weight: 5,
                                             lineCap: "round" });
          orange.addTo(routeLayer);
          legLines.push({ idx: idx, poly: orange });
        });
      }
      syncOverlays();
      refreshLabels();
    }

    var truckMarker = null;
    var truckLL = null;
    var followOn = false;
    function playRoute(hops) {
      stopTrack();
      var flat = [];
      (hops || []).forEach(function (chain, ci) {
        chain.forEach(function (nid, k) {
          if (!flat.length || flat[flat.length - 1].nid !== nid) {
            flat.push({ nid: nid, leg: ci });
          }
        });
      });
      var ll = flat.map(function (s) { return byId[s.nid]; })
                   .map(function (l) { return [l.lat, l.lng]; });
      if (!ll.length) return;
      truckMarker = L.marker(ll[0], {
        icon: L.divIcon({
          className: "lk-wrap",
          html: '<div class="lk-truck"><i class="tb"></i><i class="tc"></i></div>',
          iconSize: [18, 12], iconAnchor: [9, 6]
        }),
        interactive: false, keyboard: false, zIndexOffset: 900
      }).addTo(truckLayer);
      truckLL = ll[0];
      if (hooks.reducedMotion) {
        truckMarker.setLatLng(ll[ll.length - 1]);
        setTimeout(function () { hideTruck(); }, 900);
        return;
      }
      var i = 0;
      function step() {
        if (!truckMarker) return;
        if (i >= ll.length) {
          setTimeout(hideTruck, 900);
          return;
        }
        var from = ll[i > 0 ? i - 1 : 0];
        var to = ll[i];

        var s = 0;
        function tick() {
          if (!truckMarker || s > 4) return;
          var t = s / 4;
          var p = [from[0] + (to[0] - from[0]) * t,
                   from[1] + (to[1] - from[1]) * t];
          truckLL = p;
          truckMarker.setLatLng(p);
          if (followOn) map.panTo(p, { animate: false });
          s += 1;
          setTimeout(tick, 190);
        }
        tick();
        i += 1;
        setTimeout(step, 950);
      }
      step();
    }
    function stopTrack() {
      if (truckMarker) { truckLayer.removeLayer(truckMarker); truckMarker = null; }
    }
    function hideTruck() { stopTrack(); }
    function setFollow(on) { followOn = on;   }

    function setEdgeStyles(styles) {
      Object.keys(lineByEdge).forEach(function (key) {
        var s = styles[key];
        if (s) {
          lineByEdge[key].setStyle({ weight: s.width, color: s.color, opacity: 1 });
          lineByEdge[key].bringToFront();
        }
      });
    }

    function clearEdgeStyles() {
      Object.keys(lineByEdge).forEach(function (key) {
        lineByEdge[key].setStyle({ weight: 2, color: ROAD_COLOR, opacity: 1 });
      });