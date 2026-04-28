#!/usr/bin/env python3
"""
Database index optimization script
Adds composite indexes for common query patterns
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.app import create_app
from src.db.models import db
from sqlalchemy import text, inspect

def optimize_indexes():
    """Add composite indexes for common query patterns"""
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("Database Index Optimization")
        print("=" * 70)
        print()
        
        inspector = inspect(db.engine)
        existing_indexes = {}
        
        # Get all existing indexes
        for table_name in inspector.get_table_names():
            indexes = inspector.get_indexes(table_name)
            existing_indexes[table_name] = [idx['name'] for idx in indexes]
        
        try:
            # Composite index for status + category_name (very common query pattern)
            index_name = 'ix_documentaries_status_category'
            if index_name not in existing_indexes.get('documentaries', []):
                print(f"Creating composite index: {index_name}")
                with db.engine.begin() as conn:
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON documentaries(status, category_name)
                    """))
                print(f"  ✅ Created {index_name}")
            else:
                print(f"  ✓ Index {index_name} already exists")
            
            # Composite index for status + created_at (for sorting completed videos)
            index_name = 'ix_documentaries_status_created'
            if index_name not in existing_indexes.get('documentaries', []):
                print(f"Creating composite index: {index_name}")
                with db.engine.begin() as conn:
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON documentaries(status, created_at DESC)
                    """))
                print(f"  ✅ Created {index_name}")
            else:
                print(f"  ✓ Index {index_name} already exists")
            
            # Index for quality_score on MovieClip (used in stats queries)
            index_name = 'ix_movie_clips_quality_score'
            if 'movie_clips' in existing_indexes and index_name not in existing_indexes['movie_clips']:
                print(f"Creating index: {index_name}")
                with db.engine.begin() as conn:
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON movie_clips(quality_score DESC)
                    """))
                print(f"  ✅ Created {index_name}")
            else:
                print(f"  ✓ Index {index_name} already exists or table doesn't exist yet")
            
            # Composite index for documentary_id + quality_score (for clip queries)
            index_name = 'ix_movie_clips_doc_id_quality'
            if 'movie_clips' in existing_indexes and index_name not in existing_indexes['movie_clips']:
                print(f"Creating composite index: {index_name}")
                with db.engine.begin() as conn:
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON movie_clips(documentary_id, quality_score DESC)
                    """))
                print(f"  ✅ Created {index_name}")
            else:
                print(f"  ✓ Index {index_name} already exists or table doesn't exist yet")
            
            print()
            print("✅ Index optimization complete!")
            print()
            print("New indexes added for:")
            print("  - Status + Category queries (documentaries)")
            print("  - Status + Created date sorting (documentaries)")
            print("  - Quality score queries (movie_clips)")
            print("  - Documentary + Quality queries (movie_clips)")
            
        except Exception as e:
            print(f"❌ Error optimizing indexes: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    success = optimize_indexes()
    sys.exit(0 if success else 1)

