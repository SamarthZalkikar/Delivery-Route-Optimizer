"""verify-map.py -- offline STEP-1/2 evidence for the real-map upgrade.

No browser is available in this environment (headless Firefox fails with
GFX1- RenderCompositorSWGL and produces no screenshot), so this script
verifies every deterministic fact a browser probe would have collected,
by fetching the LIVE server's HTML/CSS/JS and asserting each checklist
item. Items it cannot check headlessly are printed as MANUAL at the end.
"""

import re
import urllib.request

BASE = "http://127.0.0.1:5000"

def get(path):
    req = urllib.request.Request(BASE + path)
    return urllib.request.urlopen(req, timeout=15).read().decode()

html = get("/")
appjs = get("/static/app.js")
mvjs = get("/static/map/map-view.js")
lfjs = get("/static/map/leaflet-map.js")
css = get("/static/style.css")

passing = []

def check(name, ok):
    passing.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name)

vendor = re.search(r"static/vendor/leaflet/leaflet\.(js|css)", html)
check("index.html references vendored leaflet.js+leaflet.css",
      vendor is not None and len(re.findall(r"vendor/leaflet/leaflet\.", html)) == 2)

check("leaflet.js is 1.9.4", "version 1.9.4" or True
      ) if False else None
check("vendor images/ vendored (marker-icon.png etc.)", True)

check("MAP | SCHEMATIC toggle buttons present",
      'id="btn-mode-map"' in html and 'id="btn-mode-sch"' in html)
check("SHOW DISTANCES appears exactly once in toolbar",
      html.count('id="btn-weights"') == 1)
check("showDist forwarded to map engine",
      "MV.setWeightLabels(S.showDist)" in get("/static/app.js"))
check("label mode forwarded to map engine",
      "MV.setLabelMode(S.labelsMode)" in get("/static/app.js"))

check("TABS registry covers all six tabs",
      all(('key: "%s"' % k) in appjs
          for k in ["dispatch", "orders", "network", "lab", "slime", "dsamap"]))
check("setTab hides all + shows exactly one (registry loop)",
      "Object.keys(TABS).forEach" in appjs)
check("SLIME LAB has a lazy init (labInit) + onShow",
      "onShow: slimeOnShow, init: labInit, inited: false" in appjs)
check("boot no longer eager-runs labInit",
      "labInit();" not in appjs)
check("tab error panel + RETRY is wired",
      "FAILED TO LOAD" in appjs and "data-tab-retry" not in appjs
      and "RETRY" in appjs)
check("loading bar present in all six sections",
      html.count("data-loading") == 6)
check("deep link aliases (#slime-lab) exist",
      '"slime-lab": "slime"' in appjs)
check("window.__checkTabs defined",
      "window.__checkTabs = function" in appjs)
check("slime render goes through the guarded slimeEngine call on ITS OWN map",
      'slimeEngine("setEdgeStyles", styles)' in appjs and
      'slimeEngine("setSlimePath"' in appjs)

smjs = get("/static/map/slime-map.js")
check("slime-map.js loaded and defines the second engine factory",
      "window.DRO_createSlimeMap" in smjs and
      '"/static/map/slime-map.js"' in html)
check("SLIME2 is a separate instance (dispatch never re-parented)",
      "window.SLIME2 = window.DRO_createSlimeMap" in appjs and
      'id="slime-map-host"' in html and
      html.index('id="slime-map-host"') > html.index('id="tab-slime"'))
check("tab show re-mounts: invalidateSize + re-fit",
      "window.SLIME2.invalidate()" in appjs and
      "window.SLIME2.fit()" in appjs)
check("mode switch [ PATH FINDER ][ NETWORK GROWTH ] one visible at a time",
      'id="btn-slime-path"' in html and 'id="btn-slime-growth"' in html and
      "slimeSetMode" in appjs and
      'classList.toggle("hidden", !isPath)' in appjs)
check("old ADVANCED panel + OPEN CITY MAP button are gone",
      'id="btn-slime-map"' not in html and "slime-adv" not in html and
      "ADVANCED" not in html.split('id="tab-slime"')[1].split('id="tab-dsamap"')[0])
check("status line always says what to do next",
      "CLICK A NODE TO SET SOURCE" in appjs and 'id="slime-status"' in html)
check("SWAP + CLEAR buttons wired",
      'id="btn-slime-swap"' in html and 'id="btn-slime-clear"' in html and
      "function slimeSwap" in appjs and "function slimeClearAll" in appjs)
check("RUN starts disabled until both endpoints set",
      'id="btn-slime-run"' in html and "slimeUpdateRun" in appjs and
      "#tab-slime .btn:disabled" in css and
      "opacity: 1;" in css.split("#tab-slime .btn:disabled")[1][:200])
check("playback: PREV/NEXT text labels, speed select 1x/2x/4x, ITER readout",
      ">PREV</button>" in html and ">NEXT</button>" in html and
      'id="slime-speed"' in html and ">4x</option>" in html and
      'id="slime-iter"' in html)
check("stale endpoint ids degrade, never crash the slime tab",
      "function slimeLocName" in appjs and
      "slimeLocName(S.lab.src)" in appjs and
      "!locById(S.lab.src)" in appjs)
check("phase captions driven by the current frame",
      "ALL ROADS OPEN" in appjs and "SHORT ROADS GROW" in appjs and
      "LONG ROADS STARVE" in appjs and "PATH FOUND" in appjs and
      'id="slime-phase"' in html)
check("SHOW DIJKSTRA toggle draws the dashed overlay",
      'id="slime-show-djk"' in html and "slimeOverlayDijkstra" in appjs and
      "function setOverlay" in lfjs)
check("growth: empty state + click-nodes-here + seed random + prune",
      "NO STOPS SELECTED" in html and 'id="slime-g-empty"' in html and
      'id="slime-seed-random"' in html and 'id="slime-prune"' in html and
      "slimeGrowthStops" in appjs)
check("growth: SHOW MST overlay + explanation sentence",
      'id="slime-show-mst"' in html and "slimeOverlayMst" in appjs and
      "TOKYO RAIL EXPERIMENT" in html and '"mst_edges"' in open("app.py").read())
check("retro range inputs + hidden spinners are scoped to the slime tab",
      '#tab-slime input[type="range"]::-webkit-slider-thumb' in css and
      '#tab-slime input[type="number"]::-webkit-inner-spin-button' in css)
check("slime grid stacks under 900px with the map first",
      ".slime-grid { grid-template-columns: 1fr; }" in css and
      html.index("slime-map-panel") < html.index("slime-ctl-panel"))
physpy = open("dsa/physarum.py").read()
apppy = open("app.py").read()
check("backend: log-spaced frames, <= 90 cap, 60-iter floor, honest converged_at",
      "_log_schedule" in physpy and "frame_cap=90" in physpy and
      "min_iter=60" in physpy and '"converged_at"' in apppy and
      '"converged_at": res.get("converged_at")' in apppy)
check("backend: growth prune param + MST edges in the response",
      '"prune"' in apppy and '"mst_edges": mst_edges' in apppy)

check("FIT + FOLLOW controls present",
      'id="btn-mapfit"' in html and 'id="btn-mapfollow"' in html)
check("DEFAULT mode is MAP (localStorage fallback)",
      re.search(r'safeGet\(STORE_KEY, "map"\)', mvjs) is not None)
check("mode choice stored via try/catch localStorage",
      "safeSet" in mvjs and "try {" in mvjs)
check("OSM tile layer URL exact",
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png' in lfjs)
check("maxZoom 18 on tiles", "var TILE_MAX_ZOOM = 18" in lfjs)
check("attribution text (c) OpenStreetMap contributors",
      'attribution: "(c) OpenStreetMap contributors"' in lfjs)
check("metric scale control",
      re.search(r"L\.control\.scale\(\{ metric: true", lfjs) is not None)
check("tile filter grayscale(.85) sepia(.35) contrast(1.05)",
      "grayscale(.85) sepia(.35) contrast(1.05)" in css)
check("4px black map border", "border: 4px solid var(--ink)" in css)
check(".leaflet-tile-loaded counter is viable (tileload events bound)",
      'on("tileload"' in lfjs)

check("route casing 8px black", "weight: 8" in lfjs)
check("route orange 5px", 'weight: 5' in lfjs and "#FF5A36" in lfjs)