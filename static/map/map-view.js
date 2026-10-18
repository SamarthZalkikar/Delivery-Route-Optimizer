

(function () {
  "use strict";

  var STORE_KEY = "dro-map-mode";
  var CITY_CENTER = [21.1458, 79.0882];

  function safeGet(key, fallback) {
    try { return window.localStorage.getItem(key) || fallback; }
    catch (e) { return fallback; }
  }