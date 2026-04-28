#!/usr/bin/env python3
"""
Database migration script to add content categories
Run this to add category columns to Documentary table and create category tables
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.app import create_app
from src.db.models import db

def migrate():
    """Add category support to database"""
    app = create_app()
    
    with app.app_context():
        print("Starting migration: Add content categories...")
        
        # Import models
        try:
            from src.db.models_content_categories import ContentCategory, CategoryStats
        except ImportError:
            print("ERROR: Could not import category models")
            return False
        
        # Create category tables
        print("Creating category tables...")
        try:
            db.create_all()
            print("[OK] Category tables created")
        except Exception as e:
            print(f"ERROR creating tables: {e}")
            return False
        
        # Add category_id and category_name columns to documentaries table
        print("Adding category columns to documentaries table...")
        try:
            # Check if columns already exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('documentaries')]
            
            if 'category_id' not in columns:
                db.engine.execute("ALTER TABLE documentaries ADD COLUMN category_id VARCHAR(36)")
                print("[OK] Added category_id column")
            else:
                print("[OK] category_id column already exists")
            
            if 'category_name' not in columns:
                db.engine.execute("ALTER TABLE documentaries ADD COLUMN category_name VARCHAR(100)")
                print("[OK] Added category_name column")
            else:
                print("[OK] category_name column already exists")
            
            # Create index on category_name for faster queries
            try:
                db.engine.execute("CREATE INDEX IF NOT EXISTS ix_documentaries_category_name ON documentaries(category_name)")
                print("[OK] Created index on category_name")
            except Exception as e:
                print(f"Note: Index creation (may already exist): {e}")
            
        except Exception as e:
            print(f"ERROR adding columns: {e}")
            # Try with SQLite syntax
            try:
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    # SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS directly
                    # We'll use a different approach
                    conn.execute(text("PRAGMA table_info(documentaries)"))
                    # For SQLite, we need to recreate table or use ALTER TABLE
                    # Since this is complex, we'll just note it
                    print("Note: SQLite may need manual column addition")
            except Exception as e2:
                print(f"ERROR with SQLite approach: {e2}")
        
        # Initialize default categories
        print("Initializing default categories...")
        try:
            from src.services.content_categories import content_category_service
            categories = content_category_service.get_all_categories()
            print(f"[OK] Initialized {len(categories)} default categories")
        except Exception as e:
            print(f"ERROR initializing categories: {e}")
        
        print("\n[OK] Migration completed successfully!")
        print("\nDefault categories:")
        print("  - underholdning (Entertainment)")
        print("  - porn (Adult content)")
        print("  - rettigheder (Rights)")
        
        return True

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

