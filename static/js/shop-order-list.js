/**
 * Shop order lists — purchases + stall listings, checkboxes, PDF download.
 * Uses /api/shop/purchases, /api/shop/stall-orders, /api/shop/order-pdf.
 */
(function (global) {
  'use strict';

  var STATUS_LABELS = {
    pending: 'Pending',
    completed: 'Completed',
    refunded: 'Refunded',
    cancelled: 'Cancelled',
    active: 'Active',
    sold: 'Sold',
    bought: 'Bought',
  };

  var selected = Object.create(null);

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function rowSource(row) {
    if (row && row.source) return String(row.source);
    if (row && row.listing_id) return 'listing';
    if (row && (row.order_id || row.price_type === 'paypal_mn2_hosting')) return 'masternode_hosting';
    return 'purchase';
  }

  function rowId(row) {
    if (!row) return '';
    var src = rowSource(row);
    if (src === 'listing') return String(row.listing_id || row.id || '');
    if (src === 'masternode_hosting') return String(row.order_id || row.id || '');
    return String(row.id || row.item_id || '');
  }

  function rowKey(row) {
    return rowSource(row) + ':' + rowId(row);
  }

  function statusBucket(row) {
    if (row && row.status_bucket) return String(row.status_bucket);
    var s = String((row && (row.purchase_status || row.status)) || 'completed').toLowerCase();
    if (['pending', 'pending_payment', 'quoted', 'unpaid', 'awaiting', 'processing', 'active', 'listed', 'reserved'].indexOf(s) !== -1) {
      return 'pending';
    }
    if (s === 'refunded') return 'refunded';
    if (['cancelled', 'canceled', 'expired', 'failed'].indexOf(s) !== -1) {
      return 'cancelled';
    }
    return 'completed';
  }

  function formatStatus(row) {
    var raw = String((row && (row.purchase_status || row.status)) || '').trim().toLowerCase();
    if (STATUS_LABELS[raw]) return STATUS_LABELS[raw];
    var bucket = statusBucket(row);
    if (STATUS_LABELS[bucket]) return STATUS_LABELS[bucket];
    return raw ? raw.replace(/_/g, ' ') : 'Completed';
  }

  function formatPayment(row) {
    row = row || {};
    if (row.payment_method_label) return String(row.payment_method_label);
    var method = String(row.payment_method || row.price_type || '').toLowerCase();
    if (method === 'paypal' || method === 'paypal_mn2_hosting') return 'PayPal';
    if (method === 'coins' || method === 'credits') return 'Coins';
    if (method === 'mn2') return 'MN2 balance';
    if (method === 'mn2_onchain') return 'MN2 on-chain';
    if (method === 'points' || method === 'unified_points') return 'Points';
    if (method === 'casino') return 'Casino';
    if (method === 'exchange') return 'Exchange';
    if (rowSource(row) === 'listing') return 'Coins';
    if (rowSource(row) === 'masternode_hosting') return 'PayPal';
    return method ? method.replace(/_/g, ' ') : '—';
  }

  function formatPrice(row) {
    row = row || {};
    if (row.amount_label) return String(row.amount_label);
    if (rowSource(row) === 'listing' || row.listing_id) {
      var coins = row.price_paid_coins != null ? row.price_paid_coins : row.price_coins;
      return String(coins || 0) + ' coins';
    }
    if (rowSource(row) === 'masternode_hosting' || row.price_type === 'paypal_mn2_hosting') {
      var hostMethod = String(row.payment_method || row.price_type || '').toLowerCase();
      if ((hostMethod === 'coins' || hostMethod === 'credits') && row.coins_total) {
        return String(row.coins_total) + ' coins';
      }
      if ((hostMethod === 'mn2' || hostMethod === 'mn2_onchain') && row.mn2_total != null) {
        var hostMn2 = Number(row.mn2_total);
        return (isNaN(hostMn2) ? String(row.mn2_total) : hostMn2.toFixed(4)) +
          ' MN2' + (hostMethod === 'mn2_onchain' ? ' (on-chain)' : '');
      }
      var hostUsd = row.usd_total != null ? Number(row.usd_total) : null;
      if (hostUsd != null && !isNaN(hostUsd)) return '$' + hostUsd.toFixed(2) + ' PayPal';
      return 'PayPal';
    }
    var type = String(row.price_type || '').toLowerCase();
    var points = row.price_paid_points;
    if (type === 'coins') {
      return String(row.price_paid_coins || 0) + ' coins';
    }
    if (type === 'paypal' || type === 'paypal_mn2_hosting') {
      var usd = points && typeof points === 'object' && points.usd != null ? Number(points.usd) : null;
      return usd != null && !isNaN(usd) ? '$' + usd.toFixed(2) + ' PayPal' : 'PayPal';
    }
    if (type === 'mn2' || type === 'mn2_onchain') {
      var mn2Paid =
        points && typeof points === 'object' && points.mn2 != null ? points.mn2 : points;
      var mn2Text = typeof mn2Paid === 'number' ? mn2Paid.toFixed(4) : String(mn2Paid || '');
      return mn2Text + ' MN2' + (type === 'mn2_onchain' ? ' (on-chain)' : '');
    }
    if (type === 'points' || type === 'unified_points' || points) {
      if (points && typeof points === 'object') {
        var keys = Object.keys(points);
        if (keys.length === 1) return String(points[keys[0]]) + ' ' + keys[0];
      }
      return 'points';
    }
    if (row.price_paid_coins) return String(row.price_paid_coins) + ' coins';
    return '—';
  }

  function formatDate(row) {
    var raw = row && (row.sold_at || row.paid_at || row.created_at);
    if (!raw) return '—';
    var d = new Date(raw);
    if (isNaN(d.getTime())) return String(raw);
    try {
      return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    } catch (e) {
      return d.toLocaleString();
    }
  }

  function classifyRow(row) {
    var tax = global.ShopTaxonomy;
    var copy = tax && typeof tax.enrich === 'function' ? tax.enrich(row || {}) : Object.assign({}, row || {});
    if (!copy.subcategory) copy.subcategory = 'other';
    copy.source = rowSource(copy);
    copy.status_bucket = statusBucket(copy);
    return copy;
  }

  function snapshot(row) {
    return {
      source: rowSource(row),
      id: rowId(row),
      item_name: row.item_name || row.item_id || 'Item',
      quantity: row.quantity || 1,
      price_label: formatPrice(row),
      status: formatStatus(row),
      date: formatDate(row),
    };
  }

  function filterOrders(rows, opts) {
    opts = opts || {};
    var sub = opts.subcategory || 'all';
    var status = opts.status || 'all';
    return (rows || []).filter(function (r) {
      if (sub !== 'all' && String(r.subcategory || 'other') !== sub) return false;
      if (status !== 'all' && statusBucket(r) !== status) return false;
      return true;
    });
  }

  function statusTabs(rows) {
    var counts = { all: (rows || []).length, pending: 0, completed: 0, refunded: 0, cancelled: 0 };
    (rows || []).forEach(function (r) {
      var b = statusBucket(r);
      if (counts[b] != null) counts[b] += 1;
    });
    var tabs = [
      { id: 'all', label: 'All', count: counts.all },
      { id: 'pending', label: 'Pending', count: counts.pending },
      { id: 'completed', label: 'Completed', count: counts.completed },
    ];
    if (counts.refunded) tabs.push({ id: 'refunded', label: 'Refunded', count: counts.refunded });
    if (counts.cancelled) tabs.push({ id: 'cancelled', label: 'Cancelled', count: counts.cancelled });
    return tabs;
  }

  function subcategoryTabs(rows) {
    var tax = global.ShopTaxonomy;
    var counts = {};
    (rows || []).forEach(function (r) {
      var id = r.subcategory || 'other';
      counts[id] = (counts[id] || 0) + 1;
    });
    var tabs = [{ id: 'all', label: 'All', count: (rows || []).length }];
    var source = (tax && tax.INVENTORY_SUBCATS) || [];
    source.forEach(function (s) {
      if (s.id === 'all') return;
      if (counts[s.id]) tabs.push({ id: s.id, label: s.label, count: counts[s.id] });
    });
    Object.keys(counts).forEach(function (id) {
      if (!tabs.some(function (t) { return t.id === id; })) {
        tabs.push({
          id: id,
          label: (tax && tax.subcatLabel(id)) || id,
          count: counts[id],
        });
      }
    });
    return tabs;
  }

  function emptyHtml(message) {
    return '<p class="shop-order-empty" style="margin:0;">' + escapeHtml(message) + '</p>';
  }

  function errorHtml(message) {
    return (
      '<p class="shop-order-error" style="margin:0;color:#ffaa00;">' +
      escapeHtml(message) +
      '</p>'
    );
  }

  function rowHtml(p) {
    var tax = global.ShopTaxonomy;
    var name = p.item_name || p.item_id || 'Item';
    var subLabel = tax && tax.subcatLabel ? tax.subcatLabel(p.subcategory || 'other') : p.subcategory || '';
    var bucket = statusBucket(p);
    var key = rowKey(p);
    var checked = Object.prototype.hasOwnProperty.call(selected, key) ? ' checked' : '';
    return (
      '<tr class="shop-order-row" data-status="' +
      escapeHtml(bucket) +
      '" data-subcategory="' +
      escapeHtml(p.subcategory || 'other') +
      '" data-order-key="' +
      escapeHtml(key) +
      '">' +
      '<td><input type="checkbox" class="shop-order-check" data-order-key="' +
      escapeHtml(key) +
      '" aria-label="Select ' +
      escapeHtml(name) +
      '"' +
      checked +
      '></td>' +
      '<td><strong>' +
      escapeHtml(name) +
      '</strong>' +
      (subLabel ? '<div class="shop-order-meta">' + escapeHtml(subLabel) + '</div>' : '') +
      '</td>' +
      '<td>' +
      escapeHtml(String(p.quantity || 1)) +
      '</td>' +
      '<td>' +
      escapeHtml(formatPrice(p)) +
      '</td>' +
      '<td>' +
      escapeHtml(formatPayment(p)) +
      '</td>' +
      '<td>' +
      escapeHtml(formatDate(p)) +
      '</td>' +
      '<td><span class="shop-order-status is-' +
      escapeHtml(bucket) +
      '">' +
      escapeHtml(formatStatus(p)) +
      '</span></td>' +
      '</tr>'
    );
  }

  function tableHtml(rows) {
    var allOn = rows.length && rows.every(function (r) {
      return Object.prototype.hasOwnProperty.call(selected, rowKey(r));
    });
    return (
      '<div class="shop-order-table-wrap"><table class="shop-order-table">' +
      '<thead><tr>' +
      '<th scope="col"><input type="checkbox" class="shop-order-check-all" aria-label="Select all visible orders"' +
      (allOn ? ' checked' : '') +
      '></th>' +
      '<th scope="col">Item</th>' +
      '<th scope="col">Qty</th>' +
      '<th scope="col">Price</th>' +
      '<th scope="col">Payment</th>' +
      '<th scope="col">Date</th>' +
      '<th scope="col">Status</th>' +
      '</tr></thead><tbody>' +
      rows.map(rowHtml).join('') +
      '</tbody></table></div>'
    );
  }

  function groupedHtml(rows) {
    var tax = global.ShopTaxonomy;
    var groups = {};
    var order = [];
    rows.forEach(function (p) {
      var key = p.subcategory || 'other';
      if (!groups[key]) {
        groups[key] = [];
        order.push(key);
      }
      groups[key].push(p);
    });
    if (order.length <= 1) return tableHtml(rows);
    return order
      .map(function (key) {
        var label = tax && tax.subcatLabel ? tax.subcatLabel(key) : key;
        return (
          '<h4 class="shop-order-group-title">' +
          escapeHtml(label) +
          '</h4>' +
          tableHtml(groups[key])
        );
      })
      .join('');
  }

  function renderChips(nav, tabs, activeId, onPick) {
    var tax = global.ShopTaxonomy;
    if (tax && typeof tax.renderChips === 'function') {
      tax.renderChips(nav, tabs, activeId, onPick);
      return;
    }
    if (!nav) return;
    nav.innerHTML = (tabs || [])
      .map(function (t) {
        var on = t.id === activeId;
        var count = t.count != null ? ' (' + t.count + ')' : '';
        return (
          '<button type="button" class="shop-subnav-btn' +
          (on ? ' active' : '') +
          '" data-tax-id="' +
          escapeHtml(t.id) +
          '">' +
          escapeHtml(t.label) +
          count +
          '</button>'
        );
      })
      .join('');
    nav.querySelectorAll('[data-tax-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (typeof onPick === 'function') onPick(btn.getAttribute('data-tax-id'));
      });
    });
  }

  function selectedCount() {
    return Object.keys(selected).length;
  }

  function selectedItems() {
    return Object.keys(selected).map(function (key) {
      return { source: selected[key].source, id: selected[key].id };
    });
  }

  var pdfButton = null;
  var pdfHint = null;
  var pdfUserId = 'default_user';
  var pdfBusy = false;

  function syncPdfButton() {
    var n = selectedCount();
    if (pdfButton) {
      pdfButton.disabled = n === 0 || pdfBusy;
      pdfButton.setAttribute('aria-disabled', pdfButton.disabled ? 'true' : 'false');
    }
    if (pdfHint) {
      if (pdfBusy) pdfHint.textContent = 'Building PDF…';
      else if (n === 0) pdfHint.textContent = 'Select orders first';
      else pdfHint.textContent = n + ' selected';
    }
  }

  function bindChecks(listEl, classified) {
    if (!listEl || typeof listEl.querySelectorAll !== 'function') return;
    var byKey = {};
    (classified || []).forEach(function (row) {
      byKey[rowKey(row)] = row;
    });
    listEl.querySelectorAll('.shop-order-check').forEach(function (box) {
      box.addEventListener('change', function () {
        var key = box.getAttribute('data-order-key');
        var row = byKey[key];
        if (box.checked && row) selected[key] = snapshot(row);
        else delete selected[key];
        syncPdfButton();
      });
    });
    listEl.querySelectorAll('.shop-order-check-all').forEach(function (box) {
      var table = box.closest('table');
      box.addEventListener('change', function () {
        var boxes = table ? table.querySelectorAll('tbody .shop-order-check') : [];
        boxes.forEach(function (cb) {
          cb.checked = box.checked;
          var key = cb.getAttribute('data-order-key');
          var row = byKey[key];
          if (box.checked && row) selected[key] = snapshot(row);
          else delete selected[key];
        });
        syncPdfButton();
      });
    });
  }

  function render(opts) {
    opts = opts || {};
    var listEl = opts.listEl;
    var classified = (opts.rows || []).map(classifyRow);
    var sub = opts.subcategory || 'all';
    var status = opts.status || 'all';
    if (opts.statusNavEl) {
      renderChips(opts.statusNavEl, statusTabs(classified), status, opts.onStatus);
    }
    if (opts.subnavEl) {
      renderChips(opts.subnavEl, subcategoryTabs(classified), sub, opts.onSubcategory);
    }
    if (!listEl) return classified;
    if (!classified.length) {
      listEl.innerHTML = emptyHtml(opts.emptyMessage || 'No shop orders yet. Catalog purchases appear here.');
      return classified;
    }
    var visible = filterOrders(classified, { subcategory: sub, status: status });
    if (!visible.length) {
      listEl.innerHTML = emptyHtml(opts.filterEmptyMessage || 'No orders match this filter.');
      return classified;
    }
    var html = sub === 'all' && !opts.skipGroup ? groupedHtml(visible) : tableHtml(visible);
    listEl.innerHTML = html;
    bindChecks(listEl, classified);
    return classified;
  }

  function renderError(listEl, message) {
    if (listEl) listEl.innerHTML = errorHtml(message || 'Could not load shop orders.');
  }

  function downloadPdf(userId) {
    var items = selectedItems();
    if (!items.length) {
      syncPdfButton();
      return Promise.resolve(false);
    }
    pdfBusy = true;
    syncPdfButton();
    return fetch('/api/shop/order-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId || pdfUserId, items: items }),
    })
      .then(function (res) {
        if (res.status === 400) {
          return res.json().then(function (body) {
            throw new Error((body && body.error) || 'select orders first');
          });
        }
        if (!res.ok) throw new Error('Could not build PDF');
        return res.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'shop-orders.pdf';
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
        return true;
      })
      .catch(function (err) {
        if (pdfHint) pdfHint.textContent = err && err.message ? err.message : 'Could not build PDF';
        return false;
      })
      .then(function (ok) {
        pdfBusy = false;
        if (ok) syncPdfButton();
        return ok;
      });
  }

  function bindPdfControls(opts) {
    opts = opts || {};
    pdfButton = opts.button || null;
    pdfHint = opts.hintEl || null;
    if (opts.userId) pdfUserId = opts.userId;
    if (pdfButton && !pdfButton.getAttribute('data-pdf-bound')) {
      pdfButton.setAttribute('data-pdf-bound', '1');
      pdfButton.addEventListener('click', function () {
        if (selectedCount() === 0) {
          syncPdfButton();
          return;
        }
        downloadPdf(pdfUserId);
      });
    }
    syncPdfButton();
  }

  global.ShopOrderList = {
    escapeHtml: escapeHtml,
    statusBucket: statusBucket,
    formatStatus: formatStatus,
    formatPrice: formatPrice,
    formatPayment: formatPayment,
    formatDate: formatDate,
    classifyRow: classifyRow,
    filterOrders: filterOrders,
    statusTabs: statusTabs,
    subcategoryTabs: subcategoryTabs,
    rowKey: rowKey,
    selectedCount: selectedCount,
    selectedItems: selectedItems,
    render: render,
    renderError: renderError,
    bindPdfControls: bindPdfControls,
    downloadPdf: downloadPdf,
    syncPdfButton: syncPdfButton,
  };
})(typeof window !== 'undefined' ? window : globalThis);
