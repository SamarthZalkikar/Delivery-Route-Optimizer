

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