"""
Encrypted JSON Storage System
Prevents user editing of JSON files on their site
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

class EncryptedJSONStorage:
    """
    Encrypted JSON storage system
    Prevents users from editing JSON files
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encrypted storage"""
        self.encryption_key = encryption_key or self._generate_key()
        self.cipher = self._create_cipher(self.encryption_key)
        self.storage_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'encrypted')
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _generate_key(self) -> str:
        """Generate encryption key"""
        # Use system-specific key generation
        key_material = os.getenv('ENCRYPTION_KEY', 'default_key_change_in_production')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'fixed_salt_change_in_production',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_material.encode()))
        return key.decode()
    
    def _create_cipher(self, key: str) -> Fernet:
        """Create Fernet cipher"""
        return Fernet(key.encode())
    
    def save_encrypted_json(self, filename: str, data: Dict[str, Any], 
                           user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Save data as encrypted JSON
        
        Args:
            filename: Name of file (without extension)
            data: Data to save
            user_id: Optional user ID for user-specific files
            
        Returns:
            Save result
        """
        try:
            # Add metadata
            data_with_metadata = {
                'data': data,
                'metadata': {
                    'saved_at': datetime.utcnow().isoformat(),
                    'user_id': user_id,
                    'version': '1.0',
                    'encrypted': True
                }
            }
            
            # Convert to JSON
            json_data = json.dumps(data_with_metadata, indent=2)
            
            # Encrypt
            encrypted_data = self.cipher.encrypt(json_data.encode())
            
            # Save to file
            if user_id:
                filepath = os.path.join(self.storage_dir, f"{user_id}_{filename}.encrypted.json")
            else:
                filepath = os.path.join(self.storage_dir, f"{filename}.encrypted.json")
            
            with open(filepath, 'wb') as f:
                f.write(encrypted_data)
            
            # Calculate hash for verification
            file_hash = hashlib.sha256(encrypted_data).hexdigest()
            
            return {
                'success': True,
                'filename': os.path.basename(filepath),
                'filepath': filepath,
                'hash': file_hash,
                'size': len(encrypted_data)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_encrypted_json(self, filename: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and decrypt JSON file
        
        Args:
            filename: Name of file (without extension)
            user_id: Optional user ID for user-specific files
            
        Returns:
            Decrypted data
        """
        try:
            if user_id:
                filepath = os.path.join(self.storage_dir, f"{user_id}_{filename}.encrypted.json")
            else:
                filepath = os.path.join(self.storage_dir, f"{filename}.encrypted.json")
            
            if not os.path.exists(filepath):
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            # Read encrypted data
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(encrypted_data)
            json_data = json.loads(decrypted_data.decode())
            
            return {
                'success': True,
                'data': json_data.get('data', {}),
                'metadata': json_data.get('metadata', {})
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_integrity(self, filename: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Verify file integrity"""
        try:
            if user_id:
                filepath = os.path.join(self.storage_dir, f"{user_id}_{filename}.encrypted.json")
            else:
                filepath = os.path.join(self.storage_dir, f"{filename}.encrypted.json")
            
            if not os.path.exists(filepath):
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            # Read file
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
            
            # Try to decrypt (will fail if tampered)
            try:
                decrypted_data = self.cipher.decrypt(encrypted_data)
                json_data = json.loads(decrypted_data.decode())
                
                # Calculate hash
                file_hash = hashlib.sha256(encrypted_data).hexdigest()
                
                return {
                    'success': True,
                    'integrity': 'valid',
                    'hash': file_hash,
                    'metadata': json_data.get('metadata', {})
                }
            except Exception:
                return {
                    'success': False,
                    'integrity': 'invalid',
                    'error': 'File has been tampered with or corrupted'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
encrypted_json_storage = EncryptedJSONStorage()

