"""
User Identification Service
Creates proper user IDs based on IP, fingerprint, email, and other identifiers
"""
import os
import json
import uuid
import hashlib
from typing import Dict, Optional
from datetime import datetime
from flask import request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class UserIdentification:
    """Service for identifying and creating users based on various identifiers"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.identifiers_dir = os.path.join(self.base_dir, 'logs', 'user_identifiers')
        os.makedirs(self.identifiers_dir, exist_ok=True)
    
    def identify_or_create_user(self, request_obj=None) -> Dict:
        """
        Identify user from request or create new one
        Priority: email > IP+UA fingerprint > localStorage user_id > new user
        """
        if request_obj is None:
            from flask import request as flask_request
            request_obj = flask_request
        
        # Extract identifiers
        identifiers = self._extract_identifiers(request_obj)
        
        # Try to find existing user by identifiers
        existing_user_id = self._find_existing_user(identifiers)
        
        if existing_user_id:
            return {
                'success': True,
                'user_id': existing_user_id,
                'new_user': False,
                'identifiers': identifiers
            }
        
        # Create new user ID
        new_user_id = self._generate_user_id(identifiers)
        
        # Save identifier mapping
        self._save_identifier_mapping(new_user_id, identifiers)
        
        return {
            'success': True,
            'user_id': new_user_id,
            'new_user': True,
            'identifiers': identifiers
        }
    
    def _extract_identifiers(self, request_obj) -> Dict:
        """Extract all possible identifiers from request"""
        identifiers = {
            'ip_address': self._get_client_ip(request_obj),
            'user_agent': request_obj.headers.get('User-Agent', ''),
            'accept_language': request_obj.headers.get('Accept-Language', ''),
            'referer': request_obj.headers.get('Referer', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        # Try to get from request data
        try:
            if request_obj.is_json:
                data = request_obj.get_json() or {}
                identifiers.update({
                    'email': data.get('email'),
                    'device_fingerprint': data.get('device_fingerprint'),
                    'browser_fingerprint': data.get('browser_fingerprint'),
                    'localstorage_user_id': data.get('localstorage_user_id'),
                    'screen_resolution': f"{data.get('screen_width')}x{data.get('screen_height')}",
                    'timezone': data.get('timezone')
                })
        except:
            pass
        
        # Create composite fingerprint
        fingerprint_parts = [
            identifiers.get('ip_address', ''),
            identifiers.get('user_agent', ''),
            identifiers.get('accept_language', ''),
            identifiers.get('screen_resolution', ''),
            identifiers.get('timezone', '')
        ]
        identifiers['composite_fingerprint'] = hashlib.md5(
            '|'.join(filter(None, fingerprint_parts)).encode()
        ).hexdigest()[:16]
        
        return identifiers
    
    def _get_client_ip(self, request_obj) -> str:
        """Get client IP address"""
        # Check for forwarded IP (proxy/load balancer)
        forwarded = request_obj.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request_obj.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request_obj.remote_addr or 'unknown'
    
    def _find_existing_user(self, identifiers: Dict) -> Optional[str]:
        """Find existing user by identifiers"""
        # Check by email first
        if identifiers.get('email'):
            user_id = self._find_by_email(identifiers['email'])
            if user_id:
                return user_id
        
        # Check by composite fingerprint
        if identifiers.get('composite_fingerprint'):
            user_id = self._find_by_fingerprint(identifiers['composite_fingerprint'])
            if user_id:
                return user_id
        
        # Check by localStorage user_id
        if identifiers.get('localstorage_user_id'):
            user_id = identifiers['localstorage_user_id']
            if self._user_exists(user_id):
                return user_id
        
        # Check by IP + User-Agent hash
        ip_ua_hash = hashlib.md5(
            f"{identifiers.get('ip_address')}|{identifiers.get('user_agent')}".encode()
        ).hexdigest()[:16]
        user_id = self._find_by_fingerprint(ip_ua_hash)
        if user_id:
            return user_id
        
        return None
    
    def _find_by_email(self, email: str) -> Optional[str]:
        """Find user by email"""
        try:
            mapping_file = os.path.join(self.identifiers_dir, 'email_mappings.json')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mappings = json.load(f)
                    return mappings.get(email.lower())
        except:
            pass
        return None
    
    def _find_by_fingerprint(self, fingerprint: str) -> Optional[str]:
        """Find user by fingerprint"""
        try:
            mapping_file = os.path.join(self.identifiers_dir, 'fingerprint_mappings.json')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mappings = json.load(f)
                    return mappings.get(fingerprint)
        except:
            pass
        return None
    
    def _user_exists(self, user_id: str) -> bool:
        """Check if user exists"""
        # Use current app context — avoids creating a new Flask app instance per request
        try:
            from src.db.models import db
            from sqlalchemy import text
            from flask import current_app
            with current_app.app_context():
                result = db.session.execute(
                    text("SELECT 1 FROM user_profiles WHERE user_id = :user_id LIMIT 1"),
                    {'user_id': user_id}
                ).fetchone()
                if result:
                    return True
        except Exception:
            pass
        
        # Check file
        profile_file = os.path.join(self.base_dir, 'logs', 'user_profiles', f"{user_id}.json")
        return os.path.exists(profile_file)

    def get_identifiers_for_user(self, user_id: str) -> Optional[Dict]:
        """
        Return stored identifiers for a user (from logs/user_identifiers/{user_id}.json).
        Used by profile/account-control to show all user ID data. Does not create a user.
        """
        if not user_id or not str(user_id).strip():
            return None
        identifier_file = os.path.join(self.identifiers_dir, f"{user_id}.json")
        if not os.path.isfile(identifier_file):
            return None
        try:
            with open(identifier_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("identifiers") or data
        except Exception:
            return None

    def _generate_user_id(self, identifiers: Dict) -> str:
        """Generate new user ID"""
        # Use email if available
        if identifiers.get('email'):
            email_hash = hashlib.md5(identifiers['email'].lower().encode()).hexdigest()[:12]
            return f"user_{email_hash}"
        
        # Use composite fingerprint
        if identifiers.get('composite_fingerprint'):
            return f"user_{identifiers['composite_fingerprint']}"
        
        # Use IP + timestamp
        ip_hash = hashlib.md5(identifiers.get('ip_address', '').encode()).hexdigest()[:8]
        timestamp = str(int(datetime.now().timestamp()))[-6:]
        return f"user_{ip_hash}_{timestamp}"
    
    def _save_identifier_mapping(self, user_id: str, identifiers: Dict):
        """Save identifier mappings for future lookups"""
        try:
            # Email mapping
            if identifiers.get('email'):
                email_file = os.path.join(self.identifiers_dir, 'email_mappings.json')
                mappings = {}
                if os.path.exists(email_file):
                    try:
                        with open(email_file, 'r', encoding='utf-8') as f:
                            raw = f.read()
                            if raw.strip():
                                mappings = json.loads(raw)
                    except (json.JSONDecodeError, ValueError):
                        mappings = {}
                mappings[identifiers['email'].lower()] = user_id
                with open(email_file, 'w') as f:
                    json.dump(mappings, f, indent=2)
            
            # Fingerprint mapping
            if identifiers.get('composite_fingerprint'):
                fp_file = os.path.join(self.identifiers_dir, 'fingerprint_mappings.json')
                mappings = {}
                if os.path.exists(fp_file):
                    try:
                        with open(fp_file, 'r', encoding='utf-8') as f:
                            raw = f.read()
                            if raw.strip():
                                mappings = json.loads(raw)
                    except (json.JSONDecodeError, ValueError):
                        mappings = {}
                mappings[identifiers['composite_fingerprint']] = user_id
                with open(fp_file, 'w') as f:
                    json.dump(mappings, f, indent=2)
            
            # Save full identifier record
            identifier_file = os.path.join(self.identifiers_dir, f"{user_id}.json")
            with open(identifier_file, 'w') as f:
                json.dump({
                    'user_id': user_id,
                    'identifiers': identifiers,
                    'created_at': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving identifier mapping: {e}")

# Global instance
user_identification = UserIdentification()
