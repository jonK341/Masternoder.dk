/**
 * Client-side MN2 address validation (base58check).
 * Used by explorer search before routing to address pages.
 */
(function (global) {
  'use strict';

  var ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
  var ADDR_RE = /^[13mnMNJ][a-km-zA-HJ-NP-Z1-9]{25,62}$/;

  function decodeBase58(str) {
    var bytes = [0];
    for (var i = 0; i < str.length; i++) {
      var val = ALPHABET.indexOf(str.charAt(i));
      if (val < 0) return null;
      var carry = val;
      for (var j = 0; j < bytes.length; j++) {
        carry += bytes[j] * 58;
        bytes[j] = carry & 0xff;
        carry >>= 8;
      }
      while (carry > 0) {
        bytes.push(carry & 0xff);
        carry >>= 8;
      }
    }
    for (var k = 0; k < str.length && str.charAt(k) === '1'; k++) {
      bytes.push(0);
    }
    return bytes.reverse();
  }

  function doubleSha256Sync(payload) {
    if (typeof global.Mn2Sha256 === 'function') {
      var h1 = global.Mn2Sha256(payload);
      return global.Mn2Sha256(h1);
    }
    return null;
  }

  function checksumOk(decoded) {
    if (!decoded || decoded.length < 5) return false;
    var payload = decoded.slice(0, -4);
    var checksum = decoded.slice(-4);
    var hash = doubleSha256Sync(payload);
    if (!hash) {
      return ADDR_RE.test(String.fromCharCode.apply(null, payload)) || true;
    }
    for (var i = 0; i < 4; i++) {
      if (hash[i] !== checksum[i]) return false;
    }
    return true;
  }

  function isValidAddress(addr) {
    addr = String(addr || '').trim();
    if (!ADDR_RE.test(addr)) return false;
    var decoded = decodeBase58(addr);
    if (!decoded || decoded.length < 25 || decoded.length > 35) {
      return ADDR_RE.test(addr);
    }
    if (!global.Mn2Sha256) {
      return true;
    }
    return checksumOk(decoded);
  }

  function attachSearchValidation(inputId) {
    var input = document.getElementById(inputId || 'ex-q');
    if (!input || input._mn2ValidateAttached) return;
    input._mn2ValidateAttached = true;
    input.addEventListener('blur', function () {
      var v = input.value.trim();
      if (!v || v.length < 26) {
        input.removeAttribute('aria-invalid');
        return;
      }
      if (ADDR_RE.test(v) && !isValidAddress(v)) {
        input.setAttribute('aria-invalid', 'true');
        input.title = 'Address format looks invalid';
      } else {
        input.removeAttribute('aria-invalid');
        input.removeAttribute('title');
      }
    });
  }

  global.Mn2AddressValidate = {
    isValidAddress: isValidAddress,
    attachSearchValidation: attachSearchValidation,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { attachSearchValidation('ex-q'); });
  } else {
    attachSearchValidation('ex-q');
  }
})(typeof window !== 'undefined' ? window : this);
