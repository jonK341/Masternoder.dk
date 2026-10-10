"""SFTP upload service for masternoder.dk integration"""
import os
from pathlib import Path
from typing import Optional
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    print("Warning: paramiko not installed. SFTP upload not available.")


class SFTPUploadService:
    """Service to upload generated videos to masternoder.dk via SFTP"""
    
    def __init__(self, 
                 host: str = None,
                 user: str = None,
                 password: str = None,
                 path: str = None,
                 port: int = 22):
        """Initialize SFTP upload service"""
        self.host = host or os.getenv('SFTP_HOST', 'masternoder.dk')
        self.user = user or os.getenv('SFTP_USER', 'root')
        self.password = password or os.getenv('SFTP_PASSWORD', '')
        self.path = path or os.getenv('SFTP_PATH', '/var/www/videos')
        self.port = int(os.getenv('SFTP_PORT', port))
        self.enabled = os.getenv('SFTP_ENABLED', 'false').lower() == 'true'
        self.ssh = None
        self.sftp = None
    
    def _connect(self) -> bool:
        """Connect to SFTP server"""
        if not PARAMIKO_AVAILABLE:
            print("paramiko not available - cannot use SFTP")
            return False
        
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                timeout=10
            )
            self.sftp = self.ssh.open_sftp()
            return True
        except Exception as e:
            print(f"SFTP connection error: {e}")
            return False
    
    def _disconnect(self):
        """Disconnect from SFTP server"""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        if self.ssh:
            self.ssh.close()
            self.ssh = None
    
    def upload_file(self, local_path: str, remote_filename: str = None) -> bool:
        """Upload a file to SFTP server"""
        if not self.enabled:
            print("SFTP upload is disabled")
            return False
        
        if not PARAMIKO_AVAILABLE:
            print("paramiko not available - cannot use SFTP")
            return False
        
        if not os.path.exists(local_path):
            print(f"Local file not found: {local_path}")
            return False
        
        try:
            if not self._connect():
                return False
            
            # Change to upload directory
            try:
                self.sftp.chdir(self.path)
            except IOError:
                # Directory doesn't exist, try to create it
                try:
                    self.sftp.mkdir(self.path)
                    self.sftp.chdir(self.path)
                except Exception as e:
                    print(f"Error creating/changing directory: {e}")
                    self._disconnect()
                    return False
            
            # Upload file
            remote_filename = remote_filename or Path(local_path).name
            self.sftp.put(local_path, remote_filename)
            
            self._disconnect()
            
            print(f"Successfully uploaded {local_path} to {self.host}:{self.port}{self.path}/{remote_filename}")
            return True
            
        except Exception as e:
            print(f"SFTP upload error: {e}")
            self._disconnect()
            return False
    
    def upload_video(self, video_path: str, doc_id: str) -> Optional[str]:
        """Upload generated video and return public URL"""
        if not self.enabled:
            return None
        
        filename = f"{doc_id}.mp4"
        success = self.upload_file(video_path, filename)
        
        if success:
            # Return public URL (adjust based on your setup)
            base_url = os.getenv('SFTP_PUBLIC_URL', f'https://masternoder.dk/videos')
            return f"{base_url}/{filename}"
        
        return None
    
    def test_connection(self) -> bool:
        """Test SFTP connection"""
        if not self.enabled:
            print("SFTP upload is disabled")
            return False
        
        if not PARAMIKO_AVAILABLE:
            print("paramiko not available - install with: pip install paramiko")
            return False
        
        try:
            if self._connect():
                print(f"✓ SFTP connection successful to {self.host}:{self.port}")
                print(f"  User: {self.user}")
                print(f"  Path: {self.path}")
                self._disconnect()
                return True
            else:
                return False
        except Exception as e:
            print(f"✗ SFTP connection failed: {e}")
            return False
    
    def create_remote_directory(self, path: str) -> bool:
        """Create directory on remote server"""
        if not self.enabled or not PARAMIKO_AVAILABLE:
            return False
        
        try:
            if not self._connect():
                return False
            
            # Try to create directory (may fail if exists, that's OK)
            try:
                self.sftp.mkdir(path)
            except IOError:
                pass  # Directory already exists
            
            self._disconnect()
            return True
        except Exception as e:
            print(f"Error creating remote directory: {e}")
            self._disconnect()
            return False


if __name__ == "__main__":
    # Test SFTP connection
    sftp_service = SFTPUploadService()
    sftp_service.test_connection()

