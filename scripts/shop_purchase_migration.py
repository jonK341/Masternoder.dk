#!/usr/bin/env python3
"""
Shop Purchase System Database Migration
Creates tables for shop purchases, user inventory, and shop items catalog.

Run with: python scripts/shop_purchase_migration.py
Use --standalone to connect directly to DB (fast, no Flask). Otherwise uses create_app (slow).
"""
import os
import sys
import json

# Add project root to path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

# Load .env if present (for DATABASE_URL)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, '.env'))
except Exception:
    pass

from sqlalchemy import text, inspect, create_engine

USE_STANDALONE = '--standalone' in sys.argv or os.getenv('SHOP_MIGRATION_STANDALONE', '').lower() in ('1', 'true', 'yes')


class ShopPurchaseMigration:
    """Database migration for shop purchase system"""
    
    def __init__(self, standalone=False):
        self.migrations_applied = []
        self.standalone = standalone
        if standalone:
            database_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or 'sqlite:///documentary_generator.db'
            if not database_url.startswith('sqlite'):
                database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1) if 'postgresql' in database_url else database_url
            self.engine = create_engine(database_url)
            self._connection = self.engine.connect()
            self._transaction = None  # commit after each op in standalone
            self._inspector = inspect(self.engine)
        else:
            from src.app import create_app
            from src.db.models import db
            self.app = create_app()
            self.app.app_context().push()
            self._db = db
            self._connection = None
            self._transaction = None
            self._inspector = inspect(db.engine)
    
    def _execute(self, statement, params=None):
        if self.standalone:
            if params:
                return self._connection.execute(text(statement), params or {})
            return self._connection.execute(text(statement))
        if params:
            return self._db.session.execute(text(statement), params or {})
        return self._db.session.execute(text(statement))
    
    def _commit(self):
        if self.standalone:
            self._connection.commit()
        else:
            self._db.session.commit()
    
    def _rollback(self):
        if self.standalone:
            try:
                self._connection.rollback()
            except Exception:
                pass
        else:
            self._db.session.rollback()
    
    def _table_names(self):
        return self._inspector.get_table_names()
    
    def _close(self):
        if self.standalone and self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
    
    def run_migration(self):
        """Run all migrations for shop purchase system"""
        print("=" * 80)
        print("SHOP PURCHASE SYSTEM DATABASE MIGRATION")
        print("=" * 80)
        print()
        
        print("1. Creating shop system tables...")
        self.create_shop_items()
        self.create_shop_purchases()
        self.create_user_inventory()
        print()
        
        print("2. Creating indexes...")
        self.create_indexes()
        print()
        
        print("3. Seeding shop items...")
        self.seed_shop_items()
        print()
        
        print("=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print()
        print(f"Applied {len(self.migrations_applied)} migrations:")
        for migration in self.migrations_applied:
            print(f"   [OK] {migration}")
        print()
        print("Migration complete!")
        print()
    
    def create_shop_items(self):
        """Create shop_items table for catalog"""
        try:
            if 'shop_items' not in self._table_names():
                print("   Creating shop_items table...")
                self._execute("""
                    CREATE TABLE shop_items (
                        id VARCHAR(100) PRIMARY KEY,
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        category VARCHAR(50) NOT NULL,
                        price_type VARCHAR(20) NOT NULL CHECK(price_type IN ('coins', 'unified_points')),
                        price_coins INTEGER DEFAULT 0,
                        price_points TEXT,
                        icon VARCHAR(10) DEFAULT '🛍️',
                        rarity VARCHAR(20) DEFAULT 'common' CHECK(rarity IN ('common', 'rare', 'epic', 'legendary')),
                        is_active BOOLEAN DEFAULT 1,
                        stock_limit INTEGER,
                        purchase_limit INTEGER,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self._commit()
                self.migrations_applied.append("Created shop_items table")
                print("   [OK] Created shop_items table")
            else:
                print("   [OK] shop_items table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            self._rollback()
    
    def create_shop_purchases(self):
        """Create shop_purchases table for purchase history"""
        try:
            if 'shop_purchases' not in self._table_names():
                print("   Creating shop_purchases table...")
                self._execute("""
                    CREATE TABLE shop_purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        item_id VARCHAR(100) NOT NULL,
                        item_name VARCHAR(200) NOT NULL,
                        quantity INTEGER DEFAULT 1,
                        price_type VARCHAR(20) NOT NULL CHECK(price_type IN ('coins', 'unified_points')),
                        price_paid_coins INTEGER DEFAULT 0,
                        price_paid_points TEXT,
                        balance_before TEXT,
                        balance_after TEXT,
                        purchase_status VARCHAR(20) DEFAULT 'completed' CHECK(purchase_status IN ('completed', 'refunded', 'cancelled')),
                        refunded_at TIMESTAMP,
                        refund_reason TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self._commit()
                self.migrations_applied.append("Created shop_purchases table")
                print("   [OK] Created shop_purchases table")
            else:
                print("   [OK] shop_purchases table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            self._rollback()
    
    def create_user_inventory(self):
        """Create user_inventory table for owned items"""
        try:
            if 'user_inventory' not in self._table_names():
                print("   Creating user_inventory table...")
                self._execute("""
                    CREATE TABLE user_inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        item_id VARCHAR(100) NOT NULL,
                        item_name VARCHAR(200) NOT NULL,
                        quantity INTEGER DEFAULT 1,
                        purchase_id INTEGER,
                        is_active BOOLEAN DEFAULT 1,
                        expires_at TIMESTAMP,
                        used_at TIMESTAMP,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, item_id)
                    )
                """)
                self._commit()
                self.migrations_applied.append("Created user_inventory table")
                print("   [OK] Created user_inventory table")
            else:
                print("   [OK] user_inventory table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            self._rollback()
    
    def create_indexes(self):
        """Create indexes for performance"""
        indexes = [
            ("idx_shop_items_category", "shop_items", "category"),
            ("idx_shop_items_active", "shop_items", "is_active"),
            ("idx_shop_items_rarity", "shop_items", "rarity"),
            ("idx_shop_purchases_user_id", "shop_purchases", "user_id"),
            ("idx_shop_purchases_item_id", "shop_purchases", "item_id"),
            ("idx_shop_purchases_created_at", "shop_purchases", "created_at"),
            ("idx_user_inventory_user_id", "user_inventory", "user_id"),
            ("idx_user_inventory_item_id", "user_inventory", "item_id"),
            ("idx_user_inventory_active", "user_inventory", "is_active"),
        ]
        
        for idx_name, table_name, columns in indexes:
            try:
                existing_indexes = [idx['name'] for idx in self._inspector.get_indexes(table_name)]
                
                if idx_name not in existing_indexes:
                    print(f"   Creating index {idx_name}...")
                    self._execute(f"CREATE INDEX {idx_name} ON {table_name}({columns})")
                    self._commit()
                    self.migrations_applied.append(f"Created index {idx_name}")
                    print(f"   [OK] Created index {idx_name}")
                else:
                    print(f"   [OK] Index {idx_name} exists")
            except Exception as e:
                print(f"   [WARN] Could not create index {idx_name}: {str(e)}")
                self._rollback()
    
    def seed_shop_items(self):
        """Seed shop_items table with initial items (from backend seed or skip if import fails)."""
        import json
        try:
            # Import from backend when run from project root (scripts/shop_purchase_migration.py)
            from backend.routes.shop_routes import _seed_shop_items
            items = _seed_shop_items()
        except Exception as e:
            print(f"   [WARN] Could not import _seed_shop_items: {e}")
            print("   [SKIP] Run migration from project root: python scripts/shop_purchase_migration.py")
            return
        try:
            existing_count = self._execute("SELECT COUNT(*) FROM shop_items").scalar()
            if existing_count > 0:
                print(f"   [OK] Shop items already seeded ({existing_count} items)")
                return
            print(f"   Seeding {len(items)} shop items...")
            inserted = 0
            for item in items:
                try:
                    price_type = 'unified_points' if isinstance(item.get('price'), dict) else 'coins'
                    price_coins = int(item.get('price')) if isinstance(item.get('price'), (int, float)) else 0
                    price_points = json.dumps(item.get('price')) if isinstance(item.get('price'), dict) else None
                    self._execute(
                        """
                            INSERT INTO shop_items 
                            (id, name, description, category, price_type, price_coins, price_points, icon, rarity)
                            VALUES (:id, :name, :description, :category, :price_type, :price_coins, :price_points, :icon, :rarity)
                        """,
                        {
                            'id': item.get('id'),
                            'name': item.get('name'),
                            'description': item.get('description') or '',
                            'category': item.get('category'),
                            'price_type': price_type,
                            'price_coins': price_coins,
                            'price_points': price_points,
                            'icon': (item.get('icon') or '🛍️')[:10],
                            'rarity': item.get('rarity') or 'common'
                        }
                    )
                    inserted += 1
                except Exception as e:
                    print(f"   [WARN] Could not insert item {item.get('id')}: {str(e)}")
                    continue
            self._commit()
            self.migrations_applied.append(f"Seeded {inserted} shop items")
            print(f"   [OK] Seeded {inserted} shop items")
        except Exception as e:
            print(f"   [ERROR] Failed to seed shop items: {str(e)}")
            self._rollback()


def main():
    """Run migration"""
    if USE_STANDALONE:
        print("Using standalone DB connection (no Flask)...")
    migration = ShopPurchaseMigration(standalone=USE_STANDALONE)
    try:
        migration.run_migration()
    finally:
        migration._close()


if __name__ == '__main__':
    main()
