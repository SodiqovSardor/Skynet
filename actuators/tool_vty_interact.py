"""
VTY Interaction Tool - Communicates with Zyxel VTY console
"""
import socket
import time

def vty_interact(target, port, commands, timeout=10):
    """
    Connect to a VTY console, send commands, and receive responses.
    Returns the full conversation.
    """
    results = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((target, port))
        time.sleep(0.5)
        banner = s.recv(4096)
        results['banner'] = banner.decode('utf-8', errors='replace')
        
        for cmd in commands:
            try:
                s.send((cmd + '\r\n').encode())
                time.sleep(0.3)
                resp = b''
                try:
                    while True:
                        s.settimeout(0.5)
                        d = s.recv(4096)
                        if not d:
                            break
                        resp += d
                except socket.timeout:
                    pass
                results[cmd] = resp.decode('utf-8', errors='replace')
            except Exception as e:
                results[cmd] = f'ERROR: {e}'
                break
    except Exception as e:
        results['error'] = str(e)
    finally:
        s.close()
    return results
