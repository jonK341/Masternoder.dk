/*
 * MN2 staking rig - Web Worker.
 * Runs a throttled, bounded SHA-256 proof-of-participation burst once per heartbeat
 * interval and reports a nonce/hash back to the page. This is an ENGAGEMENT SIGNAL
 * only - it does NOT mine or validate MN2. CPU use is intentionally capped.
 */
(function () {
  'use strict';

  var running = false;
  var difficulty = 16;      // leading zero bits target (small = light CPU)
  var intervalSec = 30;
  var timer = null;

  function toHex(buf) {
    var b = new Uint8Array(buf), s = '';
    for (var i = 0; i < b.length; i++) s += b[i].toString(16).padStart(2, '0');
    return s;
  }

  function leadingZeroBits(hex) {
    var bits = 0;
    for (var i = 0; i < hex.length; i++) {
      var nibble = parseInt(hex[i], 16);
      if (nibble === 0) { bits += 4; continue; }
      if (nibble < 2) bits += 3; else if (nibble < 4) bits += 2; else if (nibble < 8) bits += 1;
      break;
    }
    return bits;
  }

  async function sha256Hex(str) {
    var data = new TextEncoder().encode(str);
    var digest = await self.crypto.subtle.digest('SHA-256', data);
    return toHex(digest);
  }

  // Bounded search: at most maxIters hashes so we never peg the CPU.
  async function findProof() {
    var prefix = Date.now().toString(36) + ':' + Math.random().toString(36).slice(2);
    var maxIters = 20000;
    for (var n = 0; n < maxIters; n++) {
      var hash = await sha256Hex(prefix + ':' + n);
      if (leadingZeroBits(hash) >= difficulty) {
        return { nonce: prefix + ':' + n, proof: hash, ts: Date.now() };
      }
    }
    // Best-effort: return the last attempt even if target not met (still a heartbeat)
    return { nonce: prefix + ':0', proof: await sha256Hex(prefix + ':0'), ts: Date.now() };
  }

  async function tick() {
    if (!running) return;
    try {
      var result = await findProof();
      self.postMessage({ type: 'proof', payload: result });
    } catch (e) {
      self.postMessage({ type: 'error', error: String(e) });
    }
  }

  function start() {
    if (running) return;
    running = true;
    tick();
    timer = setInterval(tick, intervalSec * 1000);
    self.postMessage({ type: 'status', running: true });
  }

  function stop() {
    running = false;
    if (timer) { clearInterval(timer); timer = null; }
    self.postMessage({ type: 'status', running: false });
  }

  self.onmessage = function (e) {
    var msg = e.data || {};
    if (msg.cmd === 'config') {
      if (msg.difficulty) difficulty = msg.difficulty;
      if (msg.intervalSec) intervalSec = msg.intervalSec;
    } else if (msg.cmd === 'start') {
      if (msg.difficulty) difficulty = msg.difficulty;
      if (msg.intervalSec) intervalSec = msg.intervalSec;
      start();
    } else if (msg.cmd === 'stop') {
      stop();
    }
  };
})();
