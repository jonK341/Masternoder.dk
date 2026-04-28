"""
Browser Profile Tracker Service
Tracks browser profiles, fingerprints, and debugging sessions
"""
import os
import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import text
from src.db.models import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BrowserProfileTracker:
    """Browser profile tracking system"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure browser_profiles table exists"""
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'browser_profiles' not in inspector.get_table_names():
                db.session.execute(text("""
                    CREATE TABLE browser_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile_id VARCHAR(200) UNIQUE NOT NULL,
                        fingerprint_hash VARCHAR(64) NOT NULL,
                        user_agent TEXT,
                        browser_name VARCHAR(100),
                        browser_version VARCHAR(50),
                        os_name VARCHAR(100),
                        os_version VARCHAR(50),
                        device_type VARCHAR(50),
                        screen_resolution VARCHAR(50),
                        timezone VARCHAR(50),
                        language VARCHAR(50),
                        plugins TEXT,
                        canvas_fingerprint TEXT,
                        webgl_fingerprint TEXT,
                        audio_fingerprint TEXT,
                        ip_address VARCHAR(45),
                        country VARCHAR(100),
                        city VARCHAR(100),
                        session_count INTEGER DEFAULT 0,
                        total_debug_actions INTEGER DEFAULT 0,
                        last_seen TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.execute(text("""
                    CREATE INDEX idx_browser_profiles_profile_id ON browser_profiles(profile_id)
                """))
                db.session.execute(text("""
                    CREATE INDEX idx_browser_profiles_fingerprint ON browser_profiles(fingerprint_hash)
                """))
                db.session.execute(text("""
                    CREATE INDEX idx_browser_profiles_last_seen ON browser_profiles(last_seen)
                """))
                db.session.commit()
        except Exception as e:
            print(f"Error ensuring browser_profiles table exists: {e}")
            db.session.rollback()
    
    def create_fingerprint(self, browser_data: Dict) -> str:
        """Create a unique fingerprint from browser data"""
        fingerprint_string = json.dumps({
            'user_agent': browser_data.get('user_agent', ''),
            'screen': browser_data.get('screen', {}),
            'timezone': browser_data.get('timezone', ''),
            'language': browser_data.get('language', ''),
            'plugins': browser_data.get('plugins', []),
            'canvas': browser_data.get('canvas_fingerprint', ''),
            'webgl': browser_data.get('webgl_fingerprint', ''),
            'audio': browser_data.get('audio_fingerprint', '')
        }, sort_keys=True)
        
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    def get_or_create_profile(self, browser_data: Dict, ip_address: Optional[str] = None) -> Dict:
        """Get or create a browser profile"""
        fingerprint_hash = self.create_fingerprint(browser_data)
        
        # Try to find existing profile
        try:
            result = db.session.execute(
                text("SELECT * FROM browser_profiles WHERE fingerprint_hash = :fingerprint"),
                {"fingerprint": fingerprint_hash}
            ).fetchone()
            
            if result:
                # Update last seen
                profile_id = result[1]
                db.session.execute(
                    text("""
                        UPDATE browser_profiles
                        SET last_seen = CURRENT_TIMESTAMP,
                            session_count = session_count + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE profile_id = :profile_id
                    """),
                    {"profile_id": profile_id}
                )
                db.session.commit()
                
                return self._row_to_dict(result)
        except Exception as e:
            print(f"Error finding profile: {e}")
            db.session.rollback()
        
        # Create new profile
        profile_id = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        try:
            db.session.execute(
                text("""
                    INSERT INTO browser_profiles
                    (profile_id, fingerprint_hash, user_agent, browser_name, browser_version,
                     os_name, os_version, device_type, screen_resolution, timezone, language,
                     plugins, canvas_fingerprint, webgl_fingerprint, audio_fingerprint,
                     ip_address, country, city, session_count, last_seen)
                    VALUES (:profile_id, :fingerprint_hash, :user_agent, :browser_name, :browser_version,
                            :os_name, :os_version, :device_type, :screen_resolution, :timezone, :language,
                            :plugins, :canvas_fingerprint, :webgl_fingerprint, :audio_fingerprint,
                            :ip_address, :country, :city, 1, CURRENT_TIMESTAMP)
                """),
                {
                    "profile_id": profile_id,
                    "fingerprint_hash": fingerprint_hash,
                    "user_agent": browser_data.get('user_agent', ''),
                    "browser_name": browser_data.get('browser_name', ''),
                    "browser_version": browser_data.get('browser_version', ''),
                    "os_name": browser_data.get('os_name', ''),
                    "os_version": browser_data.get('os_version', ''),
                    "device_type": browser_data.get('device_type', ''),
                    "screen_resolution": f"{browser_data.get('screen', {}).get('width', 0)}x{browser_data.get('screen', {}).get('height', 0)}",
                    "timezone": browser_data.get('timezone', ''),
                    "language": browser_data.get('language', ''),
                    "plugins": json.dumps(browser_data.get('plugins', [])),
                    "canvas_fingerprint": browser_data.get('canvas_fingerprint', ''),
                    "webgl_fingerprint": browser_data.get('webgl_fingerprint', ''),
                    "audio_fingerprint": browser_data.get('audio_fingerprint', ''),
                    "ip_address": ip_address or '',
                    "country": browser_data.get('country', ''),
                    "city": browser_data.get('city', '')
                }
            )
            db.session.commit()
            
            # Get the created profile
            result = db.session.execute(
                text("SELECT * FROM browser_profiles WHERE profile_id = :profile_id"),
                {"profile_id": profile_id}
            ).fetchone()
            
            return self._row_to_dict(result)
        except Exception as e:
            print(f"Error creating profile: {e}")
            db.session.rollback()
            return {}
    
    def _row_to_dict(self, row) -> Dict:
        """Convert database row to dictionary"""
        if not row:
            return {}
        
        return {
            'id': row[0],
            'profile_id': row[1],
            'fingerprint_hash': row[2],
            'user_agent': row[3],
            'browser_name': row[4],
            'browser_version': row[5],
            'os_name': row[6],
            'os_version': row[7],
            'device_type': row[8],
            'screen_resolution': row[9],
            'timezone': row[10],
            'language': row[11],
            'plugins': json.loads(row[12]) if row[12] else [],
            'canvas_fingerprint': row[13],
            'webgl_fingerprint': row[14],
            'audio_fingerprint': row[15],
            'ip_address': row[16],
            'country': row[17],
            'city': row[18],
            'session_count': row[19],
            'total_debug_actions': row[20],
            'last_seen': row[21],
            'created_at': row[22],
            'updated_at': row[23]
        }
    
    def update_debug_action(self, profile_id: str):
        """Update debug action count for a profile"""
        try:
            db.session.execute(
                text("""
                    UPDATE browser_profiles
                    SET total_debug_actions = total_debug_actions + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE profile_id = :profile_id
                """),
                {"profile_id": profile_id}
            )
            db.session.commit()
        except Exception as e:
            print(f"Error updating debug action: {e}")
            db.session.rollback()
    
    def get_profile(self, profile_id: str) -> Optional[Dict]:
        """Get a browser profile by ID"""
        try:
            result = db.session.execute(
                text("SELECT * FROM browser_profiles WHERE profile_id = :profile_id"),
                {"profile_id": profile_id}
            ).fetchone()
            
            if result:
                return self._row_to_dict(result)
        except Exception as e:
            print(f"Error getting profile: {e}")
        
        return None
    
    def get_all_profiles(self, limit: int = 100) -> List[Dict]:
        """Get all browser profiles"""
        try:
            results = db.session.execute(
                text("SELECT * FROM browser_profiles ORDER BY last_seen DESC LIMIT :limit"),
                {"limit": limit}
            ).fetchall()
            
            return [self._row_to_dict(row) for row in results]
        except Exception as e:
            print(f"Error getting profiles: {e}")
            return []
    
    def get_profile_stats(self) -> Dict:
        """Get statistics about browser profiles"""
        try:
            total = db.session.execute(
                text("SELECT COUNT(*) FROM browser_profiles")
            ).scalar()
            
            active = db.session.execute(
                text("""
                    SELECT COUNT(*) FROM browser_profiles
                    WHERE last_seen > datetime('now', '-7 days')
                """)
            ).scalar()
            
            total_actions = db.session.execute(
                text("SELECT SUM(total_debug_actions) FROM browser_profiles")
            ).scalar() or 0
            
            return {
                'total_profiles': total,
                'active_profiles': active,
                'total_debug_actions': total_actions,
                'average_actions_per_profile': total_actions / max(total, 1)
            }
        except Exception as e:
            print(f"Error getting profile stats: {e}")
            return {}


# Global instance
browser_profile_tracker = BrowserProfileTracker()
