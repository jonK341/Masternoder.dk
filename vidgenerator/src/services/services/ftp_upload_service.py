"""FTP upload service for masternoder.dk integration"""
import os
import ftplib
from pathlib import Path
from typing import Optional

class FTPUploadService:
    """Service to upload generated videos to masternoder.dk via FTP"""
    
    def __init__(self, 
                 host: str = None,
                 user: str = None,
                 password: str = None,
                 path: str = None,
                 port: int = 21,
                 use_ssl: bool = False):
        """Initialize FTP upload service"""
        self.host = host or os.getenv('FTP_HOST', 'ftp.masternoder.dk')
        self.user = user or os.getenv('FTP_USER', '')
        self.password = password or os.getenv('FTP_PASSWORD', '')
        self.path = path or os.getenv('FTP_PATH', '/public_html/videos')
        self.port = int(os.getenv('FTP_PORT', port))
        self.use_ssl = use_ssl or os.getenv('FTP_SSL', 'false').lower() == 'true'
        self.enabled = os.getenv('FTP_ENABLED', 'false').lower() == 'true'
    
    def upload_file(self, local_path: str, remote_filename: str = None) -> bool:
        """Upload a file to FTP server"""
        if not self.enabled:
            print("FTP upload is disabled")
            return False
        
        if not os.path.exists(local_path):
            print(f"Local file not found: {local_path}")
            return False
        
        try:
            # Connect to FTP server
            if self.use_ssl:
                # FTPS (FTP over SSL)
                ftp = ftplib.FTP_TLS()
                ftp.connect(self.host, self.port)
                ftp.auth()
                ftp.prot_p()  # Set secure data connection
            else:
                ftp = ftplib.FTP()
                ftp.connect(self.host, self.port)
            
            # Login
            ftp.login(self.user, self.password)
            
            # Change to upload directory
            ftp.cwd(self.path)
            
            # Upload file
            remote_filename = remote_filename or Path(local_path).name
            with open(local_path, 'rb') as file:
                ftp.storbinary(f'STOR {remote_filename}', file)
            
            # Close connection
            ftp.quit()
            
            print(f"Successfully uploaded {local_path} to {self.host}{self.path}/{remote_filename}")
            return True
            
        except ftplib.error_perm as e:
            print(f"FTP permission error: {e}")
            return False
        except ftplib.error_temp as e:
            print(f"FTP temporary error: {e}")
            return False
        except Exception as e:
            print(f"FTP upload error: {e}")
            return False
    
    def upload_video(self, video_path: str, doc_id: str) -> Optional[str]:
        """Upload generated video and return public URL"""
        if not self.enabled:
            return None
        
        filename = f"{doc_id}.mp4"
        success = self.upload_file(video_path, filename)
        
        if success:
            # Return public URL (adjust based on your setup)
            base_url = os.getenv('FTP_PUBLIC_URL', f'https://masternoder.dk/videos')
            return f"{base_url}/{filename}"
        
        return None
    
    def test_connection(self) -> bool:
        """Test FTP connection"""
        if not self.enabled:
            print("FTP upload is disabled")
            return False
        
        try:
            if self.use_ssl:
                ftp = ftplib.FTP_TLS()
                ftp.connect(self.host, self.port)
                ftp.auth()
            else:
                ftp = ftplib.FTP()
                ftp.connect(self.host, self.port)
            
            ftp.login(self.user, self.password)
            ftp.quit()
            print(f"✓ FTP connection successful to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ FTP connection failed: {e}")
            return False


if __name__ == "__main__":
    # Test FTP connection
    ftp_service = FTPUploadService()
    ftp_service.test_connection()

