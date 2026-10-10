"""
IP/MAC Address User Manager
Automatically creates new users for each new IP or MAC address
Tracks IP and MAC associations with users
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
import hashlib
import uuid

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.enhanced_user_profile_json import enhanced_user_profile_json
    unified_points_db = UnifiedPointsDatabase()
except ImportError:
    unified_points_db = None


class IPMACUserManager:
    """
    Manages user creation and tracking based on IP and MAC addresses
    Creates new users automatically for new IPs/MACs
    """
    
    def __init__(self, data_dir: str = 'data/ip_mac_users'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Storage files
        self.ip_to_user_file = os.path.join(data_dir, 'ip_to_user.json')
        self.mac_to_user_file = os.path.join(data_dir, 'mac_to_user.json')
        self.user_details_file = os.path.join(data_dir, 'user_details.json')
        
        # In-memory cache
        self.ip_to_user = self._load_json(self.ip_to_user_file, {})
        self.mac_to_user = self._load_json(self.mac_to_user_file, {})
        self.user_details = self._load_json(self.user_details_file, {})
    
    def _load_json(self, file_path: str, default: Any = None) -> Any:
        """Load JSON file"""
        if default is None:
            default = {}
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[IPMACUserManager] Error loading {file_path}: {e}", flush=True)
        
        return default
    
    def _save_json(self, file_path: str, data: Any) -> bool:
        """Save JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[IPMACUserManager] Error saving {file_path}: {e}", flush=True)
            return False
    
    def _generate_user_id(self, ip_address: str, mac_address: Optional[str] = None) -> str:
        """Generate unique user ID from IP and MAC"""
        # Create hash from IP and MAC
        identifier = f"{ip_address}_{mac_address or 'no_mac'}"
        hash_value = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        
        # Generate user ID
        user_id = f"user_{hash_value}"
        return user_id
    
    def get_or_create_user(self, ip_address: str, mac_address: Optional[str] = None,
                          user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Get existing user or create new user for IP/MAC
        
        Args:
            ip_address: Client IP address
            mac_address: Client MAC address (optional, may not be available)
            user_agent: User agent string
            
        Returns:
            User information with user_id
        """
        # Normalize IP address (handle proxies)
        ip_address = self._normalize_ip(ip_address)
        
        # Check if IP already has a user
        if ip_address in self.ip_to_user:
            user_id = self.ip_to_user[ip_address]
            if user_id in self.user_details:
                # Update last seen
                self.user_details[user_id]['last_seen'] = datetime.utcnow().isoformat()
                self.user_details[user_id]['last_ip'] = ip_address
                if mac_address:
                    self.user_details[user_id]['last_mac'] = mac_address
                self._save_user_details()
                return {
                    'user_id': user_id,
                    'is_new': False,
                    'details': self.user_details[user_id]
                }
        
        # Check if MAC already has a user (if MAC provided)
        if mac_address and mac_address in self.mac_to_user:
            user_id = self.mac_to_user[mac_address]
            if user_id in self.user_details:
                # Update IP mapping
                self.ip_to_user[ip_address] = user_id
                self.user_details[user_id]['last_seen'] = datetime.utcnow().isoformat()
                self.user_details[user_id]['last_ip'] = ip_address
                self.user_details[user_id]['ips'].append(ip_address)
                self._save_all()
                return {
                    'user_id': user_id,
                    'is_new': False,
                    'details': self.user_details[user_id]
                }
        
        # Create new user
        user_id = self._generate_user_id(ip_address, mac_address)
        
        # Ensure unique user_id
        counter = 1
        original_user_id = user_id
        while user_id in self.user_details:
            user_id = f"{original_user_id}_{counter}"
            counter += 1
        
        # Create user details
        user_details = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_seen': datetime.utcnow().isoformat(),
            'first_ip': ip_address,
            'last_ip': ip_address,
            'ips': [ip_address],
            'mac_address': mac_address,
            'user_agent': user_agent,
            'login_count': 1,
            'is_active': True
        }
        
        # Store mappings
        self.ip_to_user[ip_address] = user_id
        if mac_address:
            self.mac_to_user[mac_address] = user_id
        
        self.user_details[user_id] = user_details
        
        # Save all data
        self._save_all()
        
        # Initialize user profile
        self._initialize_user_profile(user_id, ip_address, mac_address)
        
        print(f"[IPMACUserManager] Created new user: {user_id} for IP: {ip_address}, MAC: {mac_address or 'N/A'}", flush=True)
        
        return {
            'user_id': user_id,
            'is_new': True,
            'details': user_details
        }
    
    def _normalize_ip(self, ip_address: str) -> str:
        """Normalize IP address (handle proxies, IPv6, etc.)"""
        if not ip_address:
            return 'unknown'
        
        # Handle comma-separated IPs (from proxies)
        if ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        # Remove port if present
        if ':' in ip_address and not ip_address.startswith('['):  # IPv6 check
            parts = ip_address.split(':')
            if len(parts) == 2 and parts[1].isdigit():
                ip_address = parts[0]  # Remove port
        
        return ip_address
    
    def _save_all(self):
        """Save all data to files"""
        self._save_json(self.ip_to_user_file, self.ip_to_user)
        self._save_json(self.mac_to_user_file, self.mac_to_user)
        self._save_json(self.user_details_file, self.user_details)
    
    def _save_user_details(self):
        """Save user details"""
        self._save_json(self.user_details_file, self.user_details)
    
    def _initialize_user_profile(self, user_id: str, ip_address: str, mac_address: Optional[str]):
        """Initialize user profile in various systems"""
        try:
            # Initialize in enhanced user profile system
            if enhanced_user_profile_json:
                profile = enhanced_user_profile_json.get_profile(user_id)
                profile['ip_address'] = ip_address
                if mac_address:
                    profile['mac_address'] = mac_address
                profile['created_at'] = datetime.utcnow().isoformat()
                enhanced_user_profile_json.save_profile(user_id, profile)
            
            # Initialize in unified points database
            if unified_points_db:
                try:
                    points_data = {
                        'user_id': user_id,
                        'ip_address': ip_address,
                        'mac_address': mac_address,
                        'created_at': datetime.utcnow().isoformat(),
                        'first_login': datetime.utcnow().isoformat()
                    }
                    unified_points_db.save_user_points(user_id, points_data)
                except Exception as e:
                    print(f"[IPMACUserManager] Error initializing unified points: {e}", flush=True)
        except Exception as e:
            print(f"[IPMACUserManager] Error initializing user profile: {e}", flush=True)
    
    def get_user_by_ip(self, ip_address: str) -> Optional[str]:
        """Get user ID by IP address"""
        ip_address = self._normalize_ip(ip_address)
        return self.ip_to_user.get(ip_address)
    
    def get_user_by_mac(self, mac_address: str) -> Optional[str]:
        """Get user ID by MAC address"""
        return self.mac_to_user.get(mac_address)
    
    def get_user_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details"""
        return self.user_details.get(user_id)
    
    def update_user_activity(self, user_id: str, ip_address: Optional[str] = None,
                           mac_address: Optional[str] = None):
        """Update user activity timestamp"""
        if user_id in self.user_details:
            self.user_details[user_id]['last_seen'] = datetime.utcnow().isoformat()
            if ip_address:
                ip_address = self._normalize_ip(ip_address)
                self.user_details[user_id]['last_ip'] = ip_address
                if ip_address not in self.user_details[user_id]['ips']:
                    self.user_details[user_id]['ips'].append(ip_address)
                # Update IP mapping
                self.ip_to_user[ip_address] = user_id
            if mac_address:
                self.user_details[user_id]['mac_address'] = mac_address
                self.mac_to_user[mac_address] = user_id
            self.user_details[user_id]['login_count'] = self.user_details[user_id].get('login_count', 0) + 1
            self._save_all()
    
    def get_all_users(self) -> Dict[str, Dict[str, Any]]:
        """Get all users"""
        return self.user_details.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about users"""
        total_users = len(self.user_details)
        active_users = sum(1 for u in self.user_details.values() if u.get('is_active', True))
        total_ips = len(self.ip_to_user)
        total_macs = len(self.mac_to_user)
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_ips': total_ips,
            'total_macs': total_macs,
            'users_with_mac': sum(1 for u in self.user_details.values() if u.get('mac_address'))
        }


# Global instance
ip_mac_user_manager = IPMACUserManager()
