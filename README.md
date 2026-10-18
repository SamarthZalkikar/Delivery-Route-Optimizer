# Delivery-Route-Optimizer

A small Flask app that runs a delivery service on a made-up city: queue orders,
assign drivers, plan routes, and watch the algorithms work on a real map.
Built for our DSA course — every data structure is hand-written, nothing comes
from a library beyond Flask itself.

The interesting bit: routes are planned with classic search (exact + heuristic),
and there's also a slime-mold solver (Physarum, Tero et al. 2010) that "grows"
its answer tube by tube. Dijkstra stays as the referee.

![Dispatch with a solved route and the pending-order queue](docs/img/dispatch-route.png)

## Running it

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
```

Tests:

```bash
python -m unittest discover tests     # 92 tests
python verify-map.py                  # 72 checks against a running server
```

Requires Python 3.10+. Map tiles come from OpenStreetMap/CARTO (no API keys);
without internet the app falls back to a hand-drawn SVG map.
