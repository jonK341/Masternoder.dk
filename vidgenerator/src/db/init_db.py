"""
Database initialization and management utilities
Handles automatic database initialization, migrations, and health checks
"""
import os
import logging
from pathlib import Path
from typing import Optional, List
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

logger = logging.getLogger('vidgenerator.db')


class DatabaseManager:
    """Manages database initialization, migrations, and health checks"""
    
    def __init__(self, db, app):
        """
        Initialize database manager
        
        Args:
            db: SQLAlchemy database instance
            app: Flask application instance
        """
        self.db = db
        self.app = app
        self.db_path = self._get_db_path()
    
    def _get_db_path(self) -> Optional[str]:
        """Get database file path"""
        db_uri = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('sqlite:///'):
            return db_uri.replace('sqlite:///', '')
        return None
    
    def initialize_database(self, force: bool = False) -> bool:
        """
        Initialize database - create all tables if they don't exist
        
        Args:
            force: If True, recreate all tables (WARNING: deletes data)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.app.app_context():
                if force:
                    logger.warning("FORCE initialization - dropping all tables!")
                    self.db.drop_all()
                
                logger.info("Creating database tables...")
                self.db.create_all()
                
                # Verify tables were created
                inspector = inspect(self.db.engine)
                tables = inspector.get_table_names()
                logger.info(f"Database initialized with {len(tables)} tables: {', '.join(tables)}")
                
                # Run migrations
                run_migrations_if_needed(self.db, self.app)
                
                # Initialize default data
                self._initialize_default_data()
                
                return True
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            return False
    
    def _initialize_default_data(self):
        """Initialize default data (categories, etc.)"""
        try:
            # Initialize content categories
            from src.services.content_categories import content_category_service
            categories = content_category_service.get_all_categories()
            logger.info(f"Initialized {len(categories)} default categories")
        except Exception as e:
            logger.warning(f"Could not initialize default data: {e}")
    
    def check_database_health(self) -> dict:
        """
        Check database health and return status information
        
        Returns:
            Dictionary with health check results
        """
        health = {
            'status': 'unknown',
            'tables': [],
            'table_count': 0,
            'db_exists': False,
            'db_size': 0,
            'issues': []
        }
        
        try:
            with self.app.app_context():
                # Check if database file exists (for SQLite)
                if self.db_path and os.path.exists(self.db_path):
                    health['db_exists'] = True
                    health['db_size'] = os.path.getsize(self.db_path)
                
                # Check tables
                inspector = inspect(self.db.engine)
                health['tables'] = inspector.get_table_names()
                health['table_count'] = len(health['tables'])
                
                # Test a simple query
                try:
                    self.db.session.execute(text('SELECT 1'))
                    self.db.session.commit()
                    health['status'] = 'healthy'
                except Exception as e:
                    health['status'] = 'unhealthy'
                    health['issues'].append(f"Query test failed: {str(e)}")
                
                # Check for required tables
                required_tables = ['documentaries', 'content_categories']
                missing_tables = [t for t in required_tables if t not in health['tables']]
                if missing_tables:
                    health['issues'].append(f"Missing required tables: {', '.join(missing_tables)}")
                    health['status'] = 'incomplete'  # Always mark as incomplete if tables are missing
                    
                    # Try to create missing tables
                    logger.warning(f"Missing required tables: {missing_tables}. Attempting to create...")
                    try:
                        db.create_all()
                        # Re-check
                        inspector = inspect(db.engine)
                        health['tables'] = inspector.get_table_names()
                        health['table_count'] = len(health['tables'])
                        missing_after = [t for t in required_tables if t not in health['tables']]
                        if not missing_after:
                            health['status'] = 'healthy'
                            health['issues'] = []
                            logger.info("Missing tables created successfully")
                    except Exception as create_err:
                        health['issues'].append(f"Failed to create missing tables: {str(create_err)}")
                        logger.error(f"Error creating missing tables: {create_err}", exc_info=True)
                
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"Health check failed: {str(e)}")
            logger.error(f"Database health check error: {e}", exc_info=True)
        
        return health
    
    def get_database_info(self) -> dict:
        """
        Get database information and statistics
        
        Returns:
            Dictionary with database information
        """
        info = {
            'uri': self.app.config.get('SQLALCHEMY_DATABASE_URI', ''),
            'db_type': 'unknown',
            'tables': [],
            'stats': {}
        }
        
        try:
            db_uri = info['uri']
            if db_uri.startswith('sqlite:///'):
                info['db_type'] = 'sqlite'
                info['db_path'] = db_uri.replace('sqlite:///', '')
            elif db_uri.startswith('postgresql://'):
                info['db_type'] = 'postgresql'
            elif db_uri.startswith('mysql://'):
                info['db_type'] = 'mysql'
            
            with self.app.app_context():
                inspector = inspect(self.db.engine)
                info['tables'] = inspector.get_table_names()
                
                # Get table statistics
                for table_name in info['tables']:
                    try:
                        result = self.db.session.execute(
                            text(f"SELECT COUNT(*) FROM {table_name}")
                        )
                        count = result.scalar()
                        info['stats'][table_name] = {'row_count': count}
                    except Exception as e:
                        info['stats'][table_name] = {'error': str(e)}
        
        except Exception as e:
            logger.error(f"Error getting database info: {e}", exc_info=True)
            info['error'] = str(e)
        
        return info
    
    def backup_database(self, backup_path: Optional[str] = None) -> Optional[str]:
        """
        Backup database (for SQLite, copy the file)
        
        Args:
            backup_path: Optional custom backup path
        
        Returns:
            Path to backup file, or None if failed
        """
        if not self.db_path or not os.path.exists(self.db_path):
            logger.warning("Database file not found, cannot backup")
            return None
        
        try:
            from datetime import datetime
            import shutil
            
            if not backup_path:
                # Default backup location: same directory as DB with timestamp
                db_dir = os.path.dirname(self.db_path)
                db_name = os.path.basename(self.db_path)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(db_dir, f"{db_name}.backup_{timestamp}")
            
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Error backing up database: {e}", exc_info=True)
            return None


def init_db_on_first_run(app, db) -> bool:
    """
    Initialize database on first run if tables don't exist
    
    This function checks if the database is initialized and creates
    tables if needed. Safe to call on every application start.
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
    
    Returns:
        True if database was initialized or already exists, False on error
    """
    manager = DatabaseManager(db, app)
    
    try:
        # Check if database is already initialized
        health = manager.check_database_health()
        
        if health['status'] == 'healthy':
            logger.info("Database already initialized and healthy")
            return True
        
        # Initialize if not healthy or incomplete
        logger.info("Initializing database (first run or incomplete)...")
        return manager.initialize_database(force=False)
    
    except Exception as e:
        logger.error(f"Error in database initialization: {e}", exc_info=True)
        return False

