/**
 * Trophy NFT presentation helpers.
 * Shared by the trophies page gallery and Node unit tests.
 */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) {
        module.exports = api;
    }
    root.TrophyNft = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    function esc(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function rarityOf(trophy) {
        var r = String((trophy && trophy.rarity) || 'common').toLowerCase();
        if (r !== 'common' && r !== 'rare' && r !== 'epic' && r !== 'legendary') {
            r = 'common';
        }
        return r;
    }

    function contractId() {
        return 'MN2-TROPHY';
    }

    function tokenIdFromTrophy(trophy, collection) {
        var id = String(trophy && trophy.id != null ? trophy.id : '');
        var list = collection || [];
        var idx = -1;
        var i;
        for (i = 0; i < list.length; i++) {
            if (String(list[i] && list[i].id) === id) {
                idx = i;
                break;
            }
        }
        var n = idx >= 0 ? idx + 1 : 0;
        var s = String(n);
        while (s.length < 4) {
            s = '0' + s;
        }
        return '#' + s;
    }

    function buildNftCardHtml(trophy, options) {
        options = options || {};
        trophy = trophy || {};
        var disp = options.display || {};
        var name = disp.name != null ? disp.name : (trophy.name || trophy.id || 'Untitled');
        var icon = disp.icon != null ? disp.icon : (trophy.icon || '\uD83C\uDFC6');
        var rarity = rarityOf(trophy);
        var minted = !!trophy.unlocked;
        var token = tokenIdFromTrophy(trophy, options.collection);
        var category = trophy.category || 'collectible';
        var reward = trophy.reward || 0;
        var statusLabel = minted ? 'Minted' : 'Unminted';
        var statusClass = minted ? 'minted' : 'unminted';
        var prog = options.progress;
        var progressHtml = '';
        if (!minted && prog && prog.ratio != null) {
            var pct = Math.round(prog.ratio * 100);
            progressHtml = '<div class="nft-card-progress" aria-hidden="true">' +
                '<div class="nft-card-progress-fill" style="width:' + pct + '%"></div></div>' +
                '<div class="nft-card-progress-text">' + pct + '% minted</div>';
        }
        return '<article class="nft-card rarity-' + esc(rarity) + ' ' + statusClass +
            '" data-trophy-id="' + esc(trophy.id || '') + '" tabindex="0" role="button"' +
            ' aria-label="' + esc(statusLabel + ' ' + rarity + ' NFT ' + name) + '">' +
            '<div class="nft-card-art">' +
            '<div class="nft-card-hologram"></div>' +
            '<div class="nft-card-hex"></div>' +
            '<div class="nft-card-icon">' + esc(icon) + '</div>' +
            '<span class="nft-token-id">' + esc(token) + '</span>' +
            '<span class="nft-rarity-chip">' + esc(rarity) + '</span>' +
            '</div>' +
            '<div class="nft-card-body">' +
            '<div class="nft-collection">MN2 Trophies</div>' +
            '<h3 class="nft-card-name">' + esc(name) + '</h3>' +
            '<div class="nft-traits">' +
            '<span class="nft-trait">' + esc(category) + '</span>' +
            '</div>' +
            progressHtml +
            '<div class="nft-card-footer">' +
            '<span class="nft-status ' + statusClass + '">' + statusLabel + '</span>' +
            '<span class="nft-price">' + esc(reward) + ' PTS</span>' +
            '</div>' +
            '</div>' +
            '</article>';
    }

    function filterCollection(trophies, filter, search) {
        var list = (trophies || []).slice();
        if (filter === 'unlocked' || filter === 'minted') {
            list = list.filter(function (t) { return t.unlocked; });
        } else if (filter === 'locked' || filter === 'unminted') {
            list = list.filter(function (t) { return !t.unlocked; });
        } else if (filter && filter !== 'all' && filter !== 'gallery' && filter !== 'table' && filter !== 'ledger') {
            list = list.filter(function (t) { return t.category === filter; });
        }
        var q = String(search || '').trim().toLowerCase();
        if (q) {
            list = list.filter(function (t) {
                return [t.name, t.description, t.requirement, t.category, t.id]
                    .some(function (v) { return String(v || '').toLowerCase().indexOf(q) !== -1; });
            });
        }
        return list;
    }

    return {
        tokenIdFromTrophy: tokenIdFromTrophy,
        buildNftCardHtml: buildNftCardHtml,
        filterCollection: filterCollection,
        rarityOf: rarityOf,
        contractId: contractId,
        esc: esc
    };
});
