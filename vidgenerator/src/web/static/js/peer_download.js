/**
 * Peer-to-Peer Download System
 * Supports double or triple peer downloads for faster transfer
 */
class PeerDownloadManager {
    constructor() {
        this.peers = [];
        this.activeDownloads = new Map();
        this.baseUrl = window.location.origin;
    }
    
    async registerAsPeer(userId, resourceId, resourceUrl) {
        """Register this client as a peer for a resource"""
        try {
            const response = await fetch(`${this.baseUrl}/vidgenerator/api/game/peers/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    resource_id: resourceId,
                    user_id: userId,
                    url: resourceUrl,
                    ip: await this.getClientIP(),
                    capabilities: ['http', 'https'],
                    bandwidth: await this.estimateBandwidth()
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('[PeerDownload] Registered as peer:', data);
                return data;
            }
        } catch (error) {
            console.error('[PeerDownload] Registration failed:', error);
        }
        return null;
    }
    
    async getDownloadPeers(resourceId, userId, count = 3) {
        """Get peers for download (double or triple)"""
        try {
            const response = await fetch(
                `${this.baseUrl}/vidgenerator/api/game/peers/download/${resourceId}?user_id=${userId}&count=${count}`
            );
            
            if (response.ok) {
                const data = await response.json();
                console.log('[PeerDownload] Got peers:', data);
                return data.result?.peers || [];
            }
        } catch (error) {
            console.error('[PeerDownload] Failed to get peers:', error);
        }
        return [];
    }
    
    async downloadFromPeers(resourceId, userId, peers, onProgress) {
        """Download from multiple peers simultaneously"""
        if (!peers || peers.length === 0) {
            console.warn('[PeerDownload] No peers available, using direct download');
            return null;
        }
        
        console.log(`[PeerDownload] Downloading from ${peers.length} peers`);
        
        // Create download chunks from each peer
        const chunkPromises = peers.map((peer, index) => {
            return this.downloadChunk(peer.url, index, peers.length, onProgress);
        });
        
        try {
            const chunks = await Promise.all(chunkPromises);
            // Combine chunks
            const blob = new Blob(chunks, { type: 'video/mp4' });
            return blob;
        } catch (error) {
            console.error('[PeerDownload] Download failed:', error);
            return null;
        }
    }
    
    async downloadChunk(url, chunkIndex, totalChunks, onProgress) {
        """Download a chunk from a peer"""
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', url, true);
            xhr.responseType = 'blob';
            
            xhr.onprogress = (e) => {
                if (e.lengthComputable && onProgress) {
                    const progress = ((chunkIndex / totalChunks) + (e.loaded / e.total / totalChunks)) * 100;
                    onProgress(progress);
                }
            };
            
            xhr.onload = () => {
                if (xhr.status === 200) {
                    resolve(xhr.response);
                } else {
                    reject(new Error(`HTTP ${xhr.status}`));
                }
            };
            
            xhr.onerror = () => reject(new Error('Network error'));
            xhr.send();
        });
    }
    
    async getClientIP() {
        """Get client IP address"""
        try {
            const response = await fetch('https://api.ipify.org?format=json');
            const data = await response.json();
            return data.ip;
        } catch {
            return 'unknown';
        }
    }
    
    async estimateBandwidth() {
        """Estimate client bandwidth"""
        // Simple estimation
        return navigator.connection?.effectiveType === '4g' ? 10000 : 5000;
    }
}

// Global instance
window.peerDownloadManager = new PeerDownloadManager();

