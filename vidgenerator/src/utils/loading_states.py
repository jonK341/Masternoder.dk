"""
Loading state utilities for frontend
Provides standardized loading indicators and skeleton screens
"""
from typing import Dict, Any, Optional

class LoadingStates:
    """Standardized loading state management"""
    
    @staticmethod
    def create_loading_html(message: str = "Loading...", size: str = "medium") -> str:
        """
        Create HTML for loading spinner
        
        Args:
            message: Loading message
            size: Size of spinner (small, medium, large)
        
        Returns:
            HTML string for loading indicator
        """
        size_classes = {
            'small': 'loading-small',
            'medium': 'loading-medium',
            'large': 'loading-large'
        }
        size_class = size_classes.get(size, 'loading-medium')
        
        return f'''
        <div class="loading-container {size_class}">
            <div class="loading-spinner"></div>
            <div class="loading-message">{message}</div>
        </div>
        '''
    
    @staticmethod
    def create_skeleton_screen(type: str = "card", count: int = 1) -> str:
        """
        Create HTML for skeleton screen
        
        Args:
            type: Type of skeleton (card, list, grid)
            count: Number of skeleton items
        
        Returns:
            HTML string for skeleton screen
        """
        skeletons = []
        for i in range(count):
            if type == "card":
                skeletons.append('''
                <div class="skeleton-card">
                    <div class="skeleton-image"></div>
                    <div class="skeleton-content">
                        <div class="skeleton-title"></div>
                        <div class="skeleton-text"></div>
                        <div class="skeleton-text short"></div>
                    </div>
                </div>
                ''')
            elif type == "list":
                skeletons.append('<div class="skeleton-list-item"></div>')
            elif type == "grid":
                skeletons.append('<div class="skeleton-grid-item"></div>')
        
        return '<div class="skeleton-container">' + ''.join(skeletons) + '</div>'
    
    @staticmethod
    def create_progress_bar(progress: int, message: Optional[str] = None) -> str:
        """
        Create HTML for progress bar
        
        Args:
            progress: Progress percentage (0-100)
            message: Optional progress message
        
        Returns:
            HTML string for progress bar
        """
        message_html = f'<div class="progress-message">{message}</div>' if message else ''
        return f'''
        <div class="progress-container">
            {message_html}
            <div class="progress-bar">
                <div class="progress-fill" style="width: {progress}%"></div>
            </div>
            <div class="progress-percentage">{progress}%</div>
        </div>
        '''

