"""Flexible storage manager with support for multiple backends (SFTP, S3, local, etc.)"""
import os
from typing import Optional, Dict, Any, BinaryIO
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """Upload file and return public URL if available"""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from remote storage"""
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in remote storage"""
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from remote storage"""
        pass
    
    @abstractmethod
    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get public URL for file"""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if backend is enabled and configured"""
        pass


class SFTPStorageBackend(StorageBackend):
    """SFTP storage backend"""
    
    def __init__(self, 
                 host: str = None,
                 user: str = None,
                 password: str = None,
                 base_path: str = None,
                 public_url_base: str = None,
                 port: int = 22):
        """Initialize SFTP storage backend"""
        self.host = host or os.getenv('STORAGE_SFTP_HOST', os.getenv('SFTP_HOST', ''))
        self.user = user or os.getenv('STORAGE_SFTP_USER', os.getenv('SFTP_USER', ''))
        self.password = password or os.getenv('STORAGE_SFTP_PASSWORD', os.getenv('SFTP_PASSWORD', ''))
        self.base_path = base_path or os.getenv('STORAGE_SFTP_PATH', '/var/www/videos')
        self.public_url_base = public_url_base or os.getenv('STORAGE_SFTP_PUBLIC_URL', 'https://masternoder.dk/videos')
        self.port = int(os.getenv('STORAGE_SFTP_PORT', port))
        self.enabled = self.is_enabled()
        self.ssh = None
        self.sftp = None
    
    def is_enabled(self) -> bool:
        """Check if SFTP backend is enabled and configured"""
        return bool(self.host and self.user and self.password)
    
    def _connect(self) -> bool:
        """Connect to SFTP server"""
        try:
            import paramiko
        except ImportError:
            print("Warning: paramiko not installed. SFTP storage not available.")
            return False
        
        if not self.is_enabled():
            return False
        
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                timeout=30
            )
            self.sftp = self.ssh.open_sftp()
            return True
        except Exception as e:
            print(f"SFTP connection error: {e}")
            return False
    
    def _disconnect(self):
        """Disconnect from SFTP server"""
        if self.sftp:
            try:
                self.sftp.close()
            except:
                pass
            self.sftp = None
        if self.ssh:
            try:
                self.ssh.close()
            except:
                pass
            self.ssh = None
    
    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """Upload file to SFTP server"""
        if not self.enabled or not self._connect():
            return None
        
        try:
            # Ensure remote directory exists
            remote_dir = str(Path(remote_path).parent)
            full_remote_dir = f"{self.base_path}/{remote_dir}" if remote_dir else self.base_path
            
            try:
                self.sftp.chdir(self.base_path)
                # Create subdirectories if needed
                for part in remote_dir.split('/'):
                    if part:
                        try:
                            self.sftp.mkdir(part)
                        except IOError:
                            pass  # Directory already exists
                        self.sftp.chdir(part)
            except Exception as e:
                print(f"Error creating remote directories: {e}")
                # Try to create base directory
                try:
                    parts = self.base_path.split('/')
                    current = ''
                    for part in parts:
                        if part:
                            current = f"{current}/{part}" if current else part
                            try:
                                self.sftp.mkdir(current)
                            except IOError:
                                pass
                    self.sftp.chdir(self.base_path)
                except:
                    pass
            
            # Upload file
            remote_filename = Path(remote_path).name
            remote_full_path = f"{self.base_path}/{remote_path}"
            self.sftp.put(local_path, remote_full_path)
            
            self._disconnect()
            
            # Return public URL
            return self.get_public_url(remote_path)
            
        except Exception as e:
            print(f"SFTP upload error: {e}")
            self._disconnect()
            return None
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from SFTP server"""
        if not self.enabled or not self._connect():
            return False
        
        try:
            remote_full_path = f"{self.base_path}/{remote_path}"
            self.sftp.get(remote_full_path, local_path)
            self._disconnect()
            return True
        except Exception as e:
            print(f"SFTP download error: {e}")
            self._disconnect()
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists on SFTP server"""
        if not self.enabled or not self._connect():
            return False
        
        try:
            remote_full_path = f"{self.base_path}/{remote_path}"
            self.sftp.stat(remote_full_path)
            self._disconnect()
            return True
        except:
            self._disconnect()
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from SFTP server"""
        if not self.enabled or not self._connect():
            return False
        
        try:
            remote_full_path = f"{self.base_path}/{remote_path}"
            self.sftp.remove(remote_full_path)
            self._disconnect()
            return True
        except Exception as e:
            print(f"SFTP delete error: {e}")
            self._disconnect()
            return False
    
    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get public URL for file"""
        if not self.enabled:
            return None
        return f"{self.public_url_base}/{remote_path}"


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend"""
    
    def __init__(self,
                 bucket: str = None,
                 region: str = None,
                 access_key: str = None,
                 secret_key: str = None,
                 public_url_base: str = None):
        """Initialize S3 storage backend"""
        self.bucket = bucket or os.getenv('STORAGE_S3_BUCKET', '')
        self.region = region or os.getenv('STORAGE_S3_REGION', 'us-east-1')
        self.access_key = access_key or os.getenv('STORAGE_S3_ACCESS_KEY', os.getenv('AWS_ACCESS_KEY_ID', ''))
        self.secret_key = secret_key or os.getenv('STORAGE_S3_SECRET_KEY', os.getenv('AWS_SECRET_ACCESS_KEY', ''))
        self.public_url_base = public_url_base or os.getenv('STORAGE_S3_PUBLIC_URL', '')
        self.enabled = self.is_enabled()
        self.client = None
    
    def is_enabled(self) -> bool:
        """Check if S3 backend is enabled and configured"""
        try:
            import boto3
        except ImportError:
            return False
        return bool(self.bucket and self.access_key and self.secret_key)
    
    def _get_client(self):
        """Get S3 client"""
        if self.client:
            return self.client
        
        try:
            import boto3
            self.client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
            return self.client
        except Exception as e:
            print(f"S3 client error: {e}")
            return None
    
    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """Upload file to S3"""
        if not self.enabled:
            return None
        
        client = self._get_client()
        if not client:
            return None
        
        try:
            client.upload_file(local_path, self.bucket, remote_path)
            return self.get_public_url(remote_path)
        except Exception as e:
            print(f"S3 upload error: {e}")
            return None
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from S3"""
        if not self.enabled:
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.download_file(self.bucket, remote_path, local_path)
            return True
        except Exception as e:
            print(f"S3 download error: {e}")
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in S3"""
        if not self.enabled:
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.head_object(Bucket=self.bucket, Key=remote_path)
            return True
        except:
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from S3"""
        if not self.enabled:
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.delete_object(Bucket=self.bucket, Key=remote_path)
            return True
        except Exception as e:
            print(f"S3 delete error: {e}")
            return False
    
    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get public URL for file"""
        if not self.enabled:
            return None
        
        if self.public_url_base:
            return f"{self.public_url_base}/{remote_path}"
        
        # Generate S3 URL
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{remote_path}"


class LocalStorageBackend(StorageBackend):
    """Local storage backend (for development/testing)"""
    
    def __init__(self, base_path: str = None):
        """Initialize local storage backend"""
        self.base_path = Path(base_path or os.getenv('STORAGE_LOCAL_PATH', 'storage'))
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.enabled = True
    
    def is_enabled(self) -> bool:
        """Local storage is always enabled"""
        return True
    
    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """Copy file to local storage"""
        try:
            import shutil
            remote_full_path = self.base_path / remote_path
            remote_full_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, remote_full_path)
            return str(remote_full_path)
        except Exception as e:
            print(f"Local storage upload error: {e}")
            return None
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Copy file from local storage"""
        try:
            import shutil
            remote_full_path = self.base_path / remote_path
            if not remote_full_path.exists():
                return False
            shutil.copy2(remote_full_path, local_path)
            return True
        except Exception as e:
            print(f"Local storage download error: {e}")
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in local storage"""
        remote_full_path = self.base_path / remote_path
        return remote_full_path.exists()
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from local storage"""
        try:
            remote_full_path = self.base_path / remote_path
            if remote_full_path.exists():
                remote_full_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Local storage delete error: {e}")
            return False
    
    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get local file path"""
        remote_full_path = self.base_path / remote_path
        if remote_full_path.exists():
            return str(remote_full_path)
        return None


class StorageManager:
    """Manages multiple storage backends with fallback support"""
    
    def __init__(self):
        """Initialize storage manager"""
        self.backends: list[StorageBackend] = []
        self.primary_backend: Optional[StorageBackend] = None
        
        # Initialize backends based on configuration
        storage_type = os.getenv('STORAGE_TYPE', 'auto').lower()
        
        if storage_type == 'auto' or storage_type == 'sftp':
            sftp_backend = SFTPStorageBackend()
            if sftp_backend.enabled:
                self.backends.append(sftp_backend)
                if not self.primary_backend:
                    self.primary_backend = sftp_backend
        
        if storage_type == 'auto' or storage_type == 's3':
            s3_backend = S3StorageBackend()
            if s3_backend.enabled:
                self.backends.append(s3_backend)
                if not self.primary_backend:
                    self.primary_backend = s3_backend
        
        if storage_type == 'auto' or storage_type == 'local':
            local_backend = LocalStorageBackend()
            if local_backend.enabled:
                self.backends.append(local_backend)
                if not self.primary_backend:
                    self.primary_backend = local_backend
        
        # Print configuration
        if self.primary_backend:
            backend_type = type(self.primary_backend).__name__.replace('StorageBackend', '').upper()
            print(f"[Storage] Primary storage: {backend_type}")
            if len(self.backends) > 1:
                print(f"[Storage] Fallback backends: {len(self.backends) - 1}")
        else:
            print("[Storage] Warning: No storage backends configured - files will be stored locally only")
    
    def upload_file(self, local_path: str, remote_path: str, use_primary: bool = True) -> Optional[str]:
        """Upload file using primary backend or first available"""
        backend = self.primary_backend if use_primary and self.primary_backend else None
        
        # Try primary backend first
        if backend and backend.is_enabled():
            try:
                url = backend.upload_file(local_path, remote_path)
                if url:
                    return url
            except Exception as e:
                print(f"Primary storage upload failed: {e}")
        
        # Try fallback backends
        for backend in self.backends:
            if backend != self.primary_backend and backend.is_enabled():
                try:
                    url = backend.upload_file(local_path, remote_path)
                    if url:
                        print(f"[Storage] Uploaded to fallback backend: {type(backend).__name__}")
                        return url
                except Exception as e:
                    print(f"Fallback storage upload failed: {e}")
        
        return None
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file using any available backend"""
        for backend in self.backends:
            if backend.is_enabled():
                try:
                    if backend.download_file(remote_path, local_path):
                        return True
                except Exception as e:
                    print(f"Storage download failed: {e}")
        return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in any backend"""
        for backend in self.backends:
            if backend.is_enabled():
                try:
                    if backend.file_exists(remote_path):
                        return True
                except:
                    pass
        return False
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from all backends"""
        success = False
        for backend in self.backends:
            if backend.is_enabled():
                try:
                    if backend.delete_file(remote_path):
                        success = True
                except:
                    pass
        return success
    
    def get_public_url(self, remote_path: str) -> Optional[str]:
        """Get public URL from primary backend"""
        if self.primary_backend and self.primary_backend.is_enabled():
            return self.primary_backend.get_public_url(remote_path)
        return None

