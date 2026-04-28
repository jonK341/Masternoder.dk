"""
Database Models
SQLAlchemy models for users, items, inventory, points, and game state.
All tables use IF NOT EXISTS so they're safe to re-run.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index

db = SQLAlchemy()


# ==================== USER ACCOUNTS ====================

class UserAccount(db.Model):
    """Core user account — login credentials and identity."""
    __tablename__ = "user_accounts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    username = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(256), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    auth_provider = db.Column(db.String(32), default="local")
    auth_provider_id = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_premium = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(32), default="player")
    last_login = db.Column(db.DateTime, nullable=True)
    last_ip = db.Column(db.String(45), nullable=True)
    device_fingerprint = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    profile = db.relationship("UserProfile", backref="account", uselist=False, lazy="joined")
    points = db.relationship("UserPoints", backref="account", lazy="dynamic")
    inventory = db.relationship("UserInventory", backref="account", lazy="dynamic")
    purchases = db.relationship("ShopPurchase", backref="account", lazy="dynamic")


class UserProfile(db.Model):
    """Extended user profile — display info, preferences, onboarding."""
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey("user_accounts.user_id"), unique=True, nullable=False, index=True)
    username = db.Column(db.String(128), nullable=True)
    display_name = db.Column(db.String(128), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    preferences = db.Column(db.Text, default="{}")
    scraped_info = db.Column(db.Text, default="{}")
    agent_skillset_id = db.Column(db.String(64), nullable=True)
    assigned_agent_ids = db.Column(db.Text, default="[]")
    obtained_agents = db.Column(db.Text, default="[]")
    onboarding_complete = db.Column(db.Boolean, default=False)
    onboarding_data = db.Column(db.Text, default="{}")
    feature_flags = db.Column(db.Text, default="{}")
    lifecycle_stage = db.Column(db.String(32), default="new")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


# ==================== POINTS & LEVELS ====================

class PlayerLevel(db.Model):
    """Player level and XP tracking."""
    __tablename__ = "player_levels"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    current_level = db.Column(db.Integer, default=1)
    total_xp = db.Column(db.Integer, default=0)
    current_level_xp = db.Column(db.Integer, default=0)
    xp_to_next_level = db.Column(db.Integer, default=100)
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class UserPoints(db.Model):
    """Per-user per-type point ledger."""
    __tablename__ = "user_points"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey("user_accounts.user_id"), nullable=False, index=True)
    point_type = db.Column(db.String(64), nullable=False, index=True)
    amount = db.Column(db.Float, default=0)
    source = db.Column(db.String(128), nullable=True)
    metadata_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        Index("ix_user_points_user_type", "user_id", "point_type"),
    )


class XpHistory(db.Model):
    """XP transaction history."""
    __tablename__ = "xp_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), nullable=False, index=True)
    xp_amount = db.Column(db.Integer, default=0)
    source = db.Column(db.String(128), nullable=True)
    action_type = db.Column(db.String(64), nullable=True)
    level_before = db.Column(db.Integer, nullable=True)
    level_after = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class SystemPointSnapshot(db.Model):
    """Point snapshots for analytics."""
    __tablename__ = "system_point_snapshots"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), nullable=False, index=True)
    point_type = db.Column(db.String(64), nullable=False)
    total = db.Column(db.Float, default=0)
    snapshot_data = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        Index("ix_snapshot_user_type", "user_id", "point_type"),
    )


# ==================== SHOP & ITEMS ====================

class ShopItem(db.Model):
    """Shop item catalog."""
    __tablename__ = "shop_items"

    id = db.Column(db.String(128), primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=False, index=True)
    price_type = db.Column(db.String(32), default="coins")
    price_coins = db.Column(db.Integer, default=0)
    price_points = db.Column(db.Text, nullable=True)
    price_usd = db.Column(db.Float, nullable=True)
    icon = db.Column(db.String(16), default="🛍️")
    rarity = db.Column(db.String(32), default="common")
    is_active = db.Column(db.Boolean, default=True)
    max_quantity = db.Column(db.Integer, default=0)
    sort_order = db.Column(db.Integer, default=0)
    metadata_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class UserInventory(db.Model):
    """Items a user owns."""
    __tablename__ = "user_inventory"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey("user_accounts.user_id"), nullable=False, index=True)
    item_id = db.Column(db.String(128), nullable=False, index=True)
    item_name = db.Column(db.String(256), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    is_equipped = db.Column(db.Boolean, default=False)
    purchase_id = db.Column(db.Integer, nullable=True)
    source = db.Column(db.String(64), default="purchase")
    metadata_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        Index("ix_inventory_user_item", "user_id", "item_id"),
    )


class ShopPurchase(db.Model):
    """Purchase transaction log."""
    __tablename__ = "shop_purchases"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey("user_accounts.user_id"), nullable=False, index=True)
    item_id = db.Column(db.String(128), nullable=False)
    item_name = db.Column(db.String(256), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    price_type = db.Column(db.String(32), default="coins")
    price_paid_coins = db.Column(db.Integer, default=0)
    price_paid_points = db.Column(db.Text, nullable=True)
    price_paid_usd = db.Column(db.Float, nullable=True)
    balance_before = db.Column(db.Text, nullable=True)
    balance_after = db.Column(db.Text, nullable=True)
    purchase_status = db.Column(db.String(32), default="completed")
    payment_method = db.Column(db.String(32), nullable=True)
    payment_ref = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


# ==================== BATTLE ====================

class BattleMatch(db.Model):
    """Battle match history."""
    __tablename__ = "battle_matches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    battle_id = db.Column(db.String(32), unique=True, nullable=False)
    user_id = db.Column(db.String(64), nullable=False, index=True)
    opponent_type = db.Column(db.String(32), default="ai")
    opponent_id = db.Column(db.String(64), nullable=True)
    difficulty = db.Column(db.String(32), default="balanced")
    result = db.Column(db.String(16), nullable=True)
    points_delta = db.Column(db.Integer, default=0)
    match_data = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


# ==================== USER STORAGE (generic key-value per user) ====================

class UserStorage(db.Model):
    """Generic per-user key-value store for arbitrary data."""
    __tablename__ = "user_storage"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), nullable=False, index=True)
    storage_key = db.Column(db.String(128), nullable=False)
    storage_value = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        Index("ix_user_storage_key", "user_id", "storage_key", unique=True),
    )
