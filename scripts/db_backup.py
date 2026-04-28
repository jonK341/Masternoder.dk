#!/usr/bin/env python3
"""
Database backup script
Automatically backs up SQLite database
"""
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.app import create_app
from src.db.models import db
from src.db.init_db import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_database(keep_days: int = 30):
    """
    Backup database and clean up old backups
    
    Args:
        keep_days: Number of days to keep backups (default: 30)
    """
    app = create_app()
    manager = DatabaseManager(db, app)
    
    try:
        # Create backup
        backup_path = manager.backup_database()
        if backup_path:
            logger.info(f"✅ Database backup created: {backup_path}")
            
            # Clean up old backups
            if manager.db_path:
                db_dir = Path(os.path.dirname(manager.db_path))
                db_name = os.path.basename(manager.db_path)
                
                cutoff_date = datetime.now() - timedelta(days=keep_days)
                
                # Find and delete old backups
                deleted_count = 0
                for backup_file in db_dir.glob(f"{db_name}.backup_*"):
                    try:
                        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                        if file_time < cutoff_date:
                            backup_file.unlink()
                            deleted_count += 1
                            logger.info(f"Deleted old backup: {backup_file.name}")
                    except Exception as e:
                        logger.warning(f"Error deleting backup {backup_file.name}: {e}")
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old backup(s)")
            
            return True
        else:
            logger.error("❌ Failed to create backup")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error during backup: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backup database')
    parser.add_argument('--keep-days', type=int, default=30, help='Days to keep backups (default: 30)')
    
    args = parser.parse_args()
    
    success = backup_database(keep_days=args.keep_days)
    sys.exit(0 if success else 1)

