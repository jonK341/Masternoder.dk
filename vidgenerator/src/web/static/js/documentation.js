/**
 * Documentation System
 * Client-side documentation management
 */

const DOCS_API = window.location.origin + '/vidgenerator/api/docs';

class DocumentationSystem {
    constructor() {
        this.currentResults = [];
        this.categories = [];
        this.init();
    }
    
    async init() {
        await this.loadStats();
        await this.loadCategories();
        await this.loadAllDocs();
        this.setupEventListeners();
    }
    
    async loadStats() {
        try {
            const response = await fetch(`${DOCS_API}/stats`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    document.getElementById('stat-total').textContent = data.stats.total;
                    document.getElementById('stat-fixes').textContent = data.stats.fixes;
                    document.getElementById('stat-improvements').textContent = data.stats.improvements;
                    document.getElementById('stat-categories').textContent = Object.keys(data.stats.categories).length;
                }
            }
        } catch (error) {
            console.error('[Documentation] Error loading stats:', error);
        }
    }
    
    async loadCategories() {
        try {
            const response = await fetch(`${DOCS_API}/categories`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.categories = data.categories;
                    this.renderCategoryFilter();
                    this.renderCategoryList();
                }
            }
        } catch (error) {
            console.error('[Documentation] Error loading categories:', error);
        }
    }
    
    renderCategoryFilter() {
        const filter = document.getElementById('category-filter');
        filter.innerHTML = '<option value="">All Categories</option>';
        this.categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
            filter.appendChild(option);
        });
    }
    
    renderCategoryList() {
        const list = document.getElementById('category-list');
        list.innerHTML = '';
        this.categories.forEach(cat => {
            const item = document.createElement('div');
            item.className = 'category-item';
            item.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
            item.onclick = () => {
                document.getElementById('category-filter').value = cat;
                this.search();
            };
            list.appendChild(item);
        });
    }
    
    async loadAllDocs() {
        try {
            const response = await fetch(`${DOCS_API}/search?q=`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.currentResults = data.results;
                    this.renderResults();
                }
            }
        } catch (error) {
            console.error('[Documentation] Error loading docs:', error);
        }
    }
    
    async search() {
        const query = document.getElementById('search-input').value;
        const category = document.getElementById('category-filter').value;
        const type = document.getElementById('type-filter').value;
        
        try {
            let url = `${DOCS_API}/search?q=${encodeURIComponent(query)}`;
            if (category) url += `&category=${encodeURIComponent(category)}`;
            if (type) url += `&type=${encodeURIComponent(type)}`;
            
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.currentResults = data.results;
                    this.renderResults();
                }
            }
        } catch (error) {
            console.error('[Documentation] Error searching:', error);
        }
    }
    
    renderResults() {
        const container = document.getElementById('docs-results');
        if (this.currentResults.length === 0) {
            container.innerHTML = '<div class="empty-state">No documentation found</div>';
            return;
        }
        
        container.innerHTML = this.currentResults.map(doc => `
            <div class="doc-entry ${doc.type}">
                <div class="doc-header">
                    <h3>${doc.title}</h3>
                    <div class="doc-meta">
                        <span class="badge badge-${doc.type === 'fix' ? 'success' : 'warning'}">${doc.type}</span>
                        <span class="badge">${doc.category}</span>
                        <span class="doc-date">${new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
                <div class="doc-body">
                    <p>${doc.description || 'No description provided'}</p>
                    ${doc.tags && doc.tags.length > 0 ? `
                        <div class="doc-tags">
                            ${doc.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }
    
    async addDocumentation() {
        document.getElementById('add-doc-modal').style.display = 'flex';
    }
    
    async saveDocumentation() {
        const type = document.getElementById('doc-type').value;
        const title = document.getElementById('doc-title').value;
        const description = document.getElementById('doc-description').value;
        const category = document.getElementById('doc-category').value;
        const tags = document.getElementById('doc-tags').value.split(',').map(t => t.trim()).filter(t => t);
        
        if (!title) {
            alert('Title is required');
            return;
        }
        
        try {
            const response = await fetch(`${DOCS_API}/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, title, description, category, tags })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    closeModal();
                    await this.loadStats();
                    await this.loadCategories();
                    await this.loadAllDocs();
                }
            }
        } catch (error) {
            console.error('[Documentation] Error saving:', error);
            alert('Error saving documentation');
        }
    }
    
    setupEventListeners() {
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.search();
            }
        });
        
        document.getElementById('category-filter').addEventListener('change', () => {
            this.search();
        });
        
        document.getElementById('type-filter').addEventListener('change', () => {
            this.search();
        });
    }
}

// Global functions
let docsSystem;

document.addEventListener('DOMContentLoaded', () => {
    docsSystem = new DocumentationSystem();
    window.docsSystem = docsSystem;
});

function searchDocs() {
    if (docsSystem) docsSystem.search();
}

function addDocumentation() {
    if (docsSystem) docsSystem.addDocumentation();
}

function saveDocumentation() {
    if (docsSystem) docsSystem.saveDocumentation();
}

function closeModal() {
    document.getElementById('add-doc-modal').style.display = 'none';
    // Reset form
    document.getElementById('doc-title').value = '';
    document.getElementById('doc-description').value = '';
    document.getElementById('doc-tags').value = '';
}

