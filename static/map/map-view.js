

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