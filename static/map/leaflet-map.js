

(function () {
  "use strict";

  function edgeKey(u, v) {
    return Math.min(u, v) + "-" + Math.max(u, v);
  }