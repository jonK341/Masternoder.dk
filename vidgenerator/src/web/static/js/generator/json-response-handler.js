/**
 * JSON Response Handler
 * Safely handles API responses that might return HTML instead of JSON
 */

class JSONResponseHandler {
    /**
     * Safely parse JSON response, handling HTML error pages
     */
    static async safeJson(response) {
        // Check if response is actually JSON
        const contentType = response.headers.get('content-type');
        
        if (!contentType || !contentType.includes('application/json')) {
            // Response is not JSON - might be HTML error page
            const text = await response.text();
            
            // Try to extract error message from HTML
            const errorMatch = text.match(/<title[^>]*>([^<]+)<\/title>/i) || 
                              text.match(/<h1[^>]*>([^<]+)<\/h1>/i) ||
                              text.match(/Error[:\s]+([^<\n]+)/i);
            
            const errorMessage = errorMatch ? errorMatch[1].trim() : 'Server returned HTML instead of JSON';
            
            throw new Error(`API Error (${response.status}): ${errorMessage}`);
        }
        
        // Parse JSON
        try {
            return await response.json();
        } catch (parseError) {
            // Even though content-type says JSON, parsing failed
            const text = await response.text();
            throw new Error(`Invalid JSON response: ${parseError.message}. Response: ${text.substring(0, 200)}`);
        }
    }
    
    /**
     * Check if response is OK and handle errors
     */
    static async checkResponse(response) {
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            
            try {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } else {
                    // HTML error page
                    const text = await response.text();
                    const errorMatch = text.match(/<title[^>]*>([^<]+)<\/title>/i) || 
                                      text.match(/<h1[^>]*>([^<]+)<\/h1>/i);
                    if (errorMatch) {
                        errorMessage = errorMatch[1].trim();
                    }
                }
            } catch (e) {
                // Couldn't parse error, use default
            }
            
            const error = new Error(errorMessage);
            error.status = response.status;
            error.response = response;
            throw error;
        }
        
        return response;
    }
    
    /**
     * Fetch with automatic JSON handling and error checking
     */
    static async fetchJson(url, options = {}) {
        try {
            const response = await fetch(url, options);
            await this.checkResponse(response);
            return await this.safeJson(response);
        } catch (error) {
            // Enhance error with URL for debugging
            error.url = url;
            throw error;
        }
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.JSONResponseHandler = JSONResponseHandler;
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JSONResponseHandler;
}

