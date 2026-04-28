/**
 * Compendium (Rulebook V2.1) view tracker — reports page view to API and awards compendium_points.
 * Uses user_id from localStorage (game_user_id) or backend user index API.
 */
(function() {
    var pageNum = null;
    var path = typeof window !== 'undefined' && window.location && window.location.pathname;
    if (path && path.indexOf('/compendium/') !== -1) {
        if (path.indexOf('hunters-rulebook') !== -1) {
            pageNum = 11;
        } else {
            var rm = path.match(/rulebook-v(\d+)(?:\.html)?(?:\/)?$/i);
            if (rm) {
                var vMap = {1:12,4:13,5:14,6:15,7:16,8:17,9:18,10:19,11:20,12:21,13:22,14:23,16:25};
                pageNum = vMap[parseInt(rm[1],10)] || 12;
            } else {
                var m = path.match(/page-(\d+)\.html/);
                if (m) pageNum = parseInt(m[1], 10);
            }
        }
    }
    if (pageNum === null || pageNum < 1 || pageNum > 25) return;

    var userId = typeof localStorage !== 'undefined' && localStorage.getItem('game_user_id') || 'default_user';
    var API_BASE = '/api';
    var payload = { user_id: userId, page_number: pageNum };

    function sendView() {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', API_BASE + '/compendium/view', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify(payload));
        } catch (e) {}
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', sendView);
    } else {
        sendView();
    }
})();
