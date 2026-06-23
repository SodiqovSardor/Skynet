"""
FTP Client Tool for Skynet.
Connect to FTP servers, list directories, download/upload files.
"""
import ftplib
import os
import io
from typing import Optional, List

def ftp_client(
    host: str,
    port: int = 21,
    username: str = "anonymous",
    password: str = "anonymous@",
    action: str = "list",
    remote_path: str = "/",
    local_path: Optional[str] = None,
    timeout: int = 10
) -> str:
    """
    Connect to an FTP server and perform operations.
    
    Actions:
      - list: List directory contents
      - download: Download a file (requires remote_path and local_path)
      - upload: Upload a file (requires local_path and remote_path)
      - delete: Delete a file
      - info: Get server info/banner
    
    Args:
        host: FTP server hostname or IP
        port: FTP port (default 21)
        username: FTP username (default anonymous)
        password: FTP password (default anonymous@)
        action: Operation to perform (list, download, upload, delete, info)
        remote_path: Path on remote server
        local_path: Local file path (for download/upload)
        timeout: Connection timeout in seconds
    """
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=timeout)
        ftp.login(username, password)
        
        result_lines = []
        result_lines.append(f"Connected to {host}:{port} as {username}")
        
        if action == "info":
            result_lines.append(f"Server: {ftp.getwelcome()}")
            try:
                result_lines.append(f"System: {ftp.system()}")
            except:
                pass
            try:
                result_lines.append(f"Status: {ftp.stat()}")
            except:
                pass
            
        elif action == "list":
            try:
                items = []
                ftp.retrlines(f'LIST {remote_path}', items.append)
                result_lines.append(f"Directory listing of {remote_path}:")
                result_lines.extend(items if items else ["  (empty directory)"])
            except Exception as e:
                result_lines.append(f"Error listing {remote_path}: {str(e)}")
                
        elif action == "download":
            if not local_path:
                return "Error: local_path required for download action"
            try:
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {remote_path}', f.write)
                result_lines.append(f"Downloaded {remote_path} -> {local_path}")
                size = os.path.getsize(local_path)
                result_lines.append(f"Size: {size} bytes")
            except Exception as e:
                result_lines.append(f"Error downloading: {str(e)}")
                
        elif action == "upload":
            if not local_path or not os.path.exists(local_path):
                return f"Error: local_path '{local_path}' not found or not specified"
            try:
                with open(local_path, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_path}', f)
                result_lines.append(f"Uploaded {local_path} -> {remote_path}")
            except Exception as e:
                result_lines.append(f"Error uploading: {str(e)}")
                
        elif action == "delete":
            try:
                ftp.delete(remote_path)
                result_lines.append(f"Deleted {remote_path}")
            except Exception as e:
                result_lines.append(f"Error deleting: {str(e)}")
                
        else:
            result_lines.append(f"Unknown action: {action}")
            
        ftp.quit()
        return "\n".join(result_lines)
        
    except ftplib.all_errors as e:
        return f"FTP Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
