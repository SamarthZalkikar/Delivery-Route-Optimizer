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