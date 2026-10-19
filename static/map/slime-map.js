

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