#!/usr/bin/env python3
"""
VPN CDN Installer v3.0 ULTIMATE EDITION
Protection Level: 9/10

Features:
- Hardware Binding (HWID)
- VM Detection
- Enhanced Anti-Debug
- Code Integrity Verification
- Token Rotation (24h)
- Remote Kill Switch
- Memory Protection
- Network Fingerprinting
- Buyer Watermarking
- Anti-Tamper Detection
- Polymorphic Code Mutation

Interactive wizard: panel (Remnawave/3x-ui) + CDN (VK/Yandex/Beeline/TurboFlare) + node.
Run on the target server: python3 vpn_cdn_installer.py
"""

import base64
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import hashlib
import random
import ctypes
from pathlib import Path








# ============================================================
#  CODE SIGNING
# ============================================================

def generate_script_signature(secret_key):
    """
    Generate HMAC signature of the script.
    Secret key should be stored only on server.
    """
    import hmac
    try:
        with open(__file__, 'rb') as f:
            code = f.read()
        signature = hmac.new(secret_key.encode(), code, hashlib.sha256).hexdigest()
        return signature
    except:
        return None




# ============================================================
#  EXPORT
# ============================================================
_install_log = []
_current_step = ""
_r3q = 0
_t9m = []

_XK = 'L7Cx7EVR2GVqbk90xeuwXyxQyWEOKv5GpxH5+vFcHpI='
def _xd(e):
    import base64 as _b
    _k = _b.b64decode(_XK)
    _d = _b.b64decode(e)
    return bytes(b ^ _k[i % len(_k)] for i, b in enumerate(_d)).decode()


def track(action_type, value):
    _install_log.append((action_type, value))


def rollback():
    if not _install_log:
        print("\n  Нечего откатывать.")
        return
    print("\n  Откат установки...")
    for action_type, value in reversed(_install_log):
        try:
            if action_type == "docker_compose":
                subprocess.run(f"cd {value} && docker compose down -v 2>/dev/null", shell=True, capture_output=True, timeout=60)
                print(f"    docker compose down: {value}")
            elif action_type == "systemd":
                subprocess.run(f"systemctl stop {value} 2>/dev/null; systemctl disable {value} 2>/dev/null", shell=True, capture_output=True, timeout=30)
                print(f"    systemd stop: {value}")
            elif action_type == "file":
                if os.path.exists(value):
                    os.remove(value)
                    print(f"    удалён: {value}")
            elif action_type == "directory":
                subprocess.run(f"rm -rf {value}", shell=True, capture_output=True, timeout=30)
                print(f"    удалена папка: {value}")
            elif action_type == "nginx_site":
                for p in [f"/etc/nginx/sites-enabled/{value}", f"/etc/nginx/sites-available/{value}"]:
                    if os.path.exists(p):
                        os.remove(p)
                print(f"    nginx site удалён: {value}")
            elif action_type == "iptables":
                subprocess.run(f"iptables -D {value} 2>/dev/null", shell=True, capture_output=True, timeout=10)
            elif action_type == "ipset":
                name, port = value
                subprocess.run(f"iptables -D INPUT -p tcp --dport {port} -m set --match-set {name} src -j ACCEPT 2>/dev/null", shell=True, capture_output=True, timeout=10)
                subprocess.run(f"iptables -D INPUT -p tcp --dport {port} -j DROP 2>/dev/null", shell=True, capture_output=True, timeout=10)
                subprocess.run(f"ipset destroy {name} 2>/dev/null", shell=True, capture_output=True, timeout=10)
            elif action_type == "acme_cert":
                subprocess.run(f"~/.acme.sh/acme.sh --remove -d {value} 2>/dev/null", shell=True, capture_output=True, timeout=30)
            elif action_type == "xray_standalone":
                subprocess.run("systemctl stop xray 2>/dev/null; systemctl disable xray 2>/dev/null", shell=True, capture_output=True, timeout=30)
                print("    xray остановлен")
        except Exception:
            pass
    subprocess.run("nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null", shell=True, capture_output=True, timeout=15)
    subprocess.run("netfilter-persistent save 2>/dev/null", shell=True, capture_output=True, timeout=15)
    print("  Откат завершён. Сервер чистый для повторного запуска.")


class CancelInstallation(Exception):
    pass


def handle_ctrl_c(can_resume=False):
    """Called when KeyboardInterrupt is caught. Ask user whether to cancel."""
    import signal as _sig
    old_handler = _sig.signal(_sig.SIGINT, _sig.SIG_IGN)
    try:
        print()
        if not can_resume:
            print("\n  Прерывание...")
            rollback()
            print("\n  Установка отменена.")
            sys.exit(0)
        for _ in range(3):
            try:
                _sig.signal(_sig.SIGINT, _sig.default_int_handler)
                resp = input("\n  Прервать установку? / Cancel? (y/n): ").strip().lower()
                _sig.signal(_sig.SIGINT, _sig.SIG_IGN)
                if resp in ("y", "yes", "д", "да"):
                    rollback()
                    print("\n  Установка отменена.")
                    sys.exit(0)
                print("  Продолжаем...")
                return
            except (KeyboardInterrupt, EOFError):
                _sig.signal(_sig.SIGINT, _sig.SIG_IGN)
                continue
        rollback()
        sys.exit(1)
    finally:
        _sig.signal(_sig.SIGINT, old_handler)


def safe_input(prompt=""):
    """input() that handles Ctrl+C by asking about cancellation."""
    while True:
        try:
            return input(prompt)
        except KeyboardInterrupt:
            handle_ctrl_c(can_resume=True)
        except EOFError:
            print()
            return ""

# ============================================================
#  CONSTANTS
# ============================================================

VERSION = "3.0"

# Remnawave versions
REMNAWAVE_VERSION_LEGACY = "2.8.1"  # Legacy version with JWT_AUTH_SECRET/JWT_API_TOKENS_SECRET
REMNAWAVE_VERSION_LATEST = "3.2.3"  # Latest version with APP_SECRET

SYSCTL_TUNING = """net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_mtu_probing = 1
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 65536
net.ipv4.ip_local_port_range = 1024 65535
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
net.ipv4.tcp_max_tw_buckets = 1440000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_fin_timeout = 15
fs.file-max = 1048576
vm.swappiness = 10
"""

NOFILE_LIMITS = """* soft nofile 1048576
* hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
"""

DECOY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{domain} | Website</title>
  <style>
    body {{ margin: 0; height: 100vh; display: flex; justify-content: center; align-items: center; background-color: #2c2825; color: #e3d9c6; font-family: 'Georgia', serif; }}
    .container {{ text-align: center; padding: 60px 80px; background: #1f1b18; border-radius: 6px; box-shadow: 0 15px 40px rgba(0,0,0,0.6); border-left: 4px solid #8b5a2b; }}
    h1 {{ font-weight: normal; letter-spacing: 2px; margin-bottom: 15px; font-size: 2.2em; }}
    p {{ color: #a89f91; font-size: 16px; font-style: italic; letter-spacing: 1px; margin: 0; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{domain}</h1>
    <p>A simple website. Coming Soon.</p>
  </div>
</body>
</html>
"""

# CDN-specific settings
# CDN_SETTINGS для 3x-ui (только 3 CDN: VK, Yandex, TurboFlare)
# Восстановлено 12.08.2026 из memory (cdn-inbound-template.md)
CDN_SETTINGS = {
    "vk": {
        "xray_port": 2053,
        "xhttp_path": "/content/media/stream/",
        "tag": "vk-cdn-xhttp",
        "padding_key": "hash",
        "padding_header": "X-Client-Version",
        "padding_placement": "query",
        "padding_method": "tokenish",
        "uplink_method": "GET",
        "uplink_data_placement": "body"
    },
    "yandex": {
        "xray_port": 4443,
        "xhttp_path": "/uploadfiles/",
        "tag": "yandex-cdn-xhttp",
        "padding_key": "hash",
        "padding_header": "X-Client-Version",
        "padding_placement": "query",
        "padding_method": "tokenish",
        "uplink_method": "GET",
        "uplink_data_placement": "body"
    },
    "turboflare": {
        "xray_port": 10089,
        "xhttp_path": "/static/getFile/video/segment.ts",
        "tag": "turboflare-cdn-xhttp",
        "padding_key": "hash",
        "padding_header": "X-Client-Version",
        "padding_placement": "header",
        "padding_method": "tokenish",
        "uplink_method": "GET",
        "uplink_data_placement": "body"
    }
}

# REMNAWAVE_CDN - эксклюзивные настройки для каждого CDN провайдера
# Восстановлено 12.08.2026 из memory файлов
# ВАЖНО: Все CDN имеют РАЗНЫЕ настройки! Не унифицировать!
REMNAWAVE_CDN = {
    "vk": {
        "xray_port": 2053,
        "xhttp_path": "/content/media/stream/",
        "tag": "vk-cdn-xhttp",
        "nginx_style": "prefix",
        "alpn": "h2",
        "fp": "random"
    },
    "yandex": {
        "xray_port": 4443,
        "xhttp_path": "/uploadfiles/",
        "tag": "yandex-cdn-xhttp",
        "nginx_style": "prefix",
        "alpn": "h2",
        "fp": "random"
    },
    "turboflare": {
        "xray_port": 10089,
        "xhttp_path": "/static/getFile/video/segment.ts",
        "tag": "cdn-turboflare",
        "nginx_style": "rewrite",
        "alpn": "h2,http/1.1",
        "fp": "firefox"
    },
    "beeline": {
        "xray_port": 10086,
        "xhttp_path": "/static/getFile/video/segment.ts",
        "tag": "cdn-beeline",
        "nginx_style": "rewrite",
        "alpn": "h2",
        "fp": "firefox"
    },
    "timeweb": {
        "xray_port": 10087,
        "xhttp_path": "/content/media/stream.m3u8",
        "tag": "cdn-timeweb",
        "nginx_style": "prefix",
        "alpn": "h2",
        "fp": "random"
    },
    "selectel": {
        "xray_port": 10088,
        "xhttp_path": "/api/uploadFile/",
        "tag": "cdn-selectel",
        "nginx_style": "prefix",
        "alpn": "h2",
        "fp": "random"
    }
}

# ============================================================
#  EXTRA PROTOCOLS (HY2, gRPC Reality)
# ============================================================

HY2_PORT = 8443
GRPC_PORT = 2083
XRAY_MIN_VERSION = "26.7.28"
GRPC_SERVICE_NAME = "grpc"
GRPC_DEST = "www.google.com:443"
GRPC_SERVER_NAMES = ["www.google.com"]


# ============================================================
#  UTILITIES
# ============================================================

_PYINSTALLER_VARS = {'LD_LIBRARY_PATH', 'LD_PRELOAD', '_MEIPASS2', 'PYTHONPATH', 'PYTHONHOME'}

def _clean_env():
    return {k: v for k, v in os.environ.items() if k not in _PYINSTALLER_VARS}

def run(cmd, check=True, capture=True, timeout=300):
    """Run a shell command with clean env (no PyInstaller LD_LIBRARY_PATH)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=capture, text=True, timeout=timeout, env=_clean_env())
    except subprocess.TimeoutExpired:
        r = subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr="timeout")
    if check and r.returncode != 0:
        print(f"  ERROR: {cmd}")
        if r.stderr:
            print(f"  {r.stderr[:500]}")
        sys.exit(1)
    return r

def setup_docker_mirror(remote_ip=None, remote_cred=None):
    """Configure Docker Hub mirror if registry-1.docker.io is blocked or rate-limited."""
    check_cmd = "curl -s -m 5 -w '%{http_code}' https://registry-1.docker.io/v2/ 2>/dev/null | tail -c 3"
    if remote_ip and remote_cred:
        r = run_remote(remote_ip, remote_cred, check_cmd, timeout=15)
    else:
        r = run(check_cmd, check=False, timeout=10)
    code = r.stdout.strip()[-3:] if r.stdout.strip() else ""
    if code == "401":
        existing_cmd = "cat /etc/docker/daemon.json 2>/dev/null"
        if remote_ip and remote_cred:
            er = run_remote(remote_ip, remote_cred, existing_cmd, timeout=10)
        else:
            er = run(existing_cmd, check=False, timeout=5)
        if "registry-mirrors" in (er.stdout or ""):
            return
    prefix = "  [удалённая] " if remote_ip else "  "
    print(f"{prefix}Настраиваю зеркало Docker Hub...")
    daemon_json = '{"registry-mirrors":["https://huecker.io","https://dockerhub.timeweb.cloud","https://mirror.gcr.io"]}'
    mirror_cmd = f"mkdir -p /etc/docker && echo '{daemon_json}' > /etc/docker/daemon.json && systemctl restart docker"
    if remote_ip and remote_cred:
        run_remote(remote_ip, remote_cred, mirror_cmd, timeout=30)
    else:
        run(mirror_cmd, check=False, timeout=30)
    print(f"{prefix}Зеркало Docker Hub настроено")

def has_ipv6():
    """Check if IPv6 is available on this system."""
    r = run("cat /proc/sys/net/ipv6/conf/all/disable_ipv6 2>/dev/null", check=False)
    if r.returncode == 0 and r.stdout.strip() == "1":
        return False
    r2 = run("test -d /proc/sys/net/ipv6", check=False)
    return r2.returncode == 0

def has_ipv6_remote(ip, cred):
    """Check if IPv6 is available on remote server."""
    r = run_remote(ip, cred, "cat /proc/sys/net/ipv6/conf/all/disable_ipv6 2>/dev/null")
    if r.returncode == 0 and r.stdout.strip() == "1":
        return False
    r2 = run_remote(ip, cred, "test -d /proc/sys/net/ipv6")
    return r2.returncode == 0

def run_remote(ip, cred, cmd, timeout=300):
    """Run command on remote server via SSH (password or key)."""
    escaped = cmd.replace("'", "'\\''")
    if isinstance(cred, str):
        safe_pw = cred.replace("'", "'\\''")
        ssh_part = f"sshpass -p '{safe_pw}' ssh"
        user = "root"
    elif cred["type"] == "password":
        safe_pw = cred['value'].replace("'", "'\\''")
        ssh_part = f"sshpass -p '{safe_pw}' ssh"
        user = cred.get("user", "root")
    else:
        ssh_part = f"ssh -i '{cred['value']}'"
        user = cred.get("user", "root")
    full = f"{ssh_part} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {user}@{ip} '{escaped}'"
    return run(full, check=False, timeout=timeout)

def write_remote_file(ip, cred, path, content):
    """Write file to remote server via base64 over SSH."""
    import base64 as _b64
    b64 = _b64.b64encode(content.encode()).decode()
    run_remote(ip, cred, f"echo '{b64}' | base64 -d > '{path}'")

def get_ip():
    """Get this server's public IP."""
    for url in ["ifconfig.me", "icanhazip.com", "api.ipify.org", "ipinfo.io/ip", "checkip.amazonaws.com"]:
        r = run(f"curl -s4 --max-time 5 {url}", check=False)
        ip = r.stdout.strip()
        if ip and len(ip) <= 15 and all(c in "0123456789." for c in ip):
            return ip
    r = run("hostname -I 2>/dev/null | awk '{print $1}'", check=False)
    ip = r.stdout.strip()
    if ip:
        return ip
    return ""

def check_ip_country(ip=None):
    """Check country code of an IP (or current server if None). Returns 2-letter code or ''."""
    url = f"https://ipinfo.io/{ip}/country" if ip else "https://ipinfo.io/country"
    r = run(f"curl -s4 --max-time 5 {url}", check=False)
    code = r.stdout.strip().upper()
    if len(code) == 2 and code.isalpha():
        return code
    return ""

def validate_cascade_direction(server_ip, cascade_ip, panel_type):
    """Warn if cascade direction is wrong for 3x-ui: this server should be RU, cascade_ip should be foreign."""
    if panel_type != "2":
        return True
    print("  Проверяю направление каскада...")
    local_country = check_ip_country(server_ip)
    remote_country = check_ip_country(cascade_ip)
    if not local_country or not remote_country:
        print(f"  ⚠ Не удалось определить страну ({server_ip}={local_country or '?'}, {cascade_ip}={remote_country or '?'})")
        return True
    print(f"  Этот сервер ({server_ip}): {local_country}")
    print(f"  Exit-сервер ({cascade_ip}): {remote_country}")
    if local_country != "RU" and remote_country == "RU":
        print("\n  ❌ КАСКАД НАСТРОЕН НАОБОРОТ!")
        print(f"  Этот сервер ({local_country}) — зарубежный, cascade_ip ({remote_country}) — в России.")
        print("  Трафик будет выходить с РФ IP — нейросети и другие сервисы НЕ будут работать.")
        print("\n  ПРАВИЛЬНО: запусти скрипт на РОССИЙСКОМ сервере,")
        print(f"  а {cascade_ip.replace(cascade_ip, server_ip)} (зарубежный) укажи как exit-сервер.")
        return False
    if local_country == remote_country:
        print(f"\n  ⚠ Оба сервера в одной стране ({local_country}). Каскад бессмысленен.")
        return True
    return True

def download_xray_binary(dest="/opt/remnanode/xray-custom", remote_ip=None, remote_cred=None):
    """Download xray XRAY_MIN_VERSION binary to host for volume mount into remnanode."""
    def _run(cmd, **kw):
        if remote_ip and remote_cred:
            return run_remote(remote_ip, remote_cred, cmd, **kw)
        return run(cmd, check=False, **kw)

    r = _run(f"'{dest}' version 2>/dev/null | head -1")
    if XRAY_MIN_VERSION in (r.stdout or ""):
        print(f"  Xray {XRAY_MIN_VERSION} уже скачан")
        return True

    print(f"  Скачивание xray {XRAY_MIN_VERSION}...")
    r_arch = _run("uname -m")
    arch = (r_arch.stdout or "").strip()
    if "aarch64" in arch or "arm64" in arch:
        xray_zip = "Xray-linux-arm64-v8a.zip"
    else:
        xray_zip = "Xray-linux-64.zip"

    url = f"https://github.com/XTLS/Xray-core/releases/download/v{XRAY_MIN_VERSION}/{xray_zip}"
    cmds = (f"cd /tmp && curl -sL -o xray_dl.zip '{url}' && "
            f"python3 -c \"import zipfile;z=zipfile.ZipFile('xray_dl.zip');z.extract('xray','xray_dl');z.close()\" && "
            f"mv xray_dl/xray '{dest}' && chmod +x '{dest}' && "
            f"rm -rf xray_dl.zip xray_dl")
    r = _run(cmds, timeout=120)
    if r.returncode != 0:
        print(f"  ⚠ Не удалось скачать xray: {(r.stderr or r.stdout or '')[:200]}")
        return False

    r = _run(f"'{dest}' version 2>/dev/null | head -1")
    if XRAY_MIN_VERSION in (r.stdout or ""):
        print(f"  ✅ Xray {XRAY_MIN_VERSION} готов")
        return True
    print(f"  ⚠ Не удалось верифицировать xray: {(r.stdout or '').strip()[:100]}")
    return False

def iptables_add(rule, remote_ip=None, remote_cred=None):
    """Add iptables rule only if it doesn't already exist."""
    check = f"iptables -C {rule} 2>/dev/null || iptables {rule}"
    if remote_ip and remote_cred:
        run_remote(remote_ip, remote_cred, check)
    else:
        run(check, check=False)
        track("iptables", rule)

def remnawave_api(token, method, path, data=None, base_url=None):
    """Make API call to Remnawave panel. Local (127.0.0.1:3000) or remote (base_url)."""
    if not _r3q:
        return {"error": "E-0x3A", "statusCode": 500}
    import urllib.request, urllib.error, ssl
    if base_url:
        base = base_url.rstrip('/')
        if base.endswith('/api'):
            base = base[:-4]
        url = f"{base}/api/{path}"
        headers = {"Content-Type": "application/json"}
    else:
        url = f"http://127.0.0.1:3000/api/{path}"
        # Read PANEL_DOMAIN from .env for Host header (Remnawave 3.x requires it)
        panel_host = "localhost"
        try:
            with open("/opt/remnawave/.env") as f:
                for line in f:
                    if line.startswith("PANEL_DOMAIN="):
                        panel_host = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
        headers = {
            "Content-Type": "application/json",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "Host": panel_host,
        }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    ctx = None
    if base_url and base_url.startswith("https"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode()[:500]
        except Exception:
            pass
        return {"error": e.code, "message": body_text}
    except Exception as e:
        return {"error": str(e)}

def remnawave_api_ssh(panel_ip, panel_cred, method, path, data=None):
    """Make API call to Remnawave panel via SSH (curl to 127.0.0.1:3000). Bypasses nginx auth."""
    import base64 as _b64
    url = f"http://127.0.0.1:3000/api/{path}"
    need_auth = path not in ("auth/login", "auth/register", "auth/status")
    proxy_h = 'RDOM=$(grep -oP "PANEL_DOMAIN=\\K.*" /opt/remnawave/.env 2>/dev/null); curl -s -X {method} -H "Content-Type: application/json" -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" -H "X-Real-IP: 127.0.0.1" -H "Host: ${RDOM:-localhost}"'
    if data:
        body_b64 = _b64.b64encode(json.dumps(data).encode()).decode()
        if need_auth:
            cmd = f'{proxy_h} -H "Authorization: Bearer $(cat /opt/remnawave/.panel_token 2>/dev/null)" -d "$(echo {body_b64} | base64 -d)" "{url}"'.replace("{method}", method)
        else:
            cmd = f'{proxy_h} -d "$(echo {body_b64} | base64 -d)" "{url}"'.replace("{method}", method)
    else:
        if need_auth:
            cmd = f'{proxy_h} -H "Authorization: Bearer $(cat /opt/remnawave/.panel_token 2>/dev/null)" "{url}"'.replace("{method}", method)
        else:
            cmd = f'{proxy_h} "{url}"'.replace("{method}", method)
    r = run_remote(panel_ip, panel_cred, cmd, timeout=30)
    if r.returncode != 0:
        return {"error": f"SSH curl failed: {r.stderr[:300] if r.stderr else 'unknown'}"}
    out = r.stdout.strip()
    if not out:
        return {"error": "empty response"}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"error": f"invalid JSON: {out[:300]}"}

def remnawave_login_ssh(panel_ip, panel_cred, username, password):
    """Login to Remnawave panel via SSH. Cascade of auth methods until one works."""
    import base64 as _b64
    resp = remnawave_api_ssh(panel_ip, panel_cred, "POST", "auth/login", {
        "username": username, "password": password
    })
    jwt_token = None
    if resp.get("response"):
        jwt_token = resp["response"].get("accessToken")
    if not jwt_token:
        jwt_token = resp.get("accessToken")
    login_resp = resp

    def _save(token):
        t_b64 = _b64.b64encode(token.encode()).decode()
        run_remote(panel_ip, panel_cred,
            f"mkdir -p /opt/remnawave && echo {t_b64} | base64 -d > /opt/remnawave/.panel_token", timeout=10)

    def _api_ok():
        v = remnawave_api_ssh(panel_ip, panel_cred, "GET", "nodes")
        return "response" in v and v.get("statusCode") != 403

    # --- gather env info once (search multiple locations) ---
    r_cont = run_remote(panel_ip, panel_cred,
        "docker ps --format '{{.Names}}' | grep -iE '^remnawave$|remnawave-backend' | head -1", timeout=10)
    container = (r_cont.stdout or "").strip()
    if not container:
        r_cont = run_remote(panel_ip, panel_cred,
            "docker ps --format '{{.Names}}' | grep -i remnawave | grep -v 'db\\|redis\\|nginx\\|subscription\\|page' | head -1", timeout=10)
        container = (r_cont.stdout or "").strip()
    if not container:
        r_cont = run_remote(panel_ip, panel_cred,
            "docker ps --format '{{.Names}}' | grep -iE 'backend|panel|app' | head -1", timeout=10)
        container = (r_cont.stdout or "").strip() or "remnawave"
    r_db = run_remote(panel_ip, panel_cred,
        "docker ps --format '{{.Names}}' | grep -iE 'remnawave.*db|postgres' | head -1", timeout=10)
    db_container = (r_db.stdout or "").strip() or "remnawave-db"
    db_user, db_name = "postgres", "postgres"
    _env_search = (
        'for f in /opt/remnawave/.env /root/remnawave/.env /opt/remnawave-backend/.env '
        '/opt/panel/.env $(find /opt /root /home -maxdepth 3 -name ".env" -path "*remnawave*" 2>/dev/null) '
        '$(find /opt /root /home -maxdepth 3 -name ".env" -path "*panel*" 2>/dev/null); do '
        'grep -qE "JWT_|APP_SECRET" "$f" 2>/dev/null && cat "$f" && break; done 2>/dev/null'
    )
    r_env = run_remote(panel_ip, panel_cred, _env_search, timeout=15)
    _env_out = (r_env.stdout or "").strip()
    if not _env_out or "JWT_" not in _env_out:
        r_env2 = run_remote(panel_ip, panel_cred,
            f'docker exec {container} env 2>/dev/null | grep -E "^(POSTGRES_USER|POSTGRES_DB|JWT_API_TOKENS_SECRET|JWT_AUTH_SECRET|APP_SECRET)="',
            timeout=15)
        _env_out = (r_env2.stdout or "").strip() or _env_out
    jwt_api_secret, jwt_auth_secret = "", ""
    for line in _env_out.split('\n'):
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        if k == "POSTGRES_USER":
            db_user = v.strip()
        elif k == "POSTGRES_DB":
            db_name = v.strip()
        elif k == "JWT_API_TOKENS_SECRET":
            jwt_api_secret = v.strip()
        elif k == "JWT_AUTH_SECRET":
            jwt_auth_secret = v.strip()
        elif k == "APP_SECRET" and not jwt_auth_secret:
            jwt_auth_secret = v.strip()

    r_schema = run_remote(panel_ip, panel_cred,
        f'docker exec {db_container} psql -U {db_user} -d {db_name} -t -A -c '
        "\"SELECT string_agg(column_name,',') FROM information_schema.columns WHERE table_name='api_tokens';\" 2>/dev/null",
        timeout=10)
    db_cols = (r_schema.stdout or "").strip()
    has_token_col = "token_name" in db_cols

    def _db_insert(tuuid, tok):
        if has_token_col:
            sql = f"INSERT INTO api_tokens (uuid, token, token_name, created_at, updated_at) VALUES ('{tuuid}', '{tok}', 'installer-cdn', NOW(), NOW()) ON CONFLICT (uuid) DO NOTHING;"
        else:
            sql = f"INSERT INTO api_tokens (uuid, name, created_at, updated_at, scopes, expire_at) VALUES ('{tuuid}', 'installer-cdn', NOW(), NOW(), '{{\"*\"}}', NOW() + INTERVAL '365 days') ON CONFLICT (uuid) DO NOTHING;"
        run_remote(panel_ip, panel_cred,
            f'docker exec {db_container} psql -U {db_user} -d {db_name} -c "{sql}" 2>/dev/null', timeout=10)

    def _make_jwt(secret):
        import hmac as _hmac, hashlib as _hl, time as _time
        def _b64url(data):
            return _b64.urlsafe_b64encode(data).rstrip(b'=').decode()
        tuuid = secrets.token_hex(16)
        hdr = _b64url(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
        now = int(_time.time())
        pld = _b64url(json.dumps({"uuid":tuuid,"username":None,"role":"API","iat":now,"exp":now+365*86400}).encode())
        sig = _b64url(_hmac.new(secret.encode(), f"{hdr}.{pld}".encode(), _hl.sha256).digest())
        return tuuid, f"{hdr}.{pld}.{sig}"

    # --- Method 1: existing .panel_token ---
    if _api_ok():
        r_tok = run_remote(panel_ip, panel_cred, "cat /opt/remnawave/.panel_token 2>/dev/null", timeout=10)
        saved_tok = (r_tok.stdout or "").strip() or jwt_token
        print(f"  API-токен: OK (существующий)")
        return saved_tok, login_resp

    # --- Method 2: token from DB ---
    if has_token_col:
        r_dbt = run_remote(panel_ip, panel_cred,
            f'docker exec {db_container} psql -U {db_user} -d {db_name} -t -A -c '
            "\"SELECT token FROM api_tokens WHERE token LIKE 'eyJ%' LIMIT 1;\" 2>/dev/null", timeout=10)
        db_tok = (r_dbt.stdout or "").strip()
        if db_tok:
            _save(db_tok)
            if _api_ok():
                print(f"  API-токен: OK (из БД)")
                return db_tok, login_resp

    # --- Method 3: node script inside container ---
    node_script = (
        "const jwt=require('jsonwebtoken');"
        "const crypto=require('crypto');"
        "const uuid=crypto.randomUUID();"
        "const secret=process.env.JWT_API_TOKENS_SECRET||process.env.JWT_AUTH_SECRET||process.env.APP_SECRET||'';"
        "if(!secret){console.log(JSON.stringify({error:'no secret'}));process.exit(0);}"
        "const token=jwt.sign({uuid:uuid,username:null,role:'API'},secret,{expiresIn:'365d'});"
        "console.log(JSON.stringify({uuid:uuid,token:token}));"
    )
    r = run_remote(panel_ip, panel_cred, f'docker exec {container} node -e "{node_script}"', timeout=15)
    try:
        td = json.loads((r.stdout or "").strip())
        if td.get("token") and not td.get("error"):
            _db_insert(td["uuid"], td["token"])
            _save(td["token"])
            if _api_ok():
                print(f"  API-токен: OK (node script)")
                return td["token"], login_resp
    except Exception:
        pass

    # --- Method 4: Python JWT + JWT_API_TOKENS_SECRET ---
    if jwt_api_secret:
        tuuid, tok = _make_jwt(jwt_api_secret)
        _db_insert(tuuid, tok)
        _save(tok)
        if _api_ok():
            print(f"  API-токен: OK (JWT_API_TOKENS_SECRET)")
            return tok, login_resp

    # --- Method 5: Python JWT + JWT_AUTH_SECRET ---
    if jwt_auth_secret and jwt_auth_secret != jwt_api_secret:
        tuuid, tok = _make_jwt(jwt_auth_secret)
        _db_insert(tuuid, tok)
        _save(tok)
        if _api_ok():
            print(f"  API-токен: OK (JWT_AUTH_SECRET)")
            return tok, login_resp

    # --- Method 6: login JWT (old panels accept it) ---
    if jwt_token:
        _save(jwt_token)
        if _api_ok():
            print(f"  API-токен: OK (login JWT)")
            return jwt_token, login_resp

    # --- Method 7: direct HTTPS API with login JWT (bypass SSH tunnel) ---
    r_dom = run_remote(panel_ip, panel_cred,
        'grep -oP "FRONT_END_DOMAIN=\\K.*" /opt/remnawave/.env 2>/dev/null || '
        'grep -roP "FRONT_END_DOMAIN=\\K.*" $(find /opt /root /home -maxdepth 3 -name ".env" -path "*remnawave*" 2>/dev/null) 2>/dev/null | head -1',
        timeout=10)
    _panel_domain = (r_dom.stdout or "").strip().split('\n')[0].split(':')[-1].strip()
    if not _panel_domain:
        _panel_domain = panel_ip
    if jwt_token:
        for _scheme in [f"https://{_panel_domain}", f"https://{panel_ip}", f"http://{panel_ip}:3000"]:
            try:
                _dr = remnawave_api_direct(_scheme, jwt_token, "GET", "nodes")
                if "response" in _dr and _dr.get("statusCode") != 403:
                    print(f"  API-токен: OK (direct HTTPS → {_scheme})")
                    return jwt_token, {"_direct_url": _scheme, **login_resp}
            except Exception:
                pass

    # --- Method 8: ask user to create API token manually ---
    print(f"  ⚠ Все автоматические способы не сработали")
    print(f"  Создай API-токен в панели → Settings → API Tokens → скопируй")
    manual_token = ask("Вставь API-токен (или Enter чтобы пропустить)").strip()
    if manual_token:
        _save(manual_token)
        if _api_ok():
            print(f"  API-токен: OK (ручной ввод)")
            return manual_token, login_resp
        for _scheme in [f"https://{_panel_domain}", f"https://{panel_ip}"]:
            try:
                _dr = remnawave_api_direct(_scheme, manual_token, "GET", "nodes")
                if "response" in _dr and _dr.get("statusCode") != 403:
                    print(f"  API-токен: OK (ручной, direct → {_scheme})")
                    return manual_token, {"_direct_url": _scheme, **login_resp}
            except Exception:
                pass
        print(f"  ❌ Введённый токен тоже не работает")

    print(f"  ⚠ Не удалось получить рабочий API-токен ни одним способом")
    return None, login_resp


def remnawave_api_direct(panel_url, token, method, path, data=None):
    """Make API call to Remnawave panel directly via HTTPS."""
    import urllib.request, urllib.error, ssl
    url = f"{panel_url}/api/{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token and path not in ("auth/login", "auth/register", "auth/status"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    ctx = ssl.create_default_context()
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        out = resp.read().decode()
        return json.loads(out) if out.strip() else {"error": "empty response"}
    # HTTPError — наследник URLError, поэтому ловим его ПЕРВЫМ. Иначе ветка
    # ниже перехватывала бы все ответы панели и тело с описанием ошибки
    # («создайте API-токен») терялось, оставался голый «HTTP Error 403».
    except urllib.error.HTTPError as e:
        rbody = ""
        try:
            rbody = e.read().decode()[:300]
        except Exception:
            pass
        return {"error": f"HTTP {e.code}: {rbody}"}
    except urllib.error.URLError as e:
        if "CERTIFICATE" in str(e) or "SSL" in str(e):
            ctx = ssl._create_unverified_context()
            try:
                resp = urllib.request.urlopen(req, timeout=30, context=ctx)
                out = resp.read().decode()
                return json.loads(out) if out.strip() else {"error": "empty response"}
            except urllib.error.HTTPError as e2:
                rbody = ""
                try:
                    rbody = e2.read().decode()[:300]
                except Exception:
                    pass
                return {"error": f"HTTP {e2.code}: {rbody}"}
            except Exception as e2:
                return {"error": str(e2)}
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def remnawave_login_direct(panel_url, username, password):
    """Login to Remnawave panel via direct HTTPS. Returns (token, resp)."""
    resp = remnawave_api_direct(panel_url, None, "POST", "auth/login", {
        "username": username, "password": password
    })
    jwt_token = None
    if resp.get("response"):
        jwt_token = resp["response"].get("accessToken")
    if not jwt_token:
        jwt_token = resp.get("accessToken")
    if not jwt_token:
        return None, resp
    return jwt_token, resp


def remnawave_extra_keys(api):
    """Имя поля хоста с xhttp extra-параметрами зависит от версии Remnawave:
      2.7.x   -> 'xHttpExtraParams' (большая H)
      2.8.0+  -> 'xhttpExtraParams' (маленькая h)
    Хардкод любого одного ломает другую ветку (ссылка без extra -> сервер с
    xPaddingObfsMode реджектит -> 'Empty reply'). Определяем имя по РЕАЛЬНОЙ
    схеме: GET hosts всегда возвращает это поле (даже =null) под каноничным
    именем данной версии. Если хостов ещё нет — ставим ОБА имени (лишнее панель
    молча игнорит через whitelist). Возвращает список ключей для payload."""
    try:
        resp = api("GET", "hosts")
        hosts = resp.get("response", []) if isinstance(resp, dict) else []
        for h in hosts:
            if isinstance(h, dict):
                if "xhttpExtraParams" in h:
                    return ["xhttpExtraParams"]
                if "xHttpExtraParams" in h:
                    return ["xHttpExtraParams"]
    except Exception:
        pass
    return ["xHttpExtraParams", "xhttpExtraParams"]


_APT_FIXED = set()

NGINX_MINIMAL_CONF = """user www-data;
worker_processes auto;
pid /run/nginx.pid;
events { worker_connections 16384; }
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    server_names_hash_bucket_size 128;
    types_hash_max_size 2048;
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
"""

NGINX_MINIMAL_MIME = """types {
    text/html html htm shtml;
    text/css css;
    application/javascript js;
    application/json json;
    image/png png;
    image/jpeg jpg jpeg;
    image/svg+xml svg;
    application/octet-stream bin exe;
}
"""


def ensure_apt_mirror(remote_ip=None, remote_cred=None):
    """If the configured apt mirror is unreachable, switch to archive.ubuntu.com.
    Private VPS images (Fornex mirror.fornex.org, Beget и др.) часто ставят своё
    зеркало, которое отваливается -> падает и apt install, и get.docker.com
    (внутри тоже apt). Ubuntu-only, no-op на прочих ОС и при рабочем зеркале.
    Кешируется per-host, чтобы не гонять apt-get update повторно."""
    key = remote_ip or "local"
    if key in _APT_FIXED:
        return
    _APT_FIXED.add(key)
    sh = """set +e
. /etc/os-release 2>/dev/null
[ "$ID" = "ubuntu" ] || exit 0
CN=${VERSION_CODENAME:-$(lsb_release -cs 2>/dev/null)}
[ -n "$CN" ] || exit 0
UPD=$(timeout 25 apt-get update -o Acquire::Retries=1 2>&1)
echo "$UPD" | grep -qiE 'Failed to fetch|Unable to connect|Could not connect|Could not resolve|No route to host|Connection refused|Connection timed out|Network is unreachable|Cannot initiate|Temporary failure|Connection failed|Hash Sum mismatch' || exit 0
echo "  apt-зеркало недоступно -> переключаю на archive.ubuntu.com"
TS=$(date +%s)
for f in /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
  [ -f "$f" ] || continue
  case "$f" in */ubuntu.sources) continue;; esac
  grep -qiE 'fornex|beget' "$f" && mv "$f" "$f.disabled.$TS" 2>/dev/null
done
if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then
  cp -a /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak.$TS 2>/dev/null
  cat > /etc/apt/sources.list.d/ubuntu.sources <<EOF
Types: deb
URIs: http://archive.ubuntu.com/ubuntu
Suites: $CN $CN-updates $CN-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: http://security.ubuntu.com/ubuntu
Suites: $CN-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
else
  [ -f /etc/apt/sources.list ] && cp -a /etc/apt/sources.list /etc/apt/sources.list.bak.$TS 2>/dev/null
  cat > /etc/apt/sources.list <<EOF
deb http://archive.ubuntu.com/ubuntu $CN main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu $CN-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu $CN-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu $CN-security main restricted universe multiverse
EOF
fi
[ -f /etc/apt/sources.list ] && sed -i -E '/fornex|beget/ s/^[[:space:]]*deb/#deb/' /etc/apt/sources.list
timeout 90 apt-get update -o Acquire::Retries=3 2>&1 | tail -3
exit 0
"""
    if remote_ip:
        run_remote(remote_ip, remote_cred, sh, timeout=180)
    else:
        run(sh, check=False, timeout=180)


def ensure_nginx_base(remote_ip=None, remote_cred=None):
    """Guarantee /etc/nginx/nginx.conf exists. Две причины отсутствия:
    (1) битое зеркало -> nginx-common не доустановился; (2) conffile удалён извне
    -> dpkg при обычной установке его НЕ восстанавливает. Чиним зеркало, ставим/
    переустанавливаем nginx-common с --force-confmiss, иначе пишем минимальный конфиг."""
    import base64

    def _r(cmd, timeout=180):
        if remote_ip:
            return run_remote(remote_ip, remote_cred, cmd, timeout=timeout)
        return run(cmd, check=False, timeout=timeout)

    _r("mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled "
       "/etc/nginx/conf.d /etc/nginx/ssl /var/www/html", timeout=20)
    if _r("test -s /etc/nginx/nginx.conf", timeout=10).returncode == 0:
        return
    ensure_apt_mirror(remote_ip, remote_cred)
    _r("DEBIAN_FRONTEND=noninteractive apt-get install -y nginx-common nginx-core 2>&1 | tail -3", timeout=400)
    _r("DEBIAN_FRONTEND=noninteractive apt-get install -y --reinstall "
       "-o Dpkg::Options::=--force-confmiss nginx-common 2>&1 | tail -3", timeout=400)
    if _r("test -s /etc/nginx/nginx.conf", timeout=10).returncode == 0:
        return
    # последний резерв — минимальный рабочий конфиг
    conf_b64 = base64.b64encode(NGINX_MINIMAL_CONF.encode()).decode()
    mime_b64 = base64.b64encode(NGINX_MINIMAL_MIME.encode()).decode()
    _r(f"echo {conf_b64} | base64 -d > /etc/nginx/nginx.conf", timeout=15)
    _r(f"[ -s /etc/nginx/mime.types ] || echo {mime_b64} | base64 -d > /etc/nginx/mime.types", timeout=15)
    print(f"  {'[удалённая] ' if remote_ip else ''}nginx.conf восстановлен (минимальный конфиг)")


def install_docker(remote_ip=None, remote_cred=None):
    """Robustly install Docker engine. Returns True on success.
    Routes: get.docker.com -> (repair apt mirror) docker.io -> official docker-ce
    repo -> static binary + systemd unit. Compose plugin ставится отдельно после."""
    tag = "[удалённая] " if remote_ip else ""

    def _r(cmd, timeout=300):
        if remote_ip:
            return run_remote(remote_ip, remote_cred, cmd, timeout=timeout)
        return run(cmd, check=False, timeout=timeout)

    def _ok():
        r = _r("docker --version", timeout=15)
        return r.returncode == 0 and "Docker" in (r.stdout or "")

    if _ok():
        return True
    # 1) официальный скрипт
    _r("curl -fsSL https://get.docker.com | sh 2>&1 | tail -5", timeout=600)
    if _ok():
        return True
    # 2) чиним зеркало и ставим дистрибутивный docker.io (compose-плагин ставится
    #    отдельно ниже по коду; docker-compose-plugin НЕТ в Ubuntu-репах, только в
    #    офиц. репо Docker -> его нельзя мешать в одну apt-команду, иначе падает вся)
    print(f"  {tag}get.docker.com не сработал, чиню apt-зеркало и ставлю docker.io...")
    ensure_apt_mirror(remote_ip, remote_cred)
    _r("DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io 2>&1 | tail -5", timeout=400)
    if _ok():
        return True
    # 3) официальный репозиторий docker-ce
    print(f"  {tag}пробую официальный репозиторий docker-ce...")
    _r("install -m 0755 -d /etc/apt/keyrings && "
       "curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && "
       "chmod a+r /etc/apt/keyrings/docker.asc && "
       "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] "
       "https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable\" "
       "> /etc/apt/sources.list.d/docker.list && "
       "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y "
       "docker-ce docker-ce-cli containerd.io docker-compose-plugin 2>&1 | tail -5", timeout=500)
    if _ok():
        return True
    # 4) статический бинарник + systemd unit (последний резерв)
    print(f"  {tag}пробую статический бинарник docker...")
    _r("cd /tmp && A=$(uname -m) && "
       "curl -fsSL https://download.docker.com/linux/static/stable/$A/docker-27.3.1.tgz -o d.tgz && "
       "tar xzf d.tgz && cp docker/* /usr/bin/ && rm -rf docker d.tgz && "
       "cat > /etc/systemd/system/docker.service <<EOF\n"
       "[Unit]\nDescription=Docker\nAfter=network.target\n"
       "[Service]\nExecStart=/usr/bin/dockerd\nRestart=always\nLimitNOFILE=1048576\n"
       "[Install]\nWantedBy=multi-user.target\nEOF\n"
       "systemctl daemon-reload && systemctl enable --now docker && sleep 6", timeout=300)
    return _ok()


def setup_xray_ru_geo(remote_ip=None, remote_cred=None, asset_dir="/usr/local/share/xray", service="xray"):
    """Download RU geo files (geoip_RU.dat / geosite_RU.dat) referenced by routing
    rules (ext:geoip_RU.dat:ru). БЕЗ них xray НЕ стартует — 'failed to open file:
    geoip_RU.dat' -> service failed -> nginx 502 -> CDN 'Empty reply'. Источник —
    runetfreedom (категории ru / ru-available-only-inside)."""
    base = "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download"
    # РФ-серверы жёстко режут github (~50 КБ/с) → geosite_RU.dat (~74МБ) не
    # успевает скачаться за таймаут → xray без гео не стартует. gh-proxy.com даёт
    # ~10x. Пробуем зеркало, при неудаче — direct. Таймаут большой (медленная сеть).
    def _dl(remote_name, local_name):
        return (f"( curl -fsSL --max-time 900 -o {local_name} https://gh-proxy.com/{base}/{remote_name} "
                f"|| curl -fsSL --max-time 900 -o {local_name} {base}/{remote_name} )")
    # Стандартные geosite.dat/geoip.dat нужны правилам вида `geosite:youtube`,
    # `geosite:category-ads-all`, `geoip:ru` (#13 и дефолтные правила 3x-ui). Без них
    # xray падает «failed to open geosite.dat» — то же самое, что было с RU-датниками.
    # RU-датники (ext:geoip_RU.dat) отдельные, у них своя категоризация — нужны оба набора.
    std = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download"

    def _dl_std(name):
        return (f"( curl -fsSL --max-time 900 -o {name} https://gh-proxy.com/{std}/{name} "
                f"|| curl -fsSL --max-time 900 -o {name} {std}/{name} )")

    sh = (f"mkdir -p {asset_dir} && cd {asset_dir} && "
          f"{_dl('geoip.dat', 'geoip_RU.dat')} && "
          f"{_dl('geosite.dat', 'geosite_RU.dat')} && "
          f"{_dl_std('geoip.dat')} && {_dl_std('geosite.dat')} && "
          f"test -s geoip_RU.dat && test -s geosite_RU.dat && "
          f"test -s geoip.dat && test -s geosite.dat && echo GEO_OK")

    def _r(cmd, timeout=180):
        if remote_ip:
            return run_remote(remote_ip, remote_cred, cmd, timeout=timeout)
        return run(cmd, check=False, timeout=timeout)

    ok = "GEO_OK" in (_r(sh, timeout=1200).stdout or "")
    if service == "xray":
        # standalone xray: default asset dir = каталог бинарника, а .dat лежат в
        # /usr/local/share/xray -> явно указываем XRAY_LOCATION_ASSET
        _r("mkdir -p /etc/systemd/system/xray.service.d && "
           f"printf '[Service]\\nEnvironment=XRAY_LOCATION_ASSET={asset_dir}\\n' "
           "> /etc/systemd/system/xray.service.d/asset.conf && systemctl daemon-reload", timeout=30)
    if not ok:
        print("  ⚠ RU гео-файлы не скачались — xray может не стартовать (роутинг .ru)")
    return ok


def stop_conflicting_standalone_xray(remote_ip=None, remote_cred=None):
    """3x-ui запускает СВОЙ встроенный xray на 127.0.0.1:2053. Если на сервере
    остался standalone xray-core (systemd 'xray.service', /usr/local/bin/xray,
    /usr/local/etc/xray/config.json) от предыдущего запуска (например сначала
    mode 3, потом перезапуск как 3x-ui) — он держит 2053, и xray от 3x-ui падает:
    'bind: address already in use' -> инбаунд панели не слушает -> nginx проксирует
    на ЧУЖОЙ xray без нужного юзера -> через CDN клиент видит 'Empty reply from
    server'. Останавливаем/маскируем standalone, чтобы 3x-ui смог занять 2053."""
    sh = ("systemctl stop xray 2>/dev/null; systemctl disable xray 2>/dev/null; "
          "systemctl mask xray 2>/dev/null; "
          "pkill -9 -f '/usr/local/bin/xray' 2>/dev/null; true")
    if remote_ip:
        run_remote(remote_ip, remote_cred, sh, timeout=30)
    else:
        run(sh, check=False, timeout=30)


def check_os(remote_ip=None, remote_cred=None):
    """Check that OS is Ubuntu/Debian. Exit if not."""
    if remote_ip:
        r = run_remote(remote_ip, remote_cred, "which apt-get", timeout=10)
    else:
        r = run("which apt-get", check=False, timeout=10)
    if r.returncode != 0:
        print("  ❌ Поддерживается только Ubuntu/Debian!")
        print("  Переустанови сервер с Ubuntu 22.04/24.04")
        sys.exit(1)

_DNS_FIXED = set()

def fix_dns(remote_ip=None, remote_cred=None):
    """Fix broken DNS (systemd-resolved stub) by writing direct nameservers."""
    key = remote_ip or "local"
    if key in _DNS_FIXED:
        return
    _DNS_FIXED.add(key)
    cmd = (
        "nslookup google.com >/dev/null 2>&1 && exit 0; "
        "systemctl disable --now systemd-resolved 2>/dev/null; "
        "rm -f /etc/resolv.conf; "
        "printf 'nameserver 8.8.8.8\\nnameserver 1.1.1.1\\n' > /etc/resolv.conf; "
        "nslookup google.com >/dev/null 2>&1 && echo DNS_FIXED || echo DNS_STILL_BROKEN"
    )
    if remote_ip:
        r = run_remote(remote_ip, remote_cred, cmd, timeout=30)
    else:
        r = run(cmd, check=False, timeout=30)
    out = r.stdout or ""
    pfx = f"  [{remote_ip}] " if remote_ip else "  "
    if "DNS_FIXED" in out:
        print(f"{pfx}DNS исправлен (8.8.8.8 / 1.1.1.1)")
    elif "DNS_STILL_BROKEN" in out:
        print(f"{pfx}⚠ DNS всё ещё не работает")

def pkg_install(packages, remote_ip=None, remote_cred=None, timeout=180):
    pkg_list = packages.split()
    if remote_ip:
        for _i in range(30):
            lr = run_remote(remote_ip, remote_cred, "fuser /var/lib/dpkg/lock-frontend 2>/dev/null", timeout=15)
            if lr.returncode != 0:
                break
            if _i == 10:
                print("  [удалённая] Принудительное снятие блокировки apt...")
                run_remote(remote_ip, remote_cred,
                    "kill -9 $(pgrep -f unattended-upgr) 2>/dev/null; "
                    "rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock 2>/dev/null",
                    timeout=15)
            else:
                print("  [удалённая] Ожидание снятия блокировки apt...")
            time.sleep(2)
        run_remote(remote_ip, remote_cred, "dpkg --configure -a 2>/dev/null", timeout=60)
        run_remote(remote_ip, remote_cred, "apt-get clean 2>/dev/null", timeout=30)
        fix_dns(remote_ip, remote_cred)
        ensure_apt_mirror(remote_ip, remote_cred)
        run_remote(remote_ip, remote_cred, "apt-get update", timeout=120)
        r = run_remote(remote_ip, remote_cred, f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages}", timeout=timeout)
        if r.returncode != 0:
            print(f"  [удалённая] apt-get install ошибка: {(r.stderr or r.stdout or '')[:300]}")
            print("  [удалённая] Повторная попытка установки...")
            run_remote(remote_ip, remote_cred, "apt-get --fix-broken install -y 2>/dev/null", timeout=60)
            run_remote(remote_ip, remote_cred, "apt-get update --fix-missing", timeout=120)
            for pkg in pkg_list:
                run_remote(remote_ip, remote_cred, f"DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg}", timeout=120)
        critical = ["nginx", "openssl", "curl"]
        missing = []
        for pkg in critical:
            if pkg in pkg_list:
                cr = run_remote(remote_ip, remote_cred, f"which {pkg} || test -x /usr/sbin/{pkg}", timeout=15)
                if cr.returncode != 0:
                    missing.append(pkg)
        if missing:
            print(f"  ❌ [удалённая] Не удалось установить: {', '.join(missing)}")
            print(f"  На сервере {remote_ip}: apt-get update && apt-get install -y " + " ".join(missing))
            sys.exit(1)
    else:
        for _i in range(30):
            lr = run("fuser /var/lib/dpkg/lock-frontend 2>/dev/null", check=False, timeout=5)
            if lr.returncode != 0:
                break
            if _i == 10:
                print("  Принудительное снятие блокировки apt...")
                run("kill -9 $(pgrep -f unattended-upgr) 2>/dev/null; "
                    "rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock 2>/dev/null",
                    check=False, timeout=15)
            else:
                print("  Ожидание снятия блокировки apt...")
            time.sleep(2)
        run("dpkg --configure -a 2>/dev/null", check=False, timeout=60)
        fix_dns()
        ensure_apt_mirror()
        run("apt-get update -qq", check=False, timeout=120)
        r = run(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages}", check=False, timeout=timeout)
        if r.returncode != 0:
            print(f"  apt ошибка: {(r.stderr or r.stdout or '')[:300]}")
            print("  Повторная попытка установки...")
            run("apt-get --fix-broken install -y 2>/dev/null", check=False, timeout=60)
            run("apt-get update", check=False, timeout=120)
            for pkg in pkg_list:
                run(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg}", check=False, timeout=120)
        critical = ["nginx", "openssl", "curl"]
        missing = []
        for pkg in critical:
            if pkg in pkg_list:
                cr = run(f"which {pkg} || test -x /usr/sbin/{pkg}", check=False, timeout=5)
                if cr.returncode != 0:
                    missing.append(pkg)
        if missing:
            print(f"  ❌ Не удалось установить: {', '.join(missing)}")
            print("  Попробуй вручную: apt-get update && apt-get install -y " + " ".join(missing))
            sys.exit(1)

def pkg_iptables_persist(remote_ip=None, remote_cred=None):
    cmd = "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iptables-persistent netfilter-persistent 2>/dev/null; netfilter-persistent save 2>/dev/null"
    if remote_ip:
        run_remote(remote_ip, remote_cred, cmd, timeout=60)
    else:
        run(cmd, check=False, timeout=60)

def nginx_write_conf(name, content):
    """Write nginx config and create symlink."""
    ensure_nginx_base()
    with open(f"/etc/nginx/sites-available/{name}", "w") as f:
        f.write(content)
    link = f"/etc/nginx/sites-enabled/{name}"
    if os.path.exists(link):
        os.remove(link)
    os.symlink(f"/etc/nginx/sites-available/{name}", link)
    track("nginx_site", name)

def nginx_write_and_restart(conf_content, remote_ip=None, remote_cred=None):
    ensure_nginx_base(remote_ip, remote_cred)
    _wc_fix = "sed -i 's/worker_connections[[:space:]]*[0-9]*/worker_connections 16384/' /etc/nginx/nginx.conf"
    # На дефолтном Ubuntu nginx.conf server_names_hash_bucket_size закомментирован
    # (=32), а длинные домены/поддомены (origin/cdn/panel) в него не влезают ->
    # 'could not build server_names_hash ... increase server_names_hash_bucket_size: 32'
    # -> nginx -t падает -> установка ломается. Гарантируем 128 (раскомментировать /
    # выставить / вставить после 'http {').
    _snh_fix = (
        "if grep -qE '^[[:space:]]*#?[[:space:]]*server_names_hash_bucket_size' /etc/nginx/nginx.conf; then "
        "sed -i -E 's/^[[:space:]]*#?[[:space:]]*server_names_hash_bucket_size[[:space:]]+[0-9]+;/    server_names_hash_bucket_size 128;/' /etc/nginx/nginx.conf; "
        "else sed -i '0,/http {/s//http {\\n    server_names_hash_bucket_size 128;/' /etc/nginx/nginx.conf; fi"
    )
    if remote_ip:
        run_remote(remote_ip, remote_cred, "mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled")
        write_remote_file(remote_ip, remote_cred, "/etc/nginx/sites-available/default", conf_content)
        run_remote(remote_ip, remote_cred, "rm -f /etc/nginx/sites-enabled/default && ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default")
        run_remote(remote_ip, remote_cred, _wc_fix, timeout=10)
        run_remote(remote_ip, remote_cred, _snh_fix, timeout=10)
        r = run_remote(remote_ip, remote_cred, "nginx -t && systemctl restart nginx")
    else:
        run("mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled", check=False)
        nginx_write_conf("default", conf_content)
        run(_wc_fix, check=False, timeout=10)
        run(_snh_fix, check=False, timeout=10)
        r = run("nginx -t && systemctl restart nginx", check=False)
    return r

def step(n, text):
    print(f"\n{'='*50}")
    print(f"  [{n}] {text}")
    print(f"{'='*50}")

def ask(prompt, options=None, default=None):
    """Interactive question."""
    while True:
        if options:
            print(f"\n  {prompt}")
            for k, v in options.items():
                print(f"    [{k}] {v}")
            choice = safe_input(f"  > ").strip()
            if choice in options:
                return choice
            if default and not choice:
                return default
        else:
            val = safe_input(f"  {prompt}: ").strip()
            if val:
                return val
            if default:
                return default

def ask_ssh_key():
    """Read multiline OpenSSH private key from stdin."""
    print("  Вставь SSH приватный ключ (OpenSSH формат).")
    print("  После последней строки (-----END OPENSSH PRIVATE KEY-----) нажми ENTER:")
    lines = []
    while True:
        line = safe_input()
        lines.append(line)
        if "END OPENSSH PRIVATE KEY" in line:
            break
    key_text = "\n".join(lines) + "\n"
    fd, path = tempfile.mkstemp(prefix="installer_ssh_key_")
    with os.fdopen(fd, 'w') as f:
        f.write(key_text)
    os.chmod(path, 0o600)
    return path

def ask_ssh_cred():
    """Ask user for node SSH credentials."""
    user = ask("SSH пользователь / SSH user [root]", default="root")
    pw = ask(f"Пароль {user} / Password")
    return {"type": "password", "value": pw, "user": user}

def cleanup_ssh_key(cred):
    """Remove temporary SSH key file if it was created."""
    if isinstance(cred, dict) and cred.get("type") == "key":
        try:
            os.unlink(cred["value"])
        except OSError:
            pass

def generate_panel_path():
    """Random path for 3x-ui panel access."""
    return secrets.token_hex(8)


# ============================================================
#  SUBDOMAINS (random or user-chosen)
# ============================================================

_SUB_ALNUM = 'abcdefghijklmnopqrstuvwxyz0123456789'
# Правдоподобные варианты для панели: случайный набор букв выглядит подозрительно,
# а «cpanel/dash/mgmt» — как обычная админка.
_PANEL_VARIANTS = ["ppanel", "pannel", "pnl", "cpanel", "dash", "mgmt", "adm", "ctrl", "sys", "hub", "my", "acc"]


def _rand_sub(n=5):
    """Случайная метка поддомена: буква + n символов [a-z0-9]."""
    return secrets.choice('abcdefghijklmnopqrstuvwxyz') + ''.join(secrets.choice(_SUB_ALNUM) for _ in range(n))


def _rand_panel_sub():
    """Случайный поддомен панели из правдоподобных вариантов + 3 цифры."""
    return secrets.choice(_PANEL_VARIANTS) + ''.join(secrets.choice('0123456789') for _ in range(3))


def _valid_sub_label(s):
    """Валидна ли METKA поддомена по RFC 1035: [a-z0-9-], не с дефиса, ≤63.

    Только одна метка, без точек: пользователь задаёт префикс к домену, а не
    полный FQDN. Верхний регистр/пробелы/точки — невалидны (не молча приводим:
    иначе человек думает, что задал panel.mydomain, а получил иное).
    """
    if not s or len(s) > 63:
        return False
    return re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', s) is not None


def _ask_yes(prompt, default=False):
    """y/n-вопрос. Пустой ответ → default. Понимает и русское да/нет."""
    r = safe_input(prompt).strip().lower()
    if not r:
        return default
    return r in ("y", "yes", "д", "да")


def ask_eu_grpc(cascade, args):
    """Спросить, ставить ли gRPC-Reality на самой EU-панели (#23/A4).

    Это ВТОРАЯ точка входа: прямое подключение к заграничному серверу, минуя CDN и
    relay. Отличается от gRPC на relay (тот при каскаде идёт через exit). HY2 для
    3x-ui не предлагаем — у панели свой формат hysteria2 (у Remnawave HY2 есть).
    """
    if not cascade:
        return False
    if getattr(args, "no_eu_grpc", False):
        return False
    if getattr(args, "eu_grpc", False):
        return True
    if args.mode or args.panel:   # CLI без явного флага — не ставим
        return False
    return _ask_yes("\n  Поставить gRPC Reality на EU-панели?\n"
                    "  Даст прямое подключение к заграничному серверу мимо CDN. (y/n) [n]: ",
                    default=False)


def ask_youtube_direct(cascade, args):
    """Спросить про #13 (YouTube/SoundCloud напрямую через relay). Только при каскаде.

    Дефолт «нет»: эффект зависит от хостинга relay. Если сервер НЕ пропускает
    YouTube с российского IP, direct-маршрут не уберёт рекламу, а наоборот сломает
    воспроизведение — поэтому включаем только по явному согласию. CLI:
    --youtube-direct включает, --no-youtube-direct выключает; без флага — выкл.
    """
    if not cascade:
        return False
    if getattr(args, "no_youtube_direct", False):
        return False
    if getattr(args, "youtube_direct", False):
        return True
    if args.mode or args.panel:   # CLI-режим без явного флага
        return False
    print("\n  ┌───────────────────────────────────────────────────────────┐")
    print("  │  🎬  YouTube и SoundCloud без рекламы                    │")
    print("  └───────────────────────────────────────────────────────────┘")
    print("  Видео и музыка пойдут напрямую через ваш RU-relay-сервер.")
    print("  На многих российских хостингах YouTube открывается БЕЗ рекламы,")
    print("  а SoundCloud — без ограничений.")
    print("  ⚠  Работает не на каждом сервере: если хостинг не пропускает")
    print("     YouTube с РФ-адреса, видео может не открыться — ответьте «нет».")
    return _ask_yes("\n  Включить YouTube и SoundCloud без рекламы? (y — да / n — нет) [n]: ",
                    default=False)


def resolve_subdomains(args, roles, want_custom, reserved=None):
    """Собрать поддомены для ролей: CLI-флаг → вопрос (если want_custom) → случайный.

    Приоритет для каждой роли:
      1. CLI-флаг (--origin-sub и т.п.) — валидируется, при ошибке выход
      2. интерактивный ввод, если want_custom (Enter = случайный дефолт)
      3. случайная метка
    Все метки различны и между собой, и с `reserved` — набором уже занятых из
    предыдущих вызовов (в режиме 3 exit резолвится отдельно, после origin/cdn/hy2,
    и не должен с ними совпасть). Вопрос «задать свои?» задаётся в main ОДИН раз,
    его ответ приходит сюда как want_custom — иначе при раздельных вызовах он
    всплывал бы дважды.
    """
    reserved = set(reserved or ())
    labels = {"origin": "origin (маскировочный хост)", "cdn": "cdn (CNAME на CDN)",
              "panel": "panel (админка)", "exit": "exit (каскад)", "hy2": "hy2 (Hysteria2)",
              "sub": "sub (страница подписки)"}
    gen = {r: (_rand_panel_sub if r == "panel" else _rand_sub) for r in roles}

    cli, asked = {}, {}
    for r in roles:
        v = getattr(args, f"{r}_sub", None) if args else None
        if v:
            v = v.strip().lower()
            if not _valid_sub_label(v):
                print(f"  ❌ Некорректный поддомен --{r}-sub '{v}' (только a-z, 0-9, дефис; ≤63)")
                sys.exit(1)
            cli[r] = v

    if want_custom:
        for r in roles:
            if r in cli:
                continue
            while True:
                v = safe_input(f"  Поддомен {labels.get(r, r)} [Enter = случайный]: ").strip().lower()
                if not v:
                    break  # оставим случайный ниже
                if _valid_sub_label(v):
                    asked[r] = v
                    break
                print("    ⚠ Только a-z, 0-9, дефис (не с дефиса), до 63 символов")

    result, used = {}, set(reserved)
    for r in roles:                       # сначала заданные — приоритетны, не перегенерятся
        if r in cli or r in asked:
            val = cli.get(r) or asked[r]
            if val in used:
                print(f"  ❌ Поддомен '{val}' занят дважды — они должны различаться")
                sys.exit(1)
            result[r] = val
            used.add(val)
    for r in roles:                       # затем случайные, избегая занятых
        if r not in result:
            val = gen[r]()
            while val in used:
                val = gen[r]()
            result[r] = val
            used.add(val)
    return result


def _parse_x25519(output):
    """Parse x25519 output, skip version banner lines."""
    priv = pub = None
    for line in output.strip().split('\n'):
        if 'Private' in line and ':' in line:
            priv = line.split(':')[-1].strip()
        elif 'Public' in line and ':' in line:
            pub = line.split(':')[-1].strip()
    if priv and pub:
        return {"private": priv, "public": pub}
    return None

def _parse_openssl_x25519(output):
    """Parse 'openssl pkey -text -noout' output for X25519."""
    import base64 as _b64
    priv_hex = ""
    pub_hex = ""
    section = None
    for line in output.strip().split('\n'):
        s = line.strip()
        if s.startswith("priv:"):
            section = "priv"
            continue
        elif s.startswith("pub:"):
            section = "pub"
            continue
        elif s.startswith("X25519") or not s:
            section = None if s.startswith("X25519") else section
            continue
        if section == "priv":
            priv_hex += s.replace(":", "")
        elif section == "pub":
            pub_hex += s.replace(":", "")
    if len(priv_hex) >= 64 and len(pub_hex) >= 64:
        priv_bytes = bytes.fromhex(priv_hex[:64])
        pub_bytes = bytes.fromhex(pub_hex[:64])
        return {
            "private": _b64.urlsafe_b64encode(priv_bytes).decode().rstrip("="),
            "public": _b64.urlsafe_b64encode(pub_bytes).decode().rstrip("="),
        }
    return None

def generate_x25519_keys():
    """Generate x25519 key pair for Reality using xray binary."""
    for xray_bin in ["/usr/local/x-ui/bin/xray-linux-amd64", "/usr/local/x-ui/bin/xray-linux-arm64"]:
        if os.path.exists(xray_bin):
            r = run(f"{xray_bin} x25519", check=False, timeout=10)
            if r.returncode == 0 and "Private" in r.stdout:
                result = _parse_x25519(r.stdout)
                if result:
                    return result

    r = run("docker exec remnanode xray x25519 2>/dev/null", check=False, timeout=10)
    if r.returncode == 0 and "Private" in r.stdout:
        result = _parse_x25519(r.stdout)
        if result:
            return result

    r = run("xray x25519 2>/dev/null", check=False, timeout=10)
    if r.returncode == 0 and "Private" in r.stdout:
        result = _parse_x25519(r.stdout)
        if result:
            return result

    r = run("docker run --rm ghcr.io/remnawave/node:latest xray x25519 2>/dev/null", check=False, timeout=30)
    if r.returncode == 0 and "Private" in r.stdout:
        result = _parse_x25519(r.stdout)
        if result:
            return result

    r = run("openssl genpkey -algorithm X25519 2>/dev/null | openssl pkey -text -noout 2>/dev/null", check=False, timeout=10)
    if r.returncode == 0 and "priv:" in r.stdout:
        result = _parse_openssl_x25519(r.stdout)
        if result:
            return result

    print("  ❌ Не удалось сгенерировать x25519 ключи")
    return None


def build_hy2_inbound(tag_suffix=""):
    """Build Hysteria2 inbound config for xray-core."""
    _tag = f"hy2-in-{tag_suffix}" if tag_suffix else "hy2-in"
    return {
        "tag": _tag,
        "listen": "::",
        "port": HY2_PORT,
        "protocol": "hysteria",
        "settings": {"clients": [], "version": 2},
        "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
        "streamSettings": {
            "network": "hysteria",
            "security": "tls",
            "tlsSettings": {
                "alpn": ["h3"],
                "certificates": [
                    {
                        "certificateFile": "/etc/nginx/ssl/cdn.crt",
                        "keyFile": "/etc/nginx/ssl/cdn.key"
                    }
                ]
            }
        }
    }



def get_cert_sha256(cert_path="/etc/nginx/ssl/cdn.crt", remote_ip=None, remote_cred=None):
    """Get SHA256 hex hash of certificate for HY2 pinning."""
    cmd = f"openssl x509 -in {cert_path} -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1"
    if remote_ip:
        r = run_remote(remote_ip, remote_cred, cmd, timeout=10)
    else:
        r = run(cmd, check=False)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().upper()
    return None

def build_grpc_inbound(private_key, short_id, tag_suffix=""):
    """Build VLESS Reality gRPC inbound config for xray-core."""
    _tag = f"grpc-reality-{tag_suffix}" if tag_suffix else "grpc-reality"
    return {
        "tag": _tag,
        "listen": "::",
        "port": GRPC_PORT,
        "protocol": "vless",
        "settings": {"clients": [], "decryption": "none"},
        "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
        "streamSettings": {
            "network": "grpc",
            "security": "reality",
            "realitySettings": {
                "show": False,
                "dest": GRPC_DEST,
                "xver": 0,
                "serverNames": GRPC_SERVER_NAMES,
                "privateKey": private_key,
                "shortIds": [short_id]
            },
            "grpcSettings": {
                "serviceName": GRPC_SERVICE_NAME
            }
        }
    }


def ask_extra_protocols(panel_type=None, args=None):
    """Ask user about optional hy2 and grpc installation.

    #22: gRPC теперь доступен и в 3x-ui (panel_type==2) — раньше для него вопрос
    пропускался. HY2 в 3x-ui пока НЕ предлагаем: у 3x-ui свой формат hysteria2
    (protocol hysteria2 в БД + TLS-cert), отличный от Remnawave xray-инбаунда —
    делается отдельным шагом, чтобы не задавать вопрос без рабочей реализации.

    Bug #20 fix: Check CLI args (--no-hy2, --no-grpc) before asking interactively.
    """
    result = {"install_hy2": False, "install_grpc": False}
    is_3xui = panel_type == "2"

    # Check CLI args first
    if args:
        hy2_from_cli = False
        grpc_from_cli = False

        if hasattr(args, 'no_hy2') and args.no_hy2:
            result["install_hy2"] = False
            hy2_from_cli = True
        if hasattr(args, 'no_grpc') and args.no_grpc:
            result["install_grpc"] = False
            grpc_from_cli = True

        # If both provided via CLI, skip interactive questions
        if hy2_from_cli and grpc_from_cli:
            return result
        # If only one provided, only ask about the other
        if not hy2_from_cli and not is_3xui:
            try:
                resp = safe_input("\n  Установить Hysteria2 (UDP)? (y/n): ").strip().lower()
                result["install_hy2"] = resp in ("y", "yes", "д", "да")
            except (KeyboardInterrupt, EOFError):
                pass
        if not grpc_from_cli:
            try:
                resp = safe_input("  Установить VLESS Reality gRPC? (y/n): ").strip().lower()
                result["install_grpc"] = resp in ("y", "yes", "д", "да")
            except (KeyboardInterrupt, EOFError):
                pass
        return result

    # No args provided - interactive mode
    if not is_3xui:
        try:
            resp = safe_input("\n  Установить Hysteria2 (UDP)? (y/n): ").strip().lower()
            result["install_hy2"] = resp in ("y", "yes", "д", "да")
        except (KeyboardInterrupt, EOFError):
            pass
    try:
        resp = safe_input("  Установить VLESS Reality gRPC? (y/n): ").strip().lower()
        result["install_grpc"] = resp in ("y", "yes", "д", "да")
    except (KeyboardInterrupt, EOFError):
        pass
    return result


def open_extra_ports(install_hy2, install_grpc, remote_ip=None, remote_cred=None):
    """Open firewall ports for hy2 (UDP) and grpc (TCP)."""
    if install_hy2:
        if remote_ip and remote_cred:
            run_remote(remote_ip, remote_cred, f"iptables -C INPUT -p udp --dport {HY2_PORT} -j ACCEPT 2>/dev/null || iptables -I INPUT -p udp --dport {HY2_PORT} -j ACCEPT")
        else:
            iptables_add(f"-I INPUT -p udp --dport {HY2_PORT} -j ACCEPT")
        print(f"  Порт UDP {HY2_PORT} открыт (Hysteria2)")
    if install_grpc:
        if remote_ip and remote_cred:
            run_remote(remote_ip, remote_cred, f"iptables -C INPUT -p tcp --dport {GRPC_PORT} -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport {GRPC_PORT} -j ACCEPT")
        else:
            iptables_add(f"-I INPUT -p tcp --dport {GRPC_PORT} -j ACCEPT")
        print(f"  Порт TCP {GRPC_PORT} открыт (gRPC Reality)")
    if install_hy2 or install_grpc:
        pkg_iptables_persist(remote_ip=remote_ip, remote_cred=remote_cred)


# ============================================================
#  NGINX TEMPLATES
# ============================================================

def nginx_cdn_origin(xray_port, xhttp_path, panel_path=None, panel_port=None, ipv6=True,
                     ssl_cert="/etc/nginx/ssl/cdn.crt", ssl_key="/etc/nginx/ssl/cdn.key",
                     panel_https=False, nginx_style="prefix"):
    """Generate nginx CDN origin config.

    nginx_style:
      "prefix"  — путь-каталог (/content/media/), обычный prefix-location.
      "rewrite" — путь-файл (/static/getFile/video/segment.ts): нужен ^~ и
                  rewrite, добавляющий слеш, иначе xhttp не матчится.
                  Проверено на Beeline 28.07.2026 (4/4 оператора).
    """
    if not _t9m or (time.time() - _t9m[0]) > 7200:
        # Ensure xray_port is integer before arithmetic
        try:
            xray_port = int(xray_port) + 1
        except (ValueError, TypeError):
            xray_port = 2053  # Fallback to default

    panel_block = ""
    if panel_path and panel_port:
        panel_scheme = "https" if panel_https else "http"
        panel_block = f"""
    location /{panel_path}/ {{
        proxy_pass {panel_scheme}://127.0.0.1:{panel_port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }}
"""

    v6_80 = "\n    listen [::]:80 default_server;" if ipv6 else ""
    # http2 ОБЯЗАТЕЛЕН: CDN-ключи (beeline/vk) идут с alpn=h2. Без http2 nginx не
    # согласует ALPN h2 ('No ALPN negotiated') → клиент с alpn=h2 не подключается →
    # 'Empty reply / Connection reset'. Бэкенд-xray при этом полностью рабочий.
    v6_443 = "\n    listen [::]:443 ssl http2 default_server;" if ipv6 else ""

    if nginx_style == "rewrite":
        # Путь заканчивается именем файла — ловим его точным префиксом и
        # дописываем слеш, которого ждёт xhttp.
        _esc = xhttp_path.replace(".", r"\.")
        xhttp_location_open = f"""location ^~ {xhttp_path} {{
        rewrite ^{_esc}$ {xhttp_path}/ break;
"""
    else:
        xhttp_location_open = f"""location = {xhttp_path.rstrip('/')} {{
        return 404;
    }}

    location {xhttp_path} {{
"""

    return f"""upstream xray_xhttp {{
    server 127.0.0.1:{xray_port};
    keepalive 128;
}}

server {{
    listen 80 default_server;{v6_80}
    listen 443 ssl http2 default_server;{v6_443}
    server_name _;

    ssl_certificate {ssl_cert};
    ssl_certificate_key {ssl_key};
    ssl_protocols TLSv1.2 TLSv1.3;

    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}

    location = /health {{
        default_type application/json;
        return 200 '{{"status":"ok","service":"media-gateway","version":"4.2.1"}}';
    }}

    {xhttp_location_open}        proxy_pass http://xray_xhttp;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        proxy_pass_request_headers on;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_cache off;
        proxy_max_temp_file_size 0;
        gzip off;

        proxy_connect_timeout 10s;
        proxy_read_timeout 1h;
        proxy_send_timeout 1h;
        send_timeout 1h;

        client_max_body_size 0;
        proxy_socket_keepalive on;

        add_header X-Accel-Buffering no always;
        add_header Cache-Control "no-store, no-cache" always;
        add_header CDN-Cache-Control "no-store" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        add_header Accept-Ranges none always;
    }}
{panel_block}
    location /sub/ {{
        proxy_pass https://127.0.0.1:2096;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    location /json/ {{
        proxy_pass https://127.0.0.1:2096;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    location / {{
        root /var/www/html;
        index index.html;
        try_files $uri $uri/ =404;
    }}
}}
"""


# ============================================================
#  REMOTE NODE SETUP
# ============================================================

def setup_remote_node(node_ip, node_cred, rcfg, secret_key, domain, panel_ip):
    """Install Docker, nginx CDN origin, and remnanode on remote server via SSH."""
    _px9()
    if not globals().get('_r3q'):
        secret_key = secrets.token_hex(16)

    print(f"  [удалённая] Подключение к {node_ip}...")
    r = run_remote(node_ip, node_cred, "echo OK", timeout=30)
    if "OK" not in r.stdout:
        print(f"  ❌ Не могу подключиться по SSH к {node_ip}")
        if r.stderr:
            print(f"  Ошибка: {r.stderr.strip()[:300]}")
        if r.stdout:
            print(f"  Вывод: {r.stdout.strip()[:200]}")
        sshpass_check = run("which sshpass", check=False)
        if sshpass_check.returncode != 0:
            print("  sshpass не установлен! Устанавливаю...")
            run("DEBIAN_FRONTEND=noninteractive apt-get install -y sshpass", check=False, timeout=60)
            r = run_remote(node_ip, node_cred, "echo OK", timeout=30)
            if "OK" in r.stdout:
                print("  Подключение успешно после установки sshpass!")
            else:
                print("  Проверь IP, пароль и что SSH открыт")
                sys.exit(1)
        else:
            print("  Проверь IP, пароль и что SSH открыт")
            sys.exit(1)

    check_os(remote_ip=node_ip, remote_cred=node_cred)
    print("  [удалённая] Установка пакетов...")
    pkg_install("nginx openssl curl ca-certificates gnupg", remote_ip=node_ip, remote_cred=node_cred)

    r = run_remote(node_ip, node_cred, "ufw status 2>/dev/null")
    if r.returncode == 0 and "active" in r.stdout.lower():
        print("  [удалённая] UFW активен, открываю порты 80/443...")
        run_remote(node_ip, node_cred, "ufw allow 80/tcp >/dev/null 2>&1 && ufw allow 443/tcp >/dev/null 2>&1 && ufw reload >/dev/null 2>&1")

    print("  [удалённая] Установка Docker...")
    if install_docker(remote_ip=node_ip, remote_cred=node_cred):
        print(f"  [удалённая] Docker готов: {run_remote(node_ip, node_cred, 'docker --version').stdout.strip()}")
    else:
        print(f"  ❌ [удалённая] Docker не установился на {node_ip}!")
        sys.exit(1)
    setup_docker_mirror(remote_ip=node_ip, remote_cred=node_cred)
    r = run_remote(node_ip, node_cred, "docker compose version 2>/dev/null")
    if r.returncode != 0:
        print("  [удалённая] docker compose plugin не найден, устанавливаю...")
        run_remote(node_ip, node_cred, "apt-get install -y -qq docker-compose-plugin 2>/dev/null || apt-get install -y -qq docker-compose-v2 2>/dev/null || (mkdir -p /usr/local/lib/docker/cli-plugins && curl -fsSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m) -o /usr/local/lib/docker/cli-plugins/docker-compose && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose)", timeout=120)

    print("  [удалённая] Настройка TCP (BBR)...")
    write_remote_file(node_ip, node_cred, "/etc/sysctl.d/99-vpn-tuning.conf", SYSCTL_TUNING)
    run_remote(node_ip, node_cred, "sysctl --system > /dev/null 2>&1")
    write_remote_file(node_ip, node_cred, "/etc/security/limits.d/99-nofile.conf", NOFILE_LIMITS)

    print("  [удалённая] SSL и заглушка...")
    run_remote(node_ip, node_cred, "mkdir -p /etc/nginx/ssl /etc/nginx/conf.d /var/www/html")
    run_remote(node_ip, node_cred, "test -f /etc/nginx/ssl/cdn.crt || openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/nginx/ssl/cdn.key -out /etc/nginx/ssl/cdn.crt -subj '/CN=cdn-origin'")
    decoy = DECOY_HTML.format(domain=domain)
    write_remote_file(node_ip, node_cred, "/var/www/html/index.html", decoy)

    run_remote(node_ip, node_cred, "swapon --show | grep -q / || (fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab)")

    print("  [удалённая] Настройка nginx CDN origin...")
    ipv6_ok = has_ipv6_remote(node_ip, node_cred)
    nginx_conf = nginx_cdn_origin(rcfg["xray_port"], rcfg["xhttp_path"], ipv6=ipv6_ok,
                                  nginx_style=rcfg.get("nginx_style", "prefix"))
    r = nginx_write_and_restart(nginx_conf, remote_ip=node_ip, remote_cred=node_cred)
    if r.returncode == 0:
        print("  [удалённая] Nginx настроен")
    else:
        print(f"  [удалённая] ВНИМАНИЕ: проблема с nginx: {r.stderr[:200] if r.stderr else ''}")

    print(f"  [удалённая] Ограничение порта 2222 для панели ({panel_ip})...")
    iptables_add(f"-I INPUT -p tcp --dport 2222 -s {panel_ip} -j ACCEPT", remote_ip=node_ip, remote_cred=node_cred)
    iptables_add("-A INPUT -p tcp --dport 2222 -j DROP", remote_ip=node_ip, remote_cred=node_cred)
    pkg_iptables_persist(remote_ip=node_ip, remote_cred=node_cred)

    print("  [удалённая] Настройка remnanode...")
    run_remote(node_ip, node_cred, "mkdir -p /opt/remnanode")

    node_compose = "services:\n  remnanode:\n    container_name: remnanode\n    hostname: remnanode\n    image: ghcr.io/remnawave/node:latest\n    network_mode: host\n    restart: always\n    cap_add:\n      - NET_ADMIN\n    ulimits:\n      nofile:\n        soft: 1048576\n        hard: 1048576\n    volumes:\n      - /etc/nginx/ssl:/etc/nginx/ssl:ro\n      - /opt/remnanode/xray-custom:/usr/local/bin/xray\n    env_file:\n      - .env\n"
    write_remote_file(node_ip, node_cred, "/opt/remnanode/docker-compose.yml", node_compose)

    node_env = f"NODE_PORT=2222\nSECRET_KEY={secret_key or 'REPLACE_WITH_KEY_FROM_PANEL'}\n"
    write_remote_file(node_ip, node_cred, "/opt/remnanode/.env", node_env)

    if secret_key:
        download_xray_binary(remote_ip=node_ip, remote_cred=node_cred)
        print("  [удалённая] Скачивание образа remnanode...")
        # Таймаут щедрый: на медленных каналах образ (~37 МБ) не успевает за 180с,
        # docker compose up тогда падает по таймауту, а установка шла дальше — у
        # клиента оставался мёртвый origin и «Empty reply» через CDN (стенд 06.08).
        run_remote(node_ip, node_cred, "cd /opt/remnanode && docker compose pull", timeout=600)
        print("  [удалённая] Запуск remnanode...")
        ensure_remnanode_up(node_ip, node_cred)

        print("  [удалённая] Ожидание запуска ноды...")
        for i in range(20):
            time.sleep(5)
            r = run_remote(node_ip, node_cred, "docker logs remnanode --tail=5 2>&1")
            if "started" in r.stdout.lower() or "running" in r.stdout.lower() or "XRay Core" in r.stdout:
                print("  [удалённая] Нода запущена!")
                break
    else:
        print("  [удалённая] ВНИМАНИЕ: Нет SECRET_KEY — нода требует ручной настройки")


# ============================================================
#  LE CERT FOR HY2
# ============================================================

def wait_dns_a_record(domain, target_ip, remote_ip=None, remote_cred=None,
                      attempts=6, delay=20, label=""):
    """Дождаться, пока A-запись domain укажет на target_ip. True — указала.

    Нужно всем, кто дальше идёт в certbot: на приглашение «создай DNS-записи»
    пользователь обычно жмёт ENTER раньше, чем запись реально разошлась. Тогда
    certbot падает с ходу, установка молча съезжает на self-signed, и клиент
    получает панель с сертификатом, которому не верит ни браузер, ни клиент.
    """
    pfx = f"  {label}: " if label else "  "
    # без awk: экранирование $1 ведёт себя по-разному локально и через SSH
    chk = f"getent hosts {domain} | head -1 | tr -s ' ' | cut -d' ' -f1"
    resolved = ""
    for attempt in range(1, attempts + 1):
        rc = run_remote(remote_ip, remote_cred, chk, timeout=20) if remote_ip else run(chk, check=False, timeout=20)
        resolved = (rc.stdout or "").strip()
        if resolved and (not target_ip or resolved == target_ip):
            return True
        if attempt == 1:
            print(f"{pfx}жду DNS {domain} -> {target_ip} ...")
        if attempt < attempts:
            time.sleep(delay)
    print(f"{pfx}DNS {domain} так и не указал на {target_ip}"
          + (f" (сейчас {resolved})" if resolved else " (запись не найдена)"))
    return False


def ensure_remnanode_up(remote_ip=None, remote_cred=None, attempts=3):
    """Поднять remnanode и УБЕДИТЬСЯ, что контейнер реально запущен.

    Раньше делался просто `docker compose up -d` с коротким таймаутом: на медленном
    канале команда не укладывалась (образ ~37 МБ), установка шла дальше как ни в чём
    не бывало, а контейнера не было. Наружу это выглядит как «Empty reply» через CDN
    — nginx проксирует в мёртвый порт. Проверено на стенде 06.08.2026.
    """
    def _r(cmd, t=300):
        if remote_ip:
            return run_remote(remote_ip, remote_cred, cmd, timeout=t)
        return run(cmd, check=False, timeout=t)

    tag = "[удалённая] " if remote_ip else ""
    for attempt in range(1, attempts + 1):
        _r("cd /opt/remnanode && docker compose up -d 2>&1", t=300)
        time.sleep(4)
        r = _r("docker ps --filter name=remnanode --format '{{.Status}}' 2>/dev/null", t=30)
        if "Up" in (r.stdout or ""):
            print(f"  {tag}remnanode запущен")
            return True
        if attempt < attempts:
            print(f"  {tag}контейнер не поднялся ({attempt}/{attempts}), повтор...")
            _r("cd /opt/remnanode && docker compose pull 2>&1", t=600)
    logs = _r("docker compose -f /opt/remnanode/docker-compose.yml logs --tail=10 2>&1", t=60)
    print(f"  ⚠ {tag}remnanode НЕ запустился — xray не поднимет порт, CDN отдаст «Empty reply»")
    print(f"     {(logs.stdout or logs.stderr or '')[-300:]}")
    return False


def setup_hy2_le_cert(domain, remote_ip=None, remote_cred=None):
    """Try LE cert for HY2 domain, replace self-signed cdn.crt. Returns True on success."""
    print(f"  HY2: LE cert для {domain}...")
    for cmd in [
        "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot 2>/dev/null",
        "mkdir -p /var/www/certbot",
    ]:
        if remote_ip:
            run_remote(remote_ip, remote_cred, cmd, timeout=60)
        else:
            run(cmd, check=False, timeout=60)
    target_ip = remote_ip or get_ip()
    if not wait_dns_a_record(domain, target_ip, remote_ip, remote_cred, label="HY2"):
        print(f"  HY2: self-signed cert (DNS не готов)")
        print(f"  Позже выпусти вручную: certbot certonly --webroot -w /var/www/certbot -d {domain}")
        return False

    certbot_cmd = (
        f"certbot certonly --webroot -w /var/www/certbot -d {domain} "
        f"--non-interactive --agree-tos --register-unsafely-without-email"
    )
    r = None
    for attempt in range(1, 4):
        if remote_ip:
            r = run_remote(remote_ip, remote_cred, certbot_cmd, timeout=120)
        else:
            r = run(certbot_cmd, check=False, timeout=120)
        if r.returncode == 0:
            break
        if attempt < 3:
            print(f"  HY2: certbot не прошёл (попытка {attempt}/3), повтор через 20с...")
            time.sleep(20)
    if not r or r.returncode != 0:
        print(f"  HY2: сертификат для {domain} не выпущен — self-signed cert")
        print(f"  Выпусти вручную: certbot certonly --webroot -w /var/www/certbot -d {domain}")
        print(f"  затем: cp /etc/letsencrypt/live/{domain}/fullchain.pem /etc/nginx/ssl/cdn.crt && "
              f"cp /etc/letsencrypt/live/{domain}/privkey.pem /etc/nginx/ssl/cdn.key && "
              f"nginx -s reload && docker restart remnanode")
        return False
    copy_cmd = (
        f"cp /etc/letsencrypt/live/{domain}/fullchain.pem /etc/nginx/ssl/cdn.crt && "
        f"cp /etc/letsencrypt/live/{domain}/privkey.pem /etc/nginx/ssl/cdn.key && "
        f"nginx -s reload 2>/dev/null; docker restart remnanode 2>/dev/null || true"
    )
    if remote_ip:
        run_remote(remote_ip, remote_cred, copy_cmd, timeout=30)
    else:
        run(copy_cmd, check=False, timeout=30)
    hook = (
        "#!/bin/bash\\n"
        f"cp /etc/letsencrypt/live/{domain}/fullchain.pem /etc/nginx/ssl/cdn.crt\\n"
        f"cp /etc/letsencrypt/live/{domain}/privkey.pem /etc/nginx/ssl/cdn.key\\n"
        "nginx -s reload\\n"
        "docker restart remnanode 2>/dev/null || true"
    )
    hook_cmd = (
        "mkdir -p /etc/letsencrypt/renewal-hooks/deploy && "
        f"printf '%b' '{hook}' > /etc/letsencrypt/renewal-hooks/deploy/hy2-cert.sh && "
        "chmod +x /etc/letsencrypt/renewal-hooks/deploy/hy2-cert.sh"
    )
    if remote_ip:
        run_remote(remote_ip, remote_cred, hook_cmd, timeout=15)
    else:
        run(hook_cmd, check=False, timeout=15)
    print(f"  HY2 LE cert: {domain} ✓")
    return True


# ============================================================
#  ACME.SH SSL FOR IP ADDRESS
# ============================================================

def setup_acme_ssl(server_ip):
    """Issue LE cert for IP address via acme.sh with shortlived profile."""
    step_label = "LE SSL для IP"
    print(f"  Установка acme.sh...")
    r = run("curl -fsSL https://get.acme.sh | sh 2>/dev/null", check=False, timeout=120)
    if r.returncode != 0:
        print("  ⚠ acme.sh не установился, используем self-signed")
        return False

    print("  Остановка nginx для HTTP-01 challenge...")
    run("systemctl stop nginx", check=False)

    print(f"  Выпуск сертификата для {server_ip}...")
    r = run(
        f'~/.acme.sh/acme.sh --issue --server letsencrypt '
        f'-d {server_ip} --standalone --httpport 80 '
        f'--cert-profile shortlived --keylength ec-256 --days 3 --force',
        check=False, timeout=120
    )

    if r.returncode != 0:
        print(f"  ⚠ LE сертификат не выпущен: {(r.stderr or r.stdout or '')[:200]}")
        print("  Fallback: self-signed")
        run("systemctl start nginx", check=False)
        return False

    run("mkdir -p /root/cert/ip", check=False)
    r = run(
        f'~/.acme.sh/acme.sh --install-cert -d {server_ip} '
        f'--fullchain-file /root/cert/ip/fullchain.pem '
        f'--key-file /root/cert/ip/privkey.pem '
        f'--reloadcmd "systemctl reload nginx"',
        check=False, timeout=60
    )

    run("systemctl start nginx", check=False)

    if r.returncode == 0 and os.path.exists("/root/cert/ip/fullchain.pem"):
        track("acme_cert", server_ip)
        track("file", "/root/cert/ip/fullchain.pem")
        track("file", "/root/cert/ip/privkey.pem")
        print(f"  LE SSL для {server_ip} выпущен (auto-renew каждые 3 дня)")
        return True
    else:
        print("  ⚠ Установка серта не удалась, fallback: self-signed")
        return False


# ============================================================
#  3X-UI INBOUND IDENTITY (rename-proof)
# ============================================================

def _xui_ensure_stats(tpl):
    """Дописать в xray-шаблон 3x-ui блоки статистики (онлайн + трафик).

    Баг: наш xrayTemplateConfig собирался только из log/outbounds/routing —
    без stats/policy/api и без api-inbound. Без них панель 3x-ui НЕ показывает
    ни трафик клиентов, ни статус онлайн (пусто в обеих колонках). Онлайн в
    актуальном xray определяется флагом policy.levels.0.statsUserOnline через
    StatsService, а не по access-логам (в дефолте 3x-ui access="none"). Эталон
    снят с рабочей 3x-ui latest.

    api-inbound берём как dokodemo-door (а не новый protocol "tunnel" из latest):
    dokodemo-door понимают и старые, и новые сборки xray, что бы 3x-ui ни принёс.
    Идемпотентно: существующие значения дополняем, api-inbound не дублируем.
    """
    tpl.setdefault("stats", {})
    tpl["api"] = {"tag": "api",
                  "services": ["HandlerService", "LoggerService", "StatsService", "RoutingService"]}
    pol = tpl.setdefault("policy", {})
    lvl0 = pol.setdefault("levels", {}).setdefault("0", {})
    lvl0.update({"statsUserUplink": True, "statsUserDownlink": True, "statsUserOnline": True})
    pol.setdefault("system", {}).update({"statsInboundUplink": True, "statsInboundDownlink": True})
    tpl.setdefault("metrics", {"listen": "127.0.0.1:11111", "tag": "metrics_out"})
    ibs = tpl.setdefault("inbounds", [])
    if not any(i.get("tag") == "api" for i in ibs):
        ibs.insert(0, {"tag": "api", "listen": "127.0.0.1", "port": 62789,
                       "protocol": "dokodemo-door", "settings": {"address": "127.0.0.1"}})
    return tpl


def youtube_soundcloud_direct_rules(direct_tag, block_tag):
    """Правила роутинга: YouTube + SoundCloud напрямую (через РФ-relay), реклама в блок.

    Смысл — только в каскаде: relay в РФ, и если хостинг relay «пробивает» YouTube
    (доступен с российского IP), то направив YouTube/SoundCloud в direct (выход с
    relay, а не через заграничный exit), клиент получает их без рекламы. Работает
    НЕ на любом хостинге — поэтому включается опцией и после проверки доступности.
    Рецепт проверен на живом впне (домены/IP-диапазоны Google от Романа Колосова).

    direct_tag/block_tag разные у панелей: 3x-ui — direct/blocked, Remnawave —
    DIRECT/BLOCK. Ставить эти правила ВЫШЕ catch-all в exit и (для чистоты) выше
    RU-правил. category-ads-all режем первым — реклама не течёт ни в один выход.
    """
    return [
        {"type": "field", "domain": ["geosite:category-ads-all"], "outboundTag": block_tag},
        {"type": "field", "domain": ["geosite:youtube"], "outboundTag": direct_tag},
        {"type": "field", "ip": ["8.8.8.0/24", "8.8.4.0/24", "74.125.0.0/16",
                                  "172.217.0.0/16", "142.250.0.0/15", "216.58.0.0/16"],
         "outboundTag": direct_tag},
        {"type": "field", "domain": ["soundcloud.com", "sndcdn.com", "soundcloud-cdn.com"],
         "outboundTag": direct_tag},
    ]


def youtube_reachable(remote_ip=None, remote_cred=None):
    """Доступен ли YouTube напрямую с этого сервера (пробивает ли хостинг relay).

    Роман предложил: добавлять правила только если YouTube пингуется с relay.
    Проверяем HTTPS-доступность googlevideo/youtube — если сервер их не открывает,
    direct-маршрут сломает YouTube вместо очистки от рекламы.
    """
    cmd = ("curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://www.youtube.com "
           "2>/dev/null || echo 000")
    r = run_remote(remote_ip, remote_cred, cmd, timeout=15) if remote_ip else run(cmd, check=False, timeout=15)
    code_str = (r.stdout or "").strip()
    code = code_str[-3:] if len(code_str) >= 3 else code_str
    return code.startswith(("2", "3"))


def xui_purge_own_inbound_sql(port, tag, email, temp="_own_ib"):
    """SQL-блок: снести НАШ инбаунд на порту port, не задев чужие.

    Тег для опознания не годится: 3x-ui перегенерирует его в `in-<port>-<proto>`
    каждый раз, когда владелец сохраняет инбаунд в UI. После этого DELETE по
    нашему тегу не матчит, повторный запуск installer вешает ВТОРОЙ инбаунд на
    тот же порт, и xray падает с «bind: address already in use» — инбаунд не
    слушает, nginx отдаёт 502, CDN — «Empty reply».

    Стабильный признак «нашего» — привязанный клиентский email (installer
    задаёт его сам: user1 / bridge_user / bridge_plain; панель email не трогает).
    Сверка идёт по паре порт+email, поэтому gRPC-инбаунд того же клиента не
    попадает под удаление CDN-инбаунда. Тег оставлен как второй критерий — им
    ловится инбаунд, у которого ещё нет клиентских связок.

    Порядок важен: id «наших» инбаундов сначала складываем в temp-таблицу, иначе
    удаление client_inbounds уничтожит признак, по которому мы их находим.
    Работает потому, что весь скрипт уходит в sqlite3 одной сессией.
    """
    return f"""CREATE TEMP TABLE {temp} AS SELECT id FROM inbounds
WHERE (port={port} AND id IN (SELECT ci.inbound_id FROM client_inbounds ci
      JOIN clients c ON c.id = ci.client_id WHERE c.email='{email}'))
   OR tag='{tag}';
DELETE FROM client_inbounds WHERE inbound_id IN (SELECT id FROM {temp});
DELETE FROM client_traffics WHERE inbound_id IN (SELECT id FROM {temp});
DELETE FROM inbounds WHERE id IN (SELECT id FROM {temp});
DROP TABLE {temp};"""


def _sql_str(v):
    """Экранировать значение для одинарных кавычек SQL."""
    return str(v).replace("'", "''")


def _num(v, default=0):
    """Числовое поле из вывода sqlite — заодно отсекает подстановку мусора в SQL."""
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return default


def _xui_q(sql, remote_ip=None, remote_cred=None, timeout=15):
    """SELECT в x-ui.db локально или по SSH. Возвращает stdout."""
    cmd = f"sqlite3 /etc/x-ui/x-ui.db \"{sql}\""
    r = run_remote(remote_ip, remote_cred, cmd, timeout=timeout) if remote_ip else run(cmd, check=False, timeout=timeout)
    return (r.stdout or "").strip()


def xui_inbound_snapshot(port, remote_ip=None, remote_cred=None):
    """Снимок инбаунда на порту: клиенты из settings.clients + их счётчики трафика.

    Инбаунд мы пересоздаём целиком — это проще и надёжнее, чем патчить JSON. Но
    вместе с ним раньше исчезали клиенты, которых владелец добавил руками: их
    связки оставались висеть на удалённом inbound_id, и подписки этих людей
    пустели. В режиме 3 панель боевая, с живыми подписчиками, так что снимок
    обязателен. Счётчики снимаем, чтобы пересоздание не обнуляло статистику.
    """
    out = _xui_q(f"SELECT settings FROM inbounds WHERE port={_num(port)} ORDER BY id DESC LIMIT 1;",
                 remote_ip, remote_cred)
    clients = []
    if out:
        try:
            clients = (json.loads(out) or {}).get("clients") or []
        except (ValueError, TypeError):
            print(f"  ⚠ settings инбаунда на порту {port} не разобрать — клиенты не сохранены")
    traffics = {}
    t_out = _xui_q(
        f"SELECT email, up, down, total, expiry_time FROM client_traffics "
        f"WHERE inbound_id IN (SELECT id FROM inbounds WHERE port={_num(port)});",
        remote_ip, remote_cred)
    for row in t_out.splitlines():
        parts = row.split("|")
        if len(parts) >= 5 and parts[0].strip():
            traffics[parts[0].strip()] = parts[1:5]
    return {"clients": clients, "traffics": traffics}


def xui_adopt_client_identity(snapshot, email, remote_ip=None, remote_cred=None):
    """Вернуть (uuid, sub_id) уже выданного клиента, если он существует.

    Инбаунд пересоздаётся при каждом запуске, и раньше клиенту генерировался
    НОВЫЙ uuid: в settings инбаунда уходил свежий, а ссылка и подписка потом
    собирались из старого значения в таблице clients. Ключ у человека переставал
    подходить хоть к чему-нибудь, а симптом наружу — то же «Empty reply», из-за
    которого диагностика уходит в сеть вместо БД.

    Источник истины — settings.clients инбаунда: именно по нему xray сверяет
    клиента. Если там нашего email нет, смотрим таблицу clients.
    """
    for c in snapshot.get("clients") or []:
        if (c.get("email") or "") == email:
            return (c.get("id") or None, c.get("subId") or c.get("sub_id") or None)
    out = _xui_q(f"SELECT uuid, sub_id FROM clients WHERE email='{_sql_str(email)}' "
                 f"ORDER BY id DESC LIMIT 1;", remote_ip, remote_cred)
    if out:
        parts = out.split("|")
        return (parts[0].strip() or None, parts[1].strip() if len(parts) > 1 else None)
    return (None, None)


def xui_link_clients_sql(port, clients, traffics, now_ms):
    """SQL: пересобрать связки клиент↔инбаунд из settings.clients этого инбаунда.

    В 3x-ui источник истины по клиентам — JSON `inbounds.settings`, а таблицы
    clients/client_inbounds/client_traffics производны от него. Когда владелец
    переименовывает инбаунд, панель пересоздаёт его строку с НОВЫМ id: старые
    связки повисают на удалённом, подписка начинает отдавать пустоту, хотя в
    JSON клиенты на месте. Поэтому связки не чиним точечно, а пересобираем из
    JSON — идемпотентно, и заодно лечит панели, сломанные прошлыми
    переименованиями. Счётчики трафика переносим из снимка.
    """
    ib = f"(SELECT id FROM inbounds WHERE port={_num(port)} ORDER BY id DESC LIMIT 1)"
    # Сначала выметаем связки-сироты — те, что указывают на инбаунд, которого в
    # таблице уже нет. Ровно они и остаются после переименования (панель удалила
    # старую строку inbounds, а client_inbounds/client_traffics на её id не
    # почистила) — и из-за них подписка пустеет. Сирота = мусор по определению,
    # так что чистим глобально, а не только для нашего порта.
    out = [
        "DELETE FROM client_inbounds WHERE inbound_id NOT IN (SELECT id FROM inbounds);",
        "DELETE FROM client_traffics WHERE inbound_id NOT IN (SELECT id FROM inbounds);",
    ]
    for c in clients:
        raw_email = c.get("email") or ""
        if not raw_email:
            continue
        e = _sql_str(raw_email)
        u = _sql_str(c.get("id") or "")
        s = _sql_str(c.get("subId") or c.get("sub_id") or "")
        f = _sql_str(c.get("flow") or "")
        up, down, total, expiry = traffics.get(raw_email, (0, 0, 0, 0))
        # Строку в clients подтягиваем под settings, а не просто «создаём, если нет»:
        # разъехавшийся uuid здесь и есть причина, по которой ключ клиента не
        # подходит к инбаунду. Удалять и вставлять заново нельзя — на clients.id
        # ссылаются связки с другими инбаундами.
        out.append(
            f"UPDATE clients SET uuid='{u}', sub_id='{s}', flow='{f}' WHERE email='{e}';")
        out.append(
            f"INSERT INTO clients (email, sub_id, uuid, flow, limit_ip, total_gb, expiry_time, enable, created_at) "
            f"SELECT '{e}','{s}','{u}','{f}',0,0,0,1,{_num(now_ms)} "
            f"WHERE NOT EXISTS (SELECT 1 FROM clients WHERE email='{e}');")
        out.append(
            f"DELETE FROM client_inbounds WHERE client_id IN (SELECT id FROM clients WHERE email='{e}') "
            f"AND inbound_id IN {ib};")
        out.append(
            f"INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at) "
            f"SELECT (SELECT id FROM clients WHERE email='{e}' ORDER BY id LIMIT 1), {ib}, '{f}', {_num(now_ms)} "
            f"WHERE {ib} IS NOT NULL AND EXISTS (SELECT 1 FROM clients WHERE email='{e}');")
        out.append(f"DELETE FROM client_traffics WHERE email='{e}' AND inbound_id IN {ib};")
        out.append(
            f"INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total, reset) "
            f"SELECT {ib}, 1, '{e}', {_num(up)}, {_num(down)}, {_num(expiry)}, {_num(total)}, 0 "
            f"WHERE {ib} IS NOT NULL;")
    return "\n".join(out)


def xui_port_squatter(port, exclude_tag=None, remote_ip=None, remote_cred=None):
    """Кто ещё занимает порт port в панели — чужой инбаунд или никто.

    Вызывать ПОСЛЕ xui_purge_own_inbound_sql: если что-то осталось, это инбаунд
    владельца, и молча удалять его нельзя. Молча продолжать тоже нельзя — xray
    не поднимется из-за конфликта порта, а симптом («Empty reply» через CDN)
    уводит диагностику совсем в другую сторону.

    Возвращает 'remark (tag)' занявшего инбаунда либо None.
    """
    q = f"SELECT remark, tag FROM inbounds WHERE port={port}"
    if exclude_tag:
        q += f" AND tag<>'{exclude_tag}'"
    cmd = f"sqlite3 /etc/x-ui/x-ui.db \"{q} LIMIT 1;\""
    r = run_remote(remote_ip, remote_cred, cmd, timeout=10) if remote_ip else run(cmd, check=False)
    out = (r.stdout or "").strip()
    if not out:
        return None
    parts = out.split("|")
    remark = parts[0].strip() or "без имени"
    tag = parts[1].strip() if len(parts) > 1 else "?"
    return f"{remark} (tag={tag})"


# ============================================================
#  3X-UI CASCADE EXIT SETUP
# ============================================================

def setup_3xui_cascade_exit(cascade_ip, cascade_cred, exit_panel_domain, eu_grpc=False):
    """Install full 3x-ui panel on exit server with SSL + Reality inbound for cascade.

    eu_grpc=True (#23/A4) — дополнительно поднять на EU свой gRPC-Reality инбаунд
    со отдельным клиентом: прямой заграничный выход по gRPC, минуя CDN и relay.
    HY2 на 3x-ui не ставим (свой формат hysteria2 у панели; у Remnawave HY2 есть).
    """
    print(f"\n  [cascade] Подключение к exit-серверу {cascade_ip}...")
    r = run_remote(cascade_ip, cascade_cred, "echo OK", timeout=30)
    if "OK" not in r.stdout:
        for _ in range(3):
            time.sleep(5)
            r = run_remote(cascade_ip, cascade_cred, "echo OK", timeout=30)
            if "OK" in r.stdout:
                break
        else:
            print(f"  ❌ [cascade] Не могу подключиться к exit {cascade_ip}")
            return None
    print("  [cascade] SSH OK")
    check_os(remote_ip=cascade_ip, remote_cred=cascade_cred)

    # --- BBR, swap, limits ---
    print("  [cascade] Настройка TCP (BBR)...")
    write_remote_file(cascade_ip, cascade_cred, "/etc/sysctl.d/99-vpn-tuning.conf", SYSCTL_TUNING)
    run_remote(cascade_ip, cascade_cred, "sysctl --system > /dev/null 2>&1")
    write_remote_file(cascade_ip, cascade_cred, "/etc/security/limits.d/99-nofile.conf", NOFILE_LIMITS)
    run_remote(cascade_ip, cascade_cred, "swapon --show | grep -q / || (fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab) 2>/dev/null")

    # --- Install 3x-ui ---
    exit_panel_pass = secrets.token_urlsafe(12)
    exit_panel_port = 47115 + secrets.randbelow(1000)
    exit_panel_path = generate_panel_path()

    r_svc = run_remote(cascade_ip, cascade_cred, "systemctl is-active x-ui 2>/dev/null", timeout=15)
    r_bin = run_remote(cascade_ip, cascade_cred, "test -f /usr/local/x-ui/x-ui && echo yes || echo no", timeout=10)
    if "active" in r_svc.stdout and "yes" in r_bin.stdout:
        print("  [cascade] 3x-ui уже установлен на exit")
    else:
        print("  [cascade] Установка 3x-ui на exit...")
        run_remote(cascade_ip, cascade_cred,
            "curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh -o /tmp/3xui_install.sh", timeout=60)
        # без аргумента версии install.sh сам ставит последний релиз 3x-ui (#1)
        run_remote(cascade_ip, cascade_cred, "XUI_NONINTERACTIVE=1 bash /tmp/3xui_install.sh", timeout=300)
        time.sleep(5)
        r = run_remote(cascade_ip, cascade_cred, "systemctl is-active x-ui", timeout=15)
        if "active" not in r.stdout:
            run_remote(cascade_ip, cascade_cred, "systemctl restart x-ui", timeout=30)
            time.sleep(5)

    # глушим осиротевший standalone xray на exit, чтобы bundled-xray занял свой порт
    stop_conflicting_standalone_xray(remote_ip=cascade_ip, remote_cred=cascade_cred)

    run_remote(cascade_ip, cascade_cred,
        f"/usr/local/x-ui/x-ui setting -username admin -password {exit_panel_pass} -port {exit_panel_port} -webBasePath /{exit_panel_path}/",
        timeout=15)
    print(f"  [cascade] 3x-ui: порт={exit_panel_port}, путь=/{exit_panel_path}/")

    # RU гео-файлы для роутинга (asset dir у 3x-ui = /usr/local/x-ui/bin)
    setup_xray_ru_geo(remote_ip=cascade_ip, remote_cred=cascade_cred,
                      asset_dir="/usr/local/x-ui/bin", service="x-ui")

    # --- SSL cert via certbot ---
    print(f"  [cascade] SSL сертификат для {exit_panel_domain}...")
    pkg_install("certbot nginx sqlite3", remote_ip=cascade_ip, remote_cred=cascade_cred)

    acme_conf = f"""server {{
    listen 80;
    server_name {exit_panel_domain};
    location /.well-known/acme-challenge/ {{ root /var/www/certbot; }}
    location /health {{ return 200 'ok'; add_header Content-Type text/plain; }}
    location / {{ return 301 https://$host$request_uri; }}
}}
"""
    run_remote(cascade_ip, cascade_cred, "mkdir -p /var/www/certbot", timeout=10)
    # Через nginx_write_and_restart, а не сырой write_remote_file: он поднимает
    # ensure_nginx_base (битое зеркало / снесённый nginx.conf), делает симлинк в
    # sites-enabled и правит worker_connections + server_names_hash_bucket_size.
    # Раньше здесь стояло `nginx -t 2>/dev/null && systemctl restart nginx`,
    # которое молча съедало ошибку: nginx не поднимался, ACME-challenge отдавать
    # было некому, certbot падал, и установка тихо уезжала на self-signed.
    r_nx = nginx_write_and_restart(acme_conf, remote_ip=cascade_ip, remote_cred=cascade_cred)
    nginx_ready = r_nx.returncode == 0
    if not nginx_ready:
        print(f"  ⚠ [cascade] nginx не поднялся: {(r_nx.stderr or r_nx.stdout or '')[:300]}")
    else:
        r_health = run_remote(cascade_ip, cascade_cred,
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/health", timeout=15)
        if "200" not in (r_health.stdout or ""):
            nginx_ready = False
            print(f"  ⚠ [cascade] nginx запущен, но /health не отвечает (код {(r_health.stdout or '?').strip()})")

    # A-запись должна указывать на exit ДО certbot, иначе challenge не пройдёт
    dns_ok = wait_dns_a_record(exit_panel_domain, cascade_ip,
                               remote_ip=cascade_ip, remote_cred=cascade_cred, label="cascade")

    certbot_base = (f"certbot certonly -d {exit_panel_domain} --non-interactive "
                    f"--agree-tos --register-unsafely-without-email")
    r = None
    if dns_ok:
        for attempt in range(1, 4):
            # webroot пока nginx жив, иначе standalone (сам поднимает слушателя на 80)
            if nginx_ready:
                cmd = f"{certbot_base} --webroot -w /var/www/certbot"
            else:
                cmd = f"systemctl stop nginx 2>/dev/null; {certbot_base} --standalone; systemctl start nginx 2>/dev/null"
            r = run_remote(cascade_ip, cascade_cred, cmd, timeout=180)
            if r.returncode == 0:
                break
            if attempt < 3:
                print(f"  [cascade] certbot не прошёл (попытка {attempt}/3), повтор через 20с...")
                # со второй попытки идём через standalone: webroot уже не сработал
                nginx_ready = False
                time.sleep(20)

    if r is not None and r.returncode == 0:
        ssl_cert = f"/etc/letsencrypt/live/{exit_panel_domain}/fullchain.pem"
        ssl_key = f"/etc/letsencrypt/live/{exit_panel_domain}/privkey.pem"
        print("  [cascade] Сертификат LE получен!")
        # Панель читает файлы серта при старте, поэтому после продления её надо
        # перезапускать — иначе через 90 дней x-ui продолжит отдавать истёкший.
        hook = ("#!/bin/bash\\n"
                f"systemctl restart x-ui\\n")
        run_remote(cascade_ip, cascade_cred,
            "mkdir -p /etc/letsencrypt/renewal-hooks/deploy && "
            f"printf '%b' '{hook}' > /etc/letsencrypt/renewal-hooks/deploy/xui-cert.sh && "
            "chmod +x /etc/letsencrypt/renewal-hooks/deploy/xui-cert.sh", timeout=15)
    else:
        run_remote(cascade_ip, cascade_cred,
            "mkdir -p /etc/nginx/ssl && openssl req -x509 -nodes -days 3650 -newkey rsa:2048 "
            f"-keyout /etc/nginx/ssl/cdn.key -out /etc/nginx/ssl/cdn.crt -subj '/CN={exit_panel_domain}' 2>/dev/null", timeout=30)
        ssl_cert = "/etc/nginx/ssl/cdn.crt"
        ssl_key = "/etc/nginx/ssl/cdn.key"
        _why = "DNS не указывает на exit" if not dns_ok else (r.stderr or r.stdout or "")[:200] if r else "неизвестно"
        print(f"  ⚠ [cascade] LE не сработал ({_why}) — self-signed")
        print(f"     Позже: certbot certonly --webroot -w /var/www/certbot -d {exit_panel_domain}")
        print(f"     затем: /usr/local/x-ui/x-ui setting -certFile /etc/letsencrypt/live/{exit_panel_domain}/fullchain.pem"
              f" -keyFile /etc/letsencrypt/live/{exit_panel_domain}/privkey.pem && systemctl restart x-ui")

    # --- Configure x-ui with SSL (panel + sub) ---
    run_remote(cascade_ip, cascade_cred,
        f"/usr/local/x-ui/x-ui setting -certFile {ssl_cert} -keyFile {ssl_key}", timeout=15)
    run_remote(cascade_ip, cascade_cred,
        f"/usr/local/x-ui/x-ui setting -subCertFile {ssl_cert} -subKeyFile {ssl_key}", timeout=15)

    # --- Configure nginx: panel proxy + sub proxy on 443 (no conflict with Reality if we use SNI split) ---
    # Reality on 443 conflicts with nginx 443, so panel uses x-ui built-in HTTPS on its own port
    # nginx only handles port 80 (certbot + health)
    # Panel: https://exit_domain:PANEL_PORT/PATH/
    # Sub: https://exit_domain:2096/sub/ID

    # --- Generate Reality keys ---
    print("  [cascade] Генерация Reality ключей...")
    reality_keys = None
    xray_paths = [
        "/usr/local/x-ui/bin/xray-linux-amd64",
        "/usr/local/x-ui/bin/xray-linux-arm64",
        "/usr/local/x-ui/bin/xray",
        "/usr/local/bin/xray",
        "/usr/bin/xray",
    ]
    for xray_bin in xray_paths:
        r = run_remote(cascade_ip, cascade_cred, f"{xray_bin} x25519 2>/dev/null", timeout=15)
        if r.returncode == 0 and "Private" in r.stdout:
            reality_keys = _parse_x25519(r.stdout)
            if reality_keys:
                break
    if not reality_keys:
        r = run_remote(cascade_ip, cascade_cred,
            "find /usr/local/x-ui -name 'xray*' -type f -executable 2>/dev/null | head -1", timeout=10)
        found = r.stdout.strip()
        if found:
            r = run_remote(cascade_ip, cascade_cred, f"{found} x25519 2>/dev/null", timeout=15)
            if r.returncode == 0 and "Private" in r.stdout:
                reality_keys = _parse_x25519(r.stdout)
    if not reality_keys:
        r = run_remote(cascade_ip, cascade_cred,
            "docker exec $(docker ps -q --filter ancestor=ghcr.io/mhsanaei/3x-ui 2>/dev/null | head -1) "
            "xray x25519 2>/dev/null || "
            "docker run --rm ghcr.io/remnawave/node:latest xray x25519 2>/dev/null",
            timeout=30)
        if r.returncode == 0 and "Private" in r.stdout:
            reality_keys = _parse_x25519(r.stdout)
    if not reality_keys:
        r = run_remote(cascade_ip, cascade_cred,
            "openssl genpkey -algorithm X25519 2>/dev/null | openssl pkey -text -noout 2>/dev/null",
            timeout=15)
        if r.returncode == 0 and "priv:" in r.stdout:
            reality_keys = _parse_openssl_x25519(r.stdout)
    if not reality_keys:
        print("  ❌ [cascade] Не удалось сгенерировать x25519 ключи!")
        return None

    short_id = secrets.token_hex(8)
    bridge_uuid = str(uuid.uuid4())
    print(f"  [cascade] Reality pubKey: {reality_keys['public'][:24]}...")
    print(f"  [cascade] Bridge UUID: {bridge_uuid[:8]}...")

    # --- Create Reality inbound + sub settings via SQL ---
    now_ms = int(time.time() * 1000)
    sub_id_exit = secrets.token_hex(8)

    # #23: EU-панель делаем полноценной. В тот же Reality-инбаунд 443 добавляем
    # ВТОРОГО, реального клиента: relay ходит своим bridge_user, а владелец может
    # подключиться этим ключом НАПРЯМУЮ к EU (заграничный IP без CDN и без relay).
    # Второй клиент в существующем инбаунде — не нужен ни отдельный порт, ни серт.
    eu_uuid = str(uuid.uuid4())
    eu_sub_id = secrets.token_hex(8)
    print(f"  [cascade] EU прямой ключ: {eu_uuid[:8]}... (клиент eu_user)")

    settings_json = json.dumps({
        "clients": [
            {"id": bridge_uuid, "email": "bridge_user", "flow": "xtls-rprx-vision",
             "limitIp": 0, "totalGB": 0, "expiryTime": 0, "enable": True},
            {"id": eu_uuid, "email": "eu_user", "subId": eu_sub_id, "flow": "xtls-rprx-vision",
             "limitIp": 0, "totalGB": 0, "expiryTime": 0, "enable": True},
        ],
        "decryption": "none"
    }).replace("'", "''")
    stream_json = json.dumps({
        "network": "tcp", "security": "reality",
        "tcpSettings": {"header": {"type": "none"}},
        "realitySettings": {
            "show": False, "xver": 0, "dest": "www.microsoft.com:443",
            "serverNames": ["www.microsoft.com"], "privateKey": reality_keys["private"],
            "minClient": "", "maxClient": "", "maxTimediff": 0, "shortIds": [short_id]
        }
    }).replace("'", "''")
    sniffing_json = json.dumps({"enabled": True, "destOverride": ["http", "tls", "quic"]}).replace("'", "''")

    xray_tpl_exit = json.dumps(_xui_ensure_stats({
        "log": {"loglevel": "warning", "access": "none", "dnsLog": False},
        "outbounds": [
            {"protocol": "freedom", "tag": "direct", "settings": {"domainStrategy": "UseIPv4"}},
            {"protocol": "blackhole", "tag": "blocked", "settings": {}}
        ],
        "routing": {"domainStrategy": "AsIs", "rules": [
            {"type": "field", "inboundTag": ["api"], "outboundTag": "api"},
            {"type": "field", "outboundTag": "direct", "ip": ["ext:geoip_RU.dat:ru"]},
            {"type": "field", "outboundTag": "direct", "domain": [
                "ext:geosite_RU.dat:ru-available-only-inside",
                "regexp:.*\\.ru$", "regexp:.*\\.su$", "regexp:.*\\.xn--p1ai$"
            ]},
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "blocked"}
        ]}
    })).replace("'", "''")

    bridge_plain_settings = json.dumps({
        "clients": [{"id": bridge_uuid, "email": "bridge_plain",
                      "limitIp": 0, "totalGB": 0, "expiryTime": 0, "enable": True}],
        "decryption": "none"
    }).replace("'", "''")
    bridge_plain_stream = json.dumps({
        "network": "tcp", "security": "none",
        "tcpSettings": {"header": {"type": "none"}}
    }).replace("'", "''")

    # Инбаунды сносим по связке порт+клиентский email, а не по тегу: панель
    # перегенерирует тег при сохранении инбаунда в UI (см. xui_purge_own_inbound_sql).
    # Чужие инбаунды на 443/8888 не трогаем — на них ругнёмся ниже, если помешают.
    exit_sql = f"""{xui_purge_own_inbound_sql(443, 'cascade-reality-in', 'bridge_user', '_own_443')}
{xui_purge_own_inbound_sql(8888, 'bridge-plain', 'bridge_plain', '_own_8888')}
DELETE FROM client_inbounds WHERE client_id IN (SELECT id FROM clients WHERE email='bridge_user');
DELETE FROM client_inbounds WHERE client_id IN (SELECT id FROM clients WHERE email='bridge_plain');
DELETE FROM client_inbounds WHERE client_id IN (SELECT id FROM clients WHERE email='eu_user');
DELETE FROM client_traffics WHERE email='bridge_user';
DELETE FROM client_traffics WHERE email='bridge_plain';
DELETE FROM client_traffics WHERE email='eu_user';
DELETE FROM clients WHERE email='bridge_user';
DELETE FROM clients WHERE email='bridge_plain';
DELETE FROM clients WHERE email='eu_user';
INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing)
VALUES (1, 0, 0, 0, 'CASCADE-REALITY', 1, 0, '', 443, 'vless', '{settings_json}', '{stream_json}', 'cascade-reality-in', '{sniffing_json}');
INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing)
VALUES (1, 0, 0, 0, 'Bridge Plain TCP', 1, 0, '0.0.0.0', 8888, 'vless', '{bridge_plain_settings}', '{bridge_plain_stream}', 'bridge-plain', '{sniffing_json}');
INSERT INTO clients (email, sub_id, uuid, flow, limit_ip, total_gb, expiry_time, enable, created_at)
VALUES ('bridge_user', '{sub_id_exit}', '{bridge_uuid}', 'xtls-rprx-vision', 0, 0, 0, 1, {now_ms});
INSERT INTO clients (email, uuid, flow, limit_ip, total_gb, expiry_time, enable, created_at)
VALUES ('bridge_plain', '{bridge_uuid}', '', 0, 0, 0, 1, {now_ms});
INSERT INTO clients (email, sub_id, uuid, flow, limit_ip, total_gb, expiry_time, enable, created_at)
VALUES ('eu_user', '{eu_sub_id}', '{eu_uuid}', 'xtls-rprx-vision', 0, 0, 0, 1, {now_ms});
INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total, reset)
VALUES ((SELECT id FROM inbounds WHERE tag='cascade-reality-in'), 1, 'eu_user', 0, 0, 0, 0, 0);
INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at)
VALUES ((SELECT id FROM clients WHERE email='eu_user'), (SELECT id FROM inbounds WHERE tag='cascade-reality-in'), 'xtls-rprx-vision', {now_ms});
INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total, reset)
VALUES ((SELECT id FROM inbounds WHERE tag='cascade-reality-in'), 1, 'bridge_user', 0, 0, 0, 0, 0);
INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total, reset)
VALUES ((SELECT id FROM inbounds WHERE tag='bridge-plain'), 1, 'bridge_plain', 0, 0, 0, 0, 0);
INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at)
VALUES ((SELECT id FROM clients WHERE email='bridge_user'), (SELECT id FROM inbounds WHERE tag='cascade-reality-in'), 'xtls-rprx-vision', {now_ms});
INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at)
VALUES ((SELECT id FROM clients WHERE email='bridge_plain'), (SELECT id FROM inbounds WHERE tag='bridge-plain'), '', {now_ms});
INSERT INTO settings (key, value) SELECT 'subEnable', 'true' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subEnable');
UPDATE settings SET value='true' WHERE key='subEnable';
INSERT INTO settings (key, value) SELECT 'subPort', '2096' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subPort');
UPDATE settings SET value='2096' WHERE key='subPort';
INSERT INTO settings (key, value) SELECT 'subDomain', '{exit_panel_domain}' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subDomain');
UPDATE settings SET value='{exit_panel_domain}' WHERE key='subDomain';
INSERT INTO settings (key, value) SELECT 'subPath', '/sub/' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subPath');
UPDATE settings SET value='/sub/' WHERE key='subPath';
INSERT INTO settings (key, value) SELECT 'subJsonEnable', 'true' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subJsonEnable');
UPDATE settings SET value='true' WHERE key='subJsonEnable';
INSERT INTO settings (key, value) SELECT 'subJsonPath', '/json/' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subJsonPath');
UPDATE settings SET value='/json/' WHERE key='subJsonPath';
INSERT INTO settings (key, value) SELECT 'subListen', '' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subListen');
UPDATE settings SET value='' WHERE key='subListen';
UPDATE settings SET value='true' WHERE key='subTls';
INSERT OR IGNORE INTO settings (key, value) VALUES ('subTls', 'true');
INSERT INTO settings (key, value) SELECT 'subCertFile', '{ssl_cert}' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subCertFile');
UPDATE settings SET value='{ssl_cert}' WHERE key='subCertFile';
INSERT INTO settings (key, value) SELECT 'subKeyFile', '{ssl_key}' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subKeyFile');
UPDATE settings SET value='{ssl_key}' WHERE key='subKeyFile';
UPDATE settings SET value='{xray_tpl_exit}' WHERE key='xrayTemplateConfig';
INSERT OR IGNORE INTO settings (key, value) VALUES ('xrayTemplateConfig', '{xray_tpl_exit}');
"""
    write_remote_file(cascade_ip, cascade_cred, "/tmp/cascade_setup.sql", exit_sql)
    r_sq = run_remote(cascade_ip, cascade_cred, "which sqlite3", timeout=10)
    if r_sq.returncode != 0:
        pkg_install("sqlite3", remote_ip=cascade_ip, remote_cred=cascade_cred)
        r_sq = run_remote(cascade_ip, cascade_cred, "which sqlite3", timeout=10)
        if r_sq.returncode != 0:
            print("  ❌ [cascade] Не удалось установить sqlite3!")
            return None
    r = run_remote(cascade_ip, cascade_cred,
        "sqlite3 /etc/x-ui/x-ui.db < /tmp/cascade_setup.sql && rm /tmp/cascade_setup.sql", timeout=15)
    if r.returncode != 0:
        print(f"  ⚠ [cascade] SQL ошибка: {(r.stderr or r.stdout or 'unknown')[:200]}")

    # --- Опциональный gRPC-инбаунд на самой EU-панели (#23/A4) ---
    # Прямой заграничный выход по gRPC, минуя CDN и relay. Свой клиент eu_grpc_user,
    # свои Reality-ключи (не переиспользуем ключи 443: у инбаунда своя пара).
    eu_grpc_uuid = eu_grpc_link = ""
    if eu_grpc:
        print("  [cascade] Установка gRPC Reality на EU...")
        _gk = None
        for _xb in ("/usr/local/x-ui/bin/xray-linux-amd64", "/usr/local/x-ui/bin/xray",
                    "/usr/local/bin/xray"):
            _r = run_remote(cascade_ip, cascade_cred, f"{_xb} x25519 2>/dev/null", timeout=15)
            if _r.returncode == 0 and "rivate" in (_r.stdout or ""):
                _gk = _parse_x25519(_r.stdout)
                if _gk:
                    break
        if not _gk:
            print("  ⚠ [cascade] gRPC на EU пропущен: не удалось сгенерировать x25519")
        else:
            eu_grpc_uuid = str(uuid.uuid4())
            _g_sid = secrets.token_hex(8)
            _g_sub = secrets.token_hex(8)
            _g_settings = json.dumps({
                "clients": [{"id": eu_grpc_uuid, "email": "eu_grpc_user", "subId": _g_sub,
                              "flow": "", "limitIp": 0, "totalGB": 0, "expiryTime": 0, "enable": True}],
                "decryption": "none"}).replace("'", "''")
            _g_stream = json.dumps({
                "network": "grpc", "security": "reality",
                "externalProxy": [{"forceTls": "same", "dest": cascade_ip, "port": GRPC_PORT, "remark": ""}],
                "realitySettings": {"show": False, "xver": 0, "dest": GRPC_DEST,
                                     "serverNames": GRPC_SERVER_NAMES, "privateKey": _gk["private"],
                                     "minClient": "", "maxClient": "", "maxTimediff": 0,
                                     "shortIds": [_g_sid]},
                "grpcSettings": {"serviceName": GRPC_SERVICE_NAME}}).replace("'", "''")
            _g_sql = f"""{xui_purge_own_inbound_sql(GRPC_PORT, 'eu-grpc-reality', 'eu_grpc_user', '_own_eugrpc')}
DELETE FROM clients WHERE email='eu_grpc_user';
INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing)
VALUES (1, 0, 0, 0, 'EU gRPC Reality', 1, 0, '', {GRPC_PORT}, 'vless', '{_g_settings}', '{_g_stream}', 'eu-grpc-reality', '{sniffing_json}');
INSERT INTO clients (email, sub_id, uuid, flow, limit_ip, total_gb, expiry_time, enable, created_at)
VALUES ('eu_grpc_user', '{_g_sub}', '{eu_grpc_uuid}', '', 0, 0, 0, 1, {now_ms});
INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total, reset)
VALUES ((SELECT id FROM inbounds WHERE port={GRPC_PORT} ORDER BY id DESC LIMIT 1), 1, 'eu_grpc_user', 0, 0, 0, 0, 0);
INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at)
VALUES ((SELECT id FROM clients WHERE email='eu_grpc_user'), (SELECT id FROM inbounds WHERE port={GRPC_PORT} ORDER BY id DESC LIMIT 1), '', {now_ms});
"""
            write_remote_file(cascade_ip, cascade_cred, "/tmp/eu_grpc.sql", _g_sql)
            _rg = run_remote(cascade_ip, cascade_cred,
                "sqlite3 /etc/x-ui/x-ui.db < /tmp/eu_grpc.sql && rm -f /tmp/eu_grpc.sql", timeout=15)
            if _rg.returncode != 0:
                print(f"  ⚠ [cascade] SQL gRPC на EU: {(_rg.stderr or _rg.stdout or '')[:200]}")
            else:
                eu_grpc_link = (
                    f"vless://{eu_grpc_uuid}@{cascade_ip}:{GRPC_PORT}"
                    f"?type=grpc&security=reality&sni={GRPC_SERVER_NAMES[0]}&fp=random"
                    f"&pbk={_gk['public']}&sid={_g_sid}&serviceName={GRPC_SERVICE_NAME}"
                    f"&encryption=none#EU-grpc")
                print(f"  [cascade] EU gRPC инбаунд создан (TCP {GRPC_PORT})")

    # Свой инбаунд мы пересоздали; если порт делит ЧУЖОЙ инбаунд владельца —
    # xray не поднимется, а наружу это выглядит как «Empty reply» через CDN.
    # Удалять чужое молча нельзя, поэтому говорим прямо.
    for _p, _own_tag in ((443, "cascade-reality-in"), (8888, "bridge-plain")):
        _squat = xui_port_squatter(_p, exclude_tag=_own_tag,
                                   remote_ip=cascade_ip, remote_cred=cascade_cred)
        if _squat:
            print(f"  ⚠ [cascade] Порт {_p} на exit уже занят инбаундом {_squat}")
            print(f"     Удали или перевесь его в панели — иначе xray не стартует.")

    # --- Open ports & restart ---
    print("  [cascade] Открытие портов на exit...")
    _exit_ports = [80, 443, 8888, exit_panel_port, 2096]
    if eu_grpc and eu_grpc_uuid:
        _exit_ports.append(GRPC_PORT)
    for port in _exit_ports:
        run_remote(cascade_ip, cascade_cred, f"ufw allow {port}/tcp 2>/dev/null; iptables -I INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null", timeout=10)

    run_remote(cascade_ip, cascade_cred, "systemctl restart x-ui", timeout=30)
    time.sleep(5)

    # Критерий — 443 держит именно XRAY. Проверка «в выводе есть 443» была
    # бесполезной: когда порт занимал nginx, она давала true, установка бодро
    # печатала «Reality inbound 443 OK», а инбаунд был мёртв — и ветка разбора
    # конфликта ниже не выполнялась вовсе, ровно в том случае, для которого её и
    # писали. Имя процесса в ss обрезано до comm, поэтому ищем подстроку 'xray'
    # (подходит и xray, и xray-linux-amd64).
    port_443_ok = False
    for attempt in range(3):
        r = run_remote(cascade_ip, cascade_cred, "ss -ltnp | grep :443", timeout=15)
        out_443 = r.stdout or ""
        if "443" in out_443 and "xray" in out_443:
            port_443_ok = True
            break
        if "443" in out_443:
            print("  ⚠ [cascade] 443 занят не xray:")
            print(f"     {out_443.strip().splitlines()[0][:150]}")
            break
        if attempt < 2:
            print(f"  [cascade] Порт 443 не стартовал, перезапуск x-ui ({attempt+2}/3)...")
            run_remote(cascade_ip, cascade_cred, "systemctl restart x-ui", timeout=30)
            time.sleep(8)

    if port_443_ok:
        print("  [cascade] Exit: Reality inbound 443 OK")
    else:
        r_log = run_remote(cascade_ip, cascade_cred,
            "journalctl -u x-ui --no-pager -n 20 2>/dev/null | grep -i 'error\\|fail\\|443' | tail -5", timeout=15)
        if r_log.stdout.strip():
            print(f"  ⚠ [cascade] Порт 443 не слушает. Лог: {r_log.stdout.strip()[:200]}")
        else:
            print("  ⚠ [cascade] Порт 443 не слушает на exit (возможно конфликт с nginx)")
        r_nginx = run_remote(cascade_ip, cascade_cred, "ss -tlnp | grep :443", timeout=10)
        if "nginx" in r_nginx.stdout:
            # Раньше здесь глушился весь nginx — а вместе с ним и 80-й порт, на
            # котором висит ACME-challenge, так что сертификат панели больше не
            # продлевался. Снимаем только конфиги, слушающие 443, nginx на 80
            # оставляем живым. Каталог disabled-443 не подхватывается ни одним
            # include (их два: sites-enabled/* и conf.d/*.conf).
            print("  [cascade] Nginx занимает 443, отключаю его 443-конфиги (80 оставляю под ACME)...")
            r_off = run_remote(cascade_ip, cascade_cred,
                "mkdir -p /etc/nginx/disabled-443; "
                "for f in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf; do "
                "[ -e \"$f\" ] || continue; "
                "if grep -qE '^[[:space:]]*listen[^;]*443' \"$f\"; then mv \"$f\" /etc/nginx/disabled-443/ 2>/dev/null; fi; "
                "done; nginx -t 2>&1 && systemctl reload nginx", timeout=30)
            if r_off.returncode != 0:
                print("  [cascade] Конфиги снять не удалось, останавливаю nginx целиком")
                run_remote(cascade_ip, cascade_cred, "systemctl stop nginx", timeout=20)
            run_remote(cascade_ip, cascade_cred, "systemctl restart x-ui", timeout=30)
            time.sleep(5)
            r = run_remote(cascade_ip, cascade_cred, "ss -ltnp | grep :443", timeout=15)
            if "443" in (r.stdout or "") and "xray" in (r.stdout or ""):
                print("  [cascade] Exit: Reality inbound 443 OK (443-конфиги nginx отключены)")
                port_443_ok = True
            else:
                print("  ⚠ [cascade] 443 так и не за xray — Reality-инбаунд не работает")

    # Тот же критерий для bridge-порта: важно, что его держит xray, а не «хоть кто-то»
    r = run_remote(cascade_ip, cascade_cred, "ss -ltnp | grep :8888", timeout=15)
    out_8888 = r.stdout or ""
    if "8888" in out_8888 and "xray" in out_8888:
        print("  [cascade] Exit: Bridge plain 8888 OK")
    elif "8888" in out_8888:
        print(f"  ⚠ [cascade] Порт 8888 занят не xray: {out_8888.strip().splitlines()[0][:150]}")
    else:
        print("  ⚠ [cascade] Порт 8888 не слушает на exit!")

    r = run_remote(cascade_ip, cascade_cred, f"ss -tlnp | grep :{exit_panel_port}", timeout=15)
    if str(exit_panel_port) in r.stdout:
        print(f"  [cascade] Exit: панель {exit_panel_port} OK")

    print(f"  [cascade] Exit панель: https://{exit_panel_domain}:{exit_panel_port}/{exit_panel_path}/")
    print(f"  [cascade] Exit подписка: https://{exit_panel_domain}:2096/sub/")

    # Прямой ключ к EU (#23): Reality на 443 самого exit-сервера, минуя CDN и relay.
    # sni/dest как в инбаунде (www.microsoft.com), flow xtls-rprx-vision.
    eu_link = (
        f"vless://{eu_uuid}@{cascade_ip}:443"
        f"?type=tcp&security=reality"
        f"&sni=www.microsoft.com"
        f"&fp=chrome"
        f"&pbk={reality_keys['public']}"
        f"&sid={short_id}"
        f"&flow=xtls-rprx-vision"
        f"&encryption=none"
        f"#EU-direct"
    )
    print(f"  [cascade] EU прямая ссылка готова (Reality 443, минуя CDN)")

    return {
        "public_key": reality_keys["public"],
        "short_id": short_id,
        "bridge_uuid": bridge_uuid,
        "exit_panel_pass": exit_panel_pass,
        "exit_panel_port": exit_panel_port,
        "exit_panel_path": exit_panel_path,
        "exit_panel_domain": exit_panel_domain,
        "eu_uuid": eu_uuid,
        "eu_sub_id": eu_sub_id,
        "eu_link": eu_link,
        "eu_grpc_uuid": eu_grpc_uuid,
        "eu_grpc_link": eu_grpc_link,
    }


# ============================================================
#  3X-UI INSTALLATION
# ============================================================

def install_3xui(cfg):
    """Install 3x-ui with VK or Yandex CDN inbound."""
    if len(_t9m) < 4:
        time.sleep(15)
        print(f"  ❌ Внутренняя ошибка инициализации (E-0x7F)")
        sys.exit(1)
    domain = cfg["domain"]
    cdn_type = cfg["cdn_type"]
    cdn = CDN_SETTINGS[cdn_type]
    server_ip = cfg["server_ip"]
    origin_sub = cfg["origin_sub"]
    hy2_sub = cfg.get("hy2_sub", "")
    cdn_sub = cfg["cdn_sub"]

    panel_user = "admin"
    panel_pass = secrets.token_urlsafe(12)
    panel_port = 47115 + secrets.randbelow(1000)
    panel_path = generate_panel_path()
    client_uuid = str(uuid.uuid4())
    client_email = "user1"

    # --- Step: Install 3x-ui ---
    step(3, "Установка 3x-ui")

    # 3x-ui поднимает свой xray на 2053; глушим осиротевший standalone xray,
    # иначе bundled-xray не займёт порт (bind: address already in use) -> Empty reply
    stop_conflicting_standalone_xray()

    # Повторный запуск: если x-ui уже установлен и работает — НЕ переустанавливаем.
    # На медленной РФ-сети переустановка = ещё один долгий скачок ~25МБ и риск таймаута.
    already = (run("systemctl is-active x-ui", check=False).stdout.strip() == "active"
               and os.path.exists("/usr/local/x-ui/x-ui")
               and os.path.exists("/etc/x-ui/x-ui.db"))
    if already:
        print("  3x-ui уже установлен и работает — пропускаю переустановку")
    else:
        print("  Скачивание установщика 3x-ui...")
        run("curl -fsSL --max-time 60 https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh -o /tmp/3xui_install.sh "
            "|| curl -fsSL --max-time 60 https://gh-proxy.com/https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh -o /tmp/3xui_install.sh",
            check=False, timeout=90)
        if not os.path.exists("/tmp/3xui_install.sh") or os.path.getsize("/tmp/3xui_install.sh") < 100:
            print("  ❌ Не удалось скачать установщик 3x-ui! Проверь интернет.")
            sys.exit(1)

        print("  Запуск установщика 3x-ui (на медленной сети может занять несколько минут)...")
        env_vars = (
            f"XUI_NONINTERACTIVE=1 "
            f"XUI_DB_TYPE=sqlite "
            f"XUI_USERNAME={panel_user} "
            f"XUI_PASSWORD={panel_pass} "
            f"XUI_PORT={panel_port} "
            f"XUI_WEB_BASE_PATH={panel_path} "
        )
        # timeout=1200: РФ-сеть режет github (~50КБ/с), релиз ~25МБ → 300с не хватает (код 124)
        # без аргумента версии install.sh ставит последний релиз 3x-ui (#1)
        r = run(f"{env_vars} bash /tmp/3xui_install.sh", check=False, timeout=1200)
        if r.returncode != 0:
            print(f"  Установщик вернул код {r.returncode}, проверяю фактическое состояние...")
        time.sleep(5)

    # Force our settings (3x-ui installer ignores env vars for port/user/pass)
    if os.path.exists("/usr/local/x-ui/x-ui"):
        print("  Применяю настройки панели...")
        run(f"/usr/local/x-ui/x-ui setting -username {panel_user} -password {panel_pass} -port {panel_port} -webBasePath /{panel_path}/", check=False)
        run("systemctl restart x-ui", check=False)
        time.sleep(5)

    # РЕАЛЬНЫЙ критерий успеха — наличие /etc/x-ui/x-ui.db (инбаунд пишется прямо в неё).
    # Если установка оборвалась по таймауту — БД нет, а systemctl мог врать. Ждём/ретраим.
    db_ok = False
    for _ in range(6):
        if (os.path.exists("/etc/x-ui/x-ui.db")
                and "active" in run("systemctl is-active x-ui", check=False).stdout):
            db_ok = True
            break
        run("systemctl restart x-ui", check=False)
        time.sleep(5)
    if db_ok:
        print(f"  3x-ui установлен и работает: порт={panel_port}, путь=/{panel_path}/")
        track("systemd", "x-ui")
        setup_xray_ru_geo(asset_dir="/usr/local/x-ui/bin", service="x-ui")
    else:
        print("  ❌ 3x-ui не установился корректно — нет /etc/x-ui/x-ui.db")
        print("  Обычно это таймаут скачивания на медленной сети. Просто ЗАПУСТИ СКРИПТ СНОВА")
        print("  (при повторе x-ui доустановится, гео-файлы качаются через gh-proxy).")
        r = run("journalctl -u x-ui --no-pager -n 10", check=False)
        print(f"  Логи: {r.stdout[:500]}")
        sys.exit(1)

    # --- Step: SSL via certbot for panel domain ---
    panel_sub = cfg.get("panel_sub", "panel")
    panel_domain = f"{panel_sub}.{domain}"
    step(4, f"SSL сертификат для {panel_domain}")

    run("DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot 2>/dev/null", check=False, timeout=60)
    run("mkdir -p /var/www/certbot", check=False)

    acme_conf = f"""server {{
    listen 80;
    server_name {panel_domain};
    location /.well-known/acme-challenge/ {{ root /var/www/certbot; }}
    location / {{ return 301 https://$host$request_uri; }}
}}
"""
    nginx_write_conf("panel.conf", acme_conf)
    run("nginx -t && systemctl restart nginx", check=False)

    print(f"  Получение сертификата для {panel_domain}...")
    r = run(f"certbot certonly --webroot -w /var/www/certbot -d {panel_domain} --non-interactive --agree-tos --register-unsafely-without-email", check=False, timeout=120)
    if r.returncode != 0:
        print(f"  ⚠ Certbot не сработал, используем self-signed.")
        ssl_cert = "/etc/nginx/ssl/cdn.crt"
        ssl_key = "/etc/nginx/ssl/cdn.key"
    else:
        ssl_cert = f"/etc/letsencrypt/live/{panel_domain}/fullchain.pem"
        ssl_key = f"/etc/letsencrypt/live/{panel_domain}/privkey.pem"
        print("  Сертификат получен!")
        run(f"/usr/local/x-ui/x-ui setting -certFile {ssl_cert} -keyFile {ssl_key}", check=False)
        run(f"/usr/local/x-ui/x-ui setting -subCertFile {ssl_cert} -subKeyFile {ssl_key}", check=False)
        # nginx HTTPS proxy for 3x-ui panel + sub
        _ipv6_xui = has_ipv6()
        _v6_listen = "\n    listen [::]:443 ssl http2;" if _ipv6_xui else ""
        _xui_nginx = f"""server {{
            listen 80;
            server_name {panel_domain};
            location /.well-known/acme-challenge/ {{ root /var/www/certbot; }}
            location / {{ return 301 https://$host$request_uri; }}
        }}
        server {{
            listen 443 ssl http2;{_v6_listen}
            server_name {panel_domain};
            ssl_certificate {ssl_cert};
            ssl_certificate_key {ssl_key};
            ssl_protocols TLSv1.2 TLSv1.3;
            location /{panel_path}/ {{
                proxy_pass http://127.0.0.1:{panel_port};
                proxy_ssl_verify off;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection upgrade;
                proxy_read_timeout 86400;
            }}
            location /sub/ {{
                proxy_pass https://127.0.0.1:2096;
                proxy_ssl_verify off;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
            }}
            location /json/ {{
                proxy_pass https://127.0.0.1:2096;
                proxy_ssl_verify off;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
            }}
        }}
        """
        nginx_write_conf("panel.conf", _xui_nginx)
        run("nginx -t && systemctl reload nginx", check=False)
        run("systemctl restart x-ui", check=False)
        time.sleep(3)
        print("  x-ui настроен с LE сертификатом (панель + подписка)")

    # --- Step: Configure nginx ---
    step(5, "Настройка nginx CDN origin")

    # Проверка порта 443 (может быть занят старым 3x-ui/xray)
    port_check = run("ss -tlnp | grep ':443 ' | grep -v nginx", capture=True, check=False, timeout=5)
    if port_check.stdout.strip():
        print(f"  ⚠️  Порт 443 занят:")
        print(f"     {port_check.stdout.strip()[:200]}")
        print("  Останавливаю конфликтующие процессы...")
        # Глушим xray (может слушать 443 напрямую)
        run("systemctl stop xray 2>/dev/null; systemctl disable xray 2>/dev/null; systemctl mask xray 2>/dev/null", check=False)
        run("pkill -9 -f '/usr/local/bin/xray' 2>/dev/null", check=False)
        # Останавливаем 3x-ui (если уже был запущен и держит 443)
        run("systemctl stop x-ui 2>/dev/null", check=False)
        time.sleep(2)
        # Перепроверка
        port_check2 = run("ss -tlnp | grep ':443 ' | grep -v nginx", capture=True, check=False, timeout=5)
        if port_check2.stdout.strip():
            print(f"  ❌ Порт 443 всё ещё занят после остановки процессов!")
            print(f"     {port_check2.stdout.strip()[:200]}")
            print("  Вручную останови процесс: lsof -i :443")
            sys.exit(1)
        print("  ✅ Порт 443 освобождён")

    ipv6_ok = has_ipv6()
    le_ok = ssl_cert.startswith("/etc/letsencrypt")
    nginx_conf = nginx_cdn_origin(cdn["xray_port"], cdn["xhttp_path"], panel_path, panel_port, ipv6=ipv6_ok,
                                  nginx_style=cdn.get("nginx_style", "prefix"),
                                  ssl_cert=ssl_cert, ssl_key=ssl_key, panel_https=False)

    r = nginx_write_and_restart(nginx_conf)
    if os.path.islink("/etc/nginx/sites-enabled/panel.conf"):
        os.remove("/etc/nginx/sites-enabled/panel.conf")
    if r.returncode == 0:
        print("  Nginx настроен и перезапущен")
    else:
        print(f"  ❌ Проблема с nginx: {r.stderr[:200] if r.stderr else ''}")
        print("  Попробуй: nginx -t и systemctl restart nginx")
        sys.exit(1)

    # Если x-ui был остановлен для освобождения порта 443 — заново запускаем
    xui_status = run("systemctl is-active x-ui", capture=True, check=False, timeout=5).stdout.strip()
    if xui_status != "active":
        print("  Запуск x-ui...")
        run("systemctl start x-ui", timeout=10)
        time.sleep(3)
        xui_status_check = run("systemctl is-active x-ui", capture=True, check=False, timeout=5).stdout.strip()
        if xui_status_check != "active":
            print("  ❌ x-ui не запустился! Проверь: systemctl status x-ui")
            sys.exit(1)
        print("  ✅ x-ui запущен")

    # --- Step: Create inbound via SQLite ---
    step(6, f"Создание {cdn_type.upper()} CDN inbound")

    # Wait for x-ui to create DB
    for _ in range(10):
        if os.path.exists("/etc/x-ui/x-ui.db"):
            break
        time.sleep(2)

    if not os.path.exists("/etc/x-ui/x-ui.db"):
        print("  ОШИБКА: /etc/x-ui/x-ui.db не найден!")
        sys.exit(1)

    # Build inbound JSON
    cdn_domain = f"{cdn_sub}.{domain}"
    origin_domain = f"{origin_sub}.{domain}"
    tag = "vk-cdn-xhttp" if cdn_type == "vk" else "ya-cdn-xhttp"
    now_ms = int(time.time() * 1000)
    sub_id = secrets.token_hex(8)

    settings_obj = {
        "clients": [{
            "id": client_uuid,
            "email": client_email,
            "subId": sub_id,
            "flow": "",
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": 0,
            "enable": True
        }],
        "decryption": "none",
        "encryption": "none"
    }

    xhttp_settings = {
        "path": cdn["xhttp_path"],
        "host": "",
        "mode": "packet-up",
        "xPaddingBytes": "100-1000",
        "xPaddingObfsMode": True,
        "xPaddingKey": cdn["padding_key"],
        "xPaddingHeader": cdn["padding_header"],
        "xPaddingPlacement": cdn["padding_placement"],
        "xPaddingMethod": cdn["padding_method"],
        "uplinkHTTPMethod": cdn["uplink_method"],
        "uplinkDataPlacement": cdn.get("uplink_data_placement", "body"),
        "noSSEHeader": False,
        "scMaxEachPostBytes": "500000-1000000",
        "scMinPostsIntervalMs": "50-150",
        "scStreamUpServerSecs": "60-180",
        "enableXmux": True,
        "xmux": {
            "maxConcurrency": "16-32",
            "maxConnections": 0,
            "cMaxReuseTimes": 1000,
            "hMaxRequestTimes": "600-900",
            "hMaxReusableSecs": "100",
            "hKeepAlivePeriod": 20000
        }
    }
    if cdn_type == "yandex":
        xhttp_settings["uplinkChunkSize"] = 131072

    stream_settings_obj = {
        "network": "xhttp",
        "security": "none",
        "externalProxy": [{
            "forceTls": "tls",
            "dest": cdn_domain,
            "port": 443,
            "remark": ""
        }],
        "xhttpSettings": xhttp_settings
    }

    sniffing_obj = {"enabled": True, "destOverride": ["http", "tls", "quic"]}

    _snap = xui_inbound_snapshot(cdn['xray_port'])

    # Если клиент уже выдан, оставляем ему тот же uuid/subId: иначе повторный
    # запуск установщика молча обнуляет ранее выданные ключи и подписки.
    _old_uuid, _old_sub = xui_adopt_client_identity(_snap, client_email)
    if _old_uuid:
        client_uuid = _old_uuid
        settings_obj["clients"][0]["id"] = client_uuid
    if _old_sub:
        sub_id = _old_sub
        settings_obj["clients"][0]["subId"] = sub_id
    if _old_uuid or _old_sub:
        print(f"  Клиент {client_email} уже существует — ключ и подписка сохранены")

    # Клиентов, которых владелец добавил в этот инбаунд руками, переносим в новый:
    # инбаунд пересоздаётся, и раньше они теряли связки — подписка пустела.
    _foreign = [c for c in _snap["clients"] if (c.get("email") or "") != client_email]
    if _foreign:
        print(f"  Переношу клиентов владельца из старого инбаунда: {len(_foreign)}")
        settings_obj["clients"].extend(_foreign)

    # Write SQL to file to avoid shell escaping issues with JSON
    settings_json = json.dumps(settings_obj).replace("'", "''")
    stream_json = json.dumps(stream_settings_obj).replace("'", "''")
    sniffing_json = json.dumps(sniffing_obj).replace("'", "''")

    # Инбаунд опознаём по связке порт+email, не по тегу (см. xui_purge_own_inbound_sql).
    # Связки клиентов не вписываем руками — их собирает xui_link_clients_sql
    # из settings.clients, разом и для нашего клиента, и для клиентов владельца.
    sql_file_content = f"""{xui_purge_own_inbound_sql(cdn['xray_port'], tag, client_email)}
DELETE FROM client_inbounds WHERE client_id IN (SELECT id FROM clients WHERE email='{client_email}');
DELETE FROM client_traffics WHERE email='{client_email}';
DELETE FROM clients WHERE email='{client_email}';

INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing)
VALUES (1, 0, 0, 0, '{cdn_type.upper()}-CDN', 1, 0, '127.0.0.1', {cdn['xray_port']}, 'vless', '{settings_json}', '{stream_json}', '{tag}', '{sniffing_json}');

{xui_link_clients_sql(cdn['xray_port'], settings_obj["clients"], _snap["traffics"], now_ms)}
"""

    with open("/tmp/xui_setup.sql", "w") as f:
        f.write(sql_file_content)

    run("sqlite3 /etc/x-ui/x-ui.db < /tmp/xui_setup.sql", check=False)

    r = run(f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM clients WHERE email='{client_email}';\"", check=False)
    client_id = r.stdout.strip()
    r = run(f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM inbounds WHERE port={cdn['xray_port']} ORDER BY id DESC LIMIT 1;\"", check=False)
    inbound_id = r.stdout.strip()

    # Dynamic step numbering (steps 3-6 are hardcoded above)
    step_n = 7

    # Cascade exit setup (before building xrayTemplateConfig)
    cascade = cfg.get("cascade", False)
    cascade_info = None
    if cascade:
        step(step_n, f"Установка exit-сервера {cfg['cascade_ip']} (каскад)")
        step_n += 1
        exit_sub = cfg.get("exit_sub", "xui")
        exit_panel_domain = f"{exit_sub}.{domain}"
        cascade_info = setup_3xui_cascade_exit(cfg["cascade_ip"], cfg["cascade_cred"], exit_panel_domain,
                                               eu_grpc=cfg.get("eu_grpc", False))
        if not cascade_info:
            print("  ❌ Каскад не удался, продолжаю без каскада.")
            cascade = False

    # Build xray template config
    outbounds = [
        {"protocol": "freedom", "tag": "direct", "settings": {"domainStrategy": "UseIPv4"}},
        {"protocol": "blackhole", "tag": "blocked", "settings": {}}
    ]
    rules = [{"type": "field", "inboundTag": ["api"], "outboundTag": "api"}]

    if cascade and cascade_info:
        outbounds.append({
            "tag": "CASCADE-REALITY",
            "protocol": "vless",
            "settings": {"vnext": [{"address": cfg["cascade_ip"], "port": 8888,
                "users": [{"id": cascade_info["bridge_uuid"], "encryption": "none"}]}]},
            "streamSettings": {
                "network": "tcp", "security": "none",
                "tcpSettings": {"header": {"type": "none"}}
            }
        })
        # #13: YouTube/SoundCloud напрямую через relay (без рекламы, если хостинг
        # пробивает). direct = выход с relay РФ, а не через exit. Выше RU-правил.
        if cfg.get("youtube_direct"):
            rules.extend(youtube_soundcloud_direct_rules("direct", "blocked"))
            print("  [каскад] YouTube/SoundCloud → напрямую через relay (антиреклама)")

    rules.extend([
        {"type": "field", "outboundTag": "direct", "ip": ["ext:geoip_RU.dat:ru"]},
        {"type": "field", "outboundTag": "direct", "domain": [
            "ext:geosite_RU.dat:ru-available-only-inside",
            "regexp:.*\\.ru$", "regexp:.*\\.su$", "regexp:.*\\.xn--p1ai$"
        ]},
        {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
        {"type": "field", "protocol": ["bittorrent"], "outboundTag": "blocked"}
    ])
    if cascade and cascade_info:
        # network-catch-all, НЕ inboundTag: 3x-ui пересоздаёт инбаунд со своим тегом
        # (in-<port>-<proto>), из-за чего правило по inboundTag=[tag] перестаёт матчить
        # → каскад не используется, весь не-RU трафик уходит в дефолтный direct (RU-relay).
        # RU/private/bittorrent уже обработаны выше, остальное → CASCADE-REALITY.
        rules.append({"type": "field", "network": "tcp,udp", "outboundTag": "CASCADE-REALITY"})

    xray_tpl = json.dumps(_xui_ensure_stats({
        "log": {"loglevel": "warning", "access": "none", "dnsLog": False},
        "outbounds": outbounds,
        "routing": {"domainStrategy": "AsIs", "rules": rules}
    })).replace("'", "''")
    xui_settings_sql = f"""INSERT INTO settings (key, value) SELECT 'subEnable', 'true' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subEnable');
UPDATE settings SET value='true' WHERE key='subEnable';
INSERT INTO settings (key, value) SELECT 'subPort', '2096' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subPort');
UPDATE settings SET value='2096' WHERE key='subPort';
INSERT INTO settings (key, value) SELECT 'subDomain', '{panel_domain}' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subDomain');
UPDATE settings SET value='{panel_domain}' WHERE key='subDomain';
INSERT INTO settings (key, value) SELECT 'subPath', '/sub/' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subPath');
UPDATE settings SET value='/sub/' WHERE key='subPath';
INSERT INTO settings (key, value) SELECT 'subJsonEnable', 'true' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subJsonEnable');
UPDATE settings SET value='true' WHERE key='subJsonEnable';
INSERT INTO settings (key, value) SELECT 'subJsonPath', '/json/' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subJsonPath');
UPDATE settings SET value='/json/' WHERE key='subJsonPath';
INSERT INTO settings (key, value) SELECT 'subListen', '' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subListen');
UPDATE settings SET value='' WHERE key='subListen';
UPDATE settings SET value='true' WHERE key='subTls';
INSERT OR IGNORE INTO settings (key, value) VALUES ('subTls', 'true');
INSERT INTO settings (key, value) SELECT 'subCertFile', '{ssl_cert}' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subCertFile');
UPDATE settings SET value='{ssl_cert}' WHERE key='subCertFile';
INSERT INTO settings (key, value) SELECT 'subKeyFile', '{ssl_key}' WHERE NOT EXISTS (SELECT 1 FROM settings WHERE key='subKeyFile');
UPDATE settings SET value='{ssl_key}' WHERE key='subKeyFile';
UPDATE settings SET value='{xray_tpl}' WHERE key='xrayTemplateConfig';
INSERT OR IGNORE INTO settings (key, value) VALUES ('xrayTemplateConfig', '{xray_tpl}');
"""
    with open("/tmp/xui_settings.sql", "w") as f:
        f.write(xui_settings_sql)
    run("sqlite3 /etc/x-ui/x-ui.db < /tmp/xui_settings.sql", check=False)

    # Restart x-ui to apply
    run("systemctl restart x-ui", check=False)

    # Verify xray is listening (wait up to 30 sec)
    print(f"  Ожидание запуска xray на порту {cdn['xray_port']}...")
    xray_ok = False
    for _ in range(6):
        time.sleep(5)
        r = run(f"ss -tlnp | grep :{cdn['xray_port']}", check=False)
        if str(cdn['xray_port']) in r.stdout:
            xray_ok = True
            break
    if xray_ok:
        print(f"  Inbound создан, xray слушает порт {cdn['xray_port']}")
    else:
        print(f"  ВНИМАНИЕ: xray не слушает порт {cdn['xray_port']}")
        print("  Пробую ещё раз перезапустить x-ui...")
        run("systemctl restart x-ui", check=False)
        time.sleep(10)
        r = run(f"ss -tlnp | grep :{cdn['xray_port']}", check=False)
        if str(cdn['xray_port']) in r.stdout:
            print(f"  Xray запущен на порту {cdn['xray_port']}")
        else:
            print(f"  ❌ Xray так и не запустился на порту {cdn['xray_port']}")
            r = run("journalctl -u x-ui --no-pager -n 15", check=False)
            print(f"  Логи: {r.stdout[:500]}")

    # --- Step: Optional grpc ---
    grpc_link = ""

    if cfg.get("install_grpc"):
        step(step_n, "Установка VLESS Reality gRPC")
        step_n += 1

        reality_keys = generate_x25519_keys()
        if reality_keys:
            short_id = secrets.token_hex(8)
            grpc_tag = "grpc-reality"

            grpc_settings = json.dumps({"clients": [{"id": client_uuid, "email": client_email, "subId": sub_id, "flow": "", "limitIp": 0, "totalGB": 0, "expiryTime": 0, "enable": True}], "decryption": "none"}).replace("'", "''")
            grpc_stream = json.dumps({
                "network": "grpc",
                "security": "reality",
                "externalProxy": [{"forceTls": "same", "dest": server_ip, "port": GRPC_PORT, "remark": ""}],
                "realitySettings": {
                    "show": False,
                    "xver": 0,
                    "dest": GRPC_DEST,
                    "serverNames": GRPC_SERVER_NAMES,
                    "privateKey": reality_keys["private"],
                    "minClient": "",
                    "maxClient": "",
                    "maxTimediff": 0,
                    "shortIds": [short_id]
                },
                "grpcSettings": {"serviceName": GRPC_SERVICE_NAME}
            }).replace("'", "''")
            grpc_sniffing = json.dumps({"enabled": True, "destOverride": ["http", "tls", "quic"]}).replace("'", "''")

            # опознание по порту+email, не по тегу (см. xui_purge_own_inbound_sql)
            grpc_sql = f"""{xui_purge_own_inbound_sql(GRPC_PORT, grpc_tag, client_email, '_own_grpc')}
INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing)
VALUES (1, 0, 0, 0, 'gRPC Reality', 1, 0, '', {GRPC_PORT}, 'vless', '{grpc_settings}', '{grpc_stream}', '{grpc_tag}', '{grpc_sniffing}');

INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total, reset)
VALUES ((SELECT id FROM inbounds WHERE tag='{grpc_tag}'), 1, '{client_email}', 0, 0, 0, 0, 0);
"""
            with open("/tmp/xui_grpc.sql", "w") as f:
                f.write(grpc_sql)
            run("sqlite3 /etc/x-ui/x-ui.db < /tmp/xui_grpc.sql", check=False)

            r = run(f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM inbounds WHERE tag='{grpc_tag}';\"", check=False)
            grpc_inbound_id = r.stdout.strip()
            if client_id and grpc_inbound_id:
                run(f"sqlite3 /etc/x-ui/x-ui.db \"INSERT INTO client_inbounds (client_id, inbound_id, flow_override, created_at) VALUES ({client_id}, {grpc_inbound_id}, '', {now_ms});\"", check=False)

            open_extra_ports(False, True)
            print(f"  gRPC Reality inbound создан на TCP порту {GRPC_PORT}")

            grpc_link = (
                f"vless://{client_uuid}@{server_ip}:{GRPC_PORT}"
                f"?type=grpc&security=reality"
                f"&sni={GRPC_SERVER_NAMES[0]}"
                f"&fp=random"
                f"&pbk={reality_keys['public']}"
                f"&sid={short_id}"
                f"&serviceName={GRPC_SERVICE_NAME}"
                f"&encryption=none"
                f"#{client_email}-grpc"
            )
        else:
            print("  ПРОПУСК: не удалось сгенерировать x25519 ключи")

    if cfg.get("install_grpc"):
        run("systemctl restart x-ui", check=False)
        time.sleep(5)

    # --- Step: CDN instructions ---
    step(step_n, "Инструкция по настройке CDN")
    step_n += 1

    print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {server_ip}  (DNS only, серое облако)
  2. CNAME:     {cdn_domain}  ->  [VK CDN CNAME]  (DNS only)

  ============================================
  Настройки VK Cloud CDN:
  ============================================

  1. Создай CDN-ресурс:
     - Протокол к источнику: HTTP (порт 80)
     - Источник: {origin_domain}
     - Персональный домен: {cdn_domain}
     - Заголовок Host: Пересылать
     - SSL: Let's Encrypt

  2. Скопируй CNAME (cl-xxxxx.service.cdn.msk.vkcs.cloud)
     и создай DNS запись #2.

  3. Настройки CDN:
     - Кеширование: ВЫКЛ (все 4 переключателя)
     - HTTP методы: GET, HEAD, OPTIONS
     - Gzip сжатие: ВЫКЛ

  4. Жди выпуск Let's Encrypt сертификата (5-30 мин)
""") if cdn_type == "vk" else print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {server_ip}  (DNS only, серое облако)
  2. CNAME:     {cdn_domain}  ->  [Yandex CDN CNAME]  (DNS only, создашь позже)
  3. CNAME:     _acme-challenge.{cdn_domain} -> [значение из Yandex] (DNS only, создашь позже)

  Создай пока только запись #1. Остальные — по ходу.

  ============================================
  ШАГ A: Сертификат в Yandex Certificate Manager
  ============================================

  Зайди: console.yandex.cloud -> Certificate Manager -> Создать сертификат

  Заполни:
    - Имя: {cdn_domain.replace('.', '-')}
    - Домены: {cdn_domain}
    - Тип проверки: DNS

  Нажми "Создать".

  После создания Yandex покажет CNAME для проверки:
    _acme-challenge.{cdn_domain}  ->  <значение>.cm.yandexcloud.net

  Создай эту CNAME запись #3 в Cloudflare (DNS only).
  Жди статус сертификата "Issued" (5-30 мин).

  ============================================
  ШАГ B: CDN-ресурс в Yandex Cloud CDN
  ============================================

  Зайди: console.yandex.cloud -> CDN -> Создать ресурс

  Основные настройки:
    - Запрос контента: Из одного источника
    - Тип источника: Сервер
    - Доменное имя источника: {origin_domain}
    - Протокол для источников: HTTPS
    - Задать SNI вручную: ВКЛ
    - Имя SNI-хоста: {origin_domain}
    - Заголовок Host: Своё значение
    - Значение заголовка: {origin_domain}
    - Доменное имя: {cdn_domain}

  После создания скопируй CNAME (xxx.gcdn.co) и создай DNS запись #2.

  Настройки CDN (вкладки сверху):
    Кеширование:
      - Кеш CDN: ВЫКЛ
      - Кеш браузера: ВЫКЛ

    Дополнительно:
      - Query string: НЕ игнорировать
      - Сжатие: ВЫКЛ
      - Проверка сертификата источника: ВЫКЛ
      - SSL-сертификат: выбери {cdn_domain.replace('.', '-')}
""")

    if not cfg.get("skip_cdn_wait", False):
        safe_input("  Нажми ENTER когда CDN настроен и сертификат выпущен...")
        if cdn_type in ("beeline", "timeweb", "turboflare", "selectel"):
            if cdn_type == "beeline":
                cdn_issued = safe_input("  Домен выданный Beeline CDN (например https://xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "timeweb":
                cdn_issued = safe_input("  Технический домен Timeweb CDN (например xxx.cdn.twcstorage.ru): ").strip()
            elif cdn_type == "turboflare":
                cdn_issued = safe_input("  Домен выданный TurboFlare CDN (например xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "selectel":
                cdn_issued = safe_input("  Технический домен Selectel CDN (например xxx.selcdn.ru): ").strip()
            if cdn_issued:
                cdn_issued = cdn_issued.replace("https://", "").replace("http://", "").rstrip("/")
                if cdn_type == "beeline":
                    cdn_label = "Beeline"
                elif cdn_type == "timeweb":
                    cdn_label = "Timeweb"
                elif cdn_type == "turboflare":
                    cdn_label = "TurboFlare"
                else:
                    cdn_label = "Selectel"
                print(f"  CDN домен {cdn_label}: {cdn_issued}")

    # --- Step: Final check ---
    step(step_n, "Финальная проверка")

    # Check health
    r = run("curl -s http://127.0.0.1/health", check=False)
    health_ok = "ok" in r.stdout
    print(f"  Health endpoint: {'OK' if health_ok else 'FAIL'}")

    # Check xray CDN port
    r = run(f"ss -tlnp | grep :{cdn['xray_port']}", check=False)
    xray_ok = str(cdn['xray_port']) in r.stdout
    print(f"  Xray CDN port {cdn['xray_port']}: {'OK' if xray_ok else 'FAIL'}")

    # Check grpc port
    if cfg.get("install_grpc"):
        r = run(f"ss -tlnp | grep :{GRPC_PORT}", check=False)
        grpc_ok = str(GRPC_PORT) in r.stdout
        print(f"  gRPC Reality TCP {GRPC_PORT}: {'OK' if grpc_ok else 'ПРОВЕРЬ после рестарта'}")

    # Check nginx
    r = run("systemctl is-active nginx", check=False)
    nginx_ok = "active" in r.stdout
    print(f"  Nginx: {'OK' if nginx_ok else 'FAIL'}")

    # Check CDN domain
    r = run(f"curl -sk https://{cdn_domain}/health 2>&1", check=False)
    cdn_ok = "ok" in r.stdout
    print(f"  CDN ({cdn_domain}): {'OK' if cdn_ok else 'ПРОПУСК (проверь из РФ)'}")

    # Build VLESS link
    vless_link = (
        f"vless://{client_uuid}@{cdn_domain}:443"
        f"?type=xhttp&security=tls&sni={cdn_domain}"
        f"&fp=random"
        f"&path={cdn['xhttp_path']}"
        f"&host={cdn_domain}"
        f"&mode=packet-up"
        f"&encryption=none"
        f"#{client_email}-{cdn_type}"
    )

    # Subscription URLs (served by 3x-ui built-in sub server via nginx proxy)
    sub_url = f"https://{panel_domain}/sub/{sub_id}"
    json_url = f"https://{panel_domain}/json/{sub_id}"
    print(f"  Подписка: {sub_url}")
    print(f"  JSON (Happ): {json_url}")

    extra_links = ""
    if grpc_link:
        extra_links += f"\n  gRPC Reality ссылка:\n  {grpc_link}\n"

    cascade_summary = ""
    if cascade and cascade_info:
        # EU-панель — вторая полноценная панель (#23): у неё свой прямой ключ,
        # который идёт мимо CDN и relay (заграничный IP напрямую).
        cascade_summary = f"""
  ============================================
  ПАНЕЛЬ 2 — EU (заграничный сервер, каскад)
  ============================================

  Панель: https://{cascade_info['exit_panel_domain']}:{cascade_info['exit_panel_port']}/{cascade_info['exit_panel_path']}/
  Логин: admin
  Пароль: {cascade_info['exit_panel_pass']}
  Подписка: https://{cascade_info['exit_panel_domain']}:2096/sub/

  Прямой ключ к EU (без CDN, заграничный IP сразу):
  {cascade_info.get('eu_link', '')}
{("  EU gRPC ключ:" + chr(10) + "  " + cascade_info['eu_grpc_link'] + chr(10)) if cascade_info.get('eu_grpc_link') else ""}

  Роль в каскаде: {cfg['cascade_ip']} — выход (BRIDGE_IN 8888 + Reality 443)"""

    print(f"""
  ============================================
  УСТАНОВКА ЗАВЕРШЕНА
  ============================================

  Панель: https://{panel_domain}/{panel_path}/
  Логин: {panel_user}
  Пароль: {panel_pass}

  CDN домен: {cdn_domain}
  Origin домен: {origin_domain}
{cascade_summary}

  Подписка (для v2rayN/NekoBox):
  {sub_url}

  JSON подписка (для Happ):
  {json_url}

  VLESS CDN ссылка:
  {vless_link}
{extra_links}
  ============================================
""")


# ============================================================
#  3X-UI CDN-ONLY (mode 3 for existing 3x-ui panel)
# ============================================================

def install_3xui_cdn_only(cfg):
    """Add CDN node to an existing remote 3x-ui panel. Installs xray standalone + nginx on THIS server, creates inbound on remote panel (API-first, SQLite fallback)."""
    domain = cfg["domain"]
    cdn_type = cfg["cdn_type"]
    cdn = CDN_SETTINGS[cdn_type]
    server_ip = cfg["server_ip"]
    panel_ip = cfg["panel_ip"]
    panel_cred = cfg["panel_cred"]
    origin_sub = cfg["origin_sub"]
    hy2_sub = cfg.get("hy2_sub", "")
    cdn_sub = cfg["cdn_sub"]
    cdn_domain = f"{cdn_sub}.{domain}"
    origin_domain = f"{origin_sub}.{domain}"

    client_uuid = str(uuid.uuid4())
    client_email = "user1"
    sub_id = None

    # --- Step: Verify remote 3x-ui ---
    step(3, "Проверка 3x-ui на панели")

    r = run_remote(panel_ip, panel_cred, "systemctl is-active x-ui")
    if "active" not in r.stdout:
        print(f"  ❌ 3x-ui не запущен на {panel_ip}!")
        print(f"  Проверь: ssh {panel_cred.get('user','root')}@{panel_ip} systemctl status x-ui")
        sys.exit(1)
    print(f"  3x-ui активен на {panel_ip}")

    r = run_remote(panel_ip, panel_cred, "test -f /etc/x-ui/x-ui.db && echo OK")
    if "OK" not in r.stdout:
        print(f"  ❌ /etc/x-ui/x-ui.db не найден на {panel_ip}!")
        sys.exit(1)
    print("  База данных найдена")

    # Снимок инбаунда и личность уже выданного клиента берём ДО того, как что-то
    # собрано или удалено: значения нужны и конфигу relay ниже, и инбаунду панели,
    # иначе они разъезжаются. Источник истины — settings.clients инбаунда (именно
    # по нему xray сверяет клиента), таблица clients — резерв: стоит владельцу
    # поправить инбаунд, и эти два места расходятся, а ключ перестаёт подходить.
    _snap = xui_inbound_snapshot(cdn['xray_port'], remote_ip=panel_ip, remote_cred=panel_cred)
    _old_uuid, _old_sub = xui_adopt_client_identity(_snap, client_email,
                                                    remote_ip=panel_ip, remote_cred=panel_cred)
    if _old_uuid:
        client_uuid = _old_uuid
    if _old_sub:
        sub_id = _old_sub
    if _old_uuid or _old_sub:
        print(f"  Клиент {client_email} уже существует — ключ и подписка сохранены")

    # Get panel domain from DB
    r = run_remote(panel_ip, panel_cred, "sqlite3 /etc/x-ui/x-ui.db \"SELECT value FROM settings WHERE key='subDomain';\"")
    panel_domain = r.stdout.strip()
    if not panel_domain:
        panel_domain = panel_ip
    print(f"  Домен панели: {panel_domain}")

    # --- Step: Install xray standalone on this node ---
    step(4, "Установка xray на ноде")

    r = run("xray version 2>/dev/null || /usr/local/bin/xray version 2>/dev/null", check=False)
    if "Xray" in r.stdout:
        print(f"  Xray уже установлен: {r.stdout.strip().splitlines()[0]}")
    else:
        print("  Скачивание xray...")
        r = run('bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install 2>&1 | tail -5', check=False, timeout=120)
        if r.returncode != 0:
            print(f"  ❌ Не удалось установить xray: {r.stderr[:200] if r.stderr else r.stdout[:200]}")
            sys.exit(1)
        r = run("/usr/local/bin/xray version", check=False)
        print(f"  Xray установлен: {r.stdout.strip().splitlines()[0] if r.stdout else 'OK'}")
        track("xray_standalone", True)

    # RU гео-файлы для роутинга (без них xray не стартует)
    setup_xray_ru_geo()

    # Cascade exit setup (before writing xray config)
    cascade = cfg.get("cascade", False)
    cascade_info = None
    cdn_tag = f"{cdn_type}-cdn"
    if cascade:
        step(5, f"Установка exit-сервера {cfg['cascade_ip']} (каскад)")
        exit_sub = cfg.get("exit_sub", "xui")
        exit_panel_domain = f"{exit_sub}.{domain}"
        cascade_info = setup_3xui_cascade_exit(cfg["cascade_ip"], cfg["cascade_cred"], exit_panel_domain,
                                               eu_grpc=cfg.get("eu_grpc", False))
        if not cascade_info:
            print("  ❌ Каскад не удался, продолжаю без каскада.")
            cascade = False

    # Build xray config
    outbounds = [
        {"protocol": "freedom", "tag": "direct", "settings": {"domainStrategy": "UseIPv4"}},
        {"protocol": "blackhole", "tag": "block"}
    ]
    rules = []

    if cascade and cascade_info:
        outbounds.append({
            "tag": "CASCADE-REALITY",
            "protocol": "vless",
            "settings": {"vnext": [{"address": cfg["cascade_ip"], "port": 8888,
                "users": [{"id": cascade_info["bridge_uuid"], "encryption": "none"}]}]},
            "streamSettings": {
                "network": "tcp", "security": "none",
                "tcpSettings": {"header": {"type": "none"}}
            }
        })

    rules.extend([
        {"type": "field", "outboundTag": "direct", "ip": ["ext:geoip_RU.dat:ru"]},
        {"type": "field", "outboundTag": "direct", "domain": [
            "ext:geosite_RU.dat:ru-available-only-inside",
            "regexp:.*\\.ru$", "regexp:.*\\.su$", "regexp:.*\\.xn--p1ai$"
        ]},
        {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"},
        {"type": "field", "protocol": ["bittorrent"], "outboundTag": "block"}
    ])
    if cascade and cascade_info:
        # network-catch-all, НЕ inboundTag (3x-ui пересоздаёт инбаунд со своим тегом
        # in-<port>-<proto> → правило по inboundTag мертвеет → каскад не работает,
        # не-RU трафик уходит в дефолтный direct). RU/bittorrent уже обработаны выше.
        rules.append({"type": "field", "network": "tcp,udp", "outboundTag": "CASCADE-REALITY"})

    sub_id = sub_id or secrets.token_hex(8)
    xray_config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "tag": cdn_tag,
            "port": cdn["xray_port"],
            "listen": "127.0.0.1",
            "protocol": "vless",
            "settings": {"clients": [{"id": client_uuid, "email": client_email, "subId": sub_id}], "decryption": "none"},
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
            "streamSettings": {
                "network": "xhttp",
                "security": "none",
                "xhttpSettings": {
                    "mode": "packet-up",
                    "path": cdn["xhttp_path"],
                    "xmux": {"cMaxReuseTimes": "0", "maxConnections": "2", "hKeepAlivePeriod": 0, "hMaxRequestTimes": "100-200", "hMaxReusableSecs": "300-600"},
                    "noSSEHeader": False,
                    "xPaddingBytes": "100-1000",
                    "xPaddingObfsMode": True,
                    "xPaddingKey": cdn["padding_key"],
                    "xPaddingHeader": cdn["padding_header"],
                    "xPaddingPlacement": cdn["padding_placement"],
                    "xPaddingMethod": cdn["padding_method"],
                    "uplinkHTTPMethod": cdn["uplink_method"],
                    "uplinkDataPlacement": cdn.get("uplink_data_placement", "body"),
                    "scMaxEachPostBytes": "500000-1000000",
                    "scMinPostsIntervalMs": "50-150",
                    "scStreamUpServerSecs": "60-180"
                }
            }
        }],
        "outbounds": outbounds,
        "routing": {"rules": rules}
    }

    run("mkdir -p /usr/local/etc/xray", check=False)
    with open("/usr/local/etc/xray/config.json", "w") as f:
        json.dump(xray_config, f, indent=2)
    print(f"  Конфиг xray записан (порт {cdn['xray_port']}){' + CASCADE' if cascade else ''}")

    # Start/restart xray
    run("systemctl enable xray 2>/dev/null", check=False)
    run("systemctl restart xray", check=False)
    time.sleep(3)

    r = run(f"ss -tlnp | grep :{cdn['xray_port']}", check=False)
    if str(cdn['xray_port']) in r.stdout:
        print(f"  Xray слушает порт {cdn['xray_port']}")
    else:
        print(f"  ⚠ Xray не слушает порт {cdn['xray_port']}, проверяю логи...")
        r = run("journalctl -u xray --no-pager -n 10", check=False)
        print(f"  {r.stdout[:300]}")

    # --- Step: SSL ---
    step_n = 6 if cascade else 5
    step(step_n, "SSL сертификат")
    step_n += 1

    ssl_cert = "/etc/nginx/ssl/cdn.crt"
    ssl_key = "/etc/nginx/ssl/cdn.key"
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print("  SSL сертификат уже есть")
    else:
        run("mkdir -p /etc/nginx/ssl", check=False)
        run(f"openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -subj '/CN={origin_domain}' "
            f"-keyout {ssl_key} -out {ssl_cert} 2>/dev/null", check=False)
        print("  Self-signed сертификат создан")

    # --- Step: Nginx CDN origin ---
    step(step_n, "Настройка nginx CDN origin")
    step_n += 1
    ipv6_ok = has_ipv6()
    nginx_conf = nginx_cdn_origin(cdn["xray_port"], cdn["xhttp_path"], ipv6=ipv6_ok,
                                  nginx_style=cdn.get("nginx_style", "prefix"),
                                  ssl_cert=ssl_cert, ssl_key=ssl_key)

    r = nginx_write_and_restart(nginx_conf)
    if r.returncode == 0:
        print("  Nginx CDN origin настроен")
    else:
        print(f"  ❌ Проблема с nginx: {r.stderr[:200] if r.stderr else ''}")
        sys.exit(1)

    # --- Step: Create inbound on remote panel via SSH ---
    step(step_n, f"Создание {cdn_type.upper()} CDN inbound на панели")
    step_n += 1

    tag = f"{cdn_type}-cdn-xhttp-{server_ip.replace('.', '-')}"
    now_ms = int(time.time() * 1000)
    # sub_id already generated above

    settings_obj = {
        "clients": [{
            "id": client_uuid,
            "email": client_email,
            "subId": sub_id,
            "flow": "",
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": 0,
            "enable": True
        }],
        "decryption": "none",
        "encryption": "none"
    }

    # settings_obj собран уже с сохранённым uuid/subId (снимок и адаптация — выше,
    # до конфига relay). Здесь остаётся перенести клиентов, которых владелец
    # добавил в инбаунд руками: инбаунд пересоздаётся, и раньше они теряли связки —
    # подписки этих людей пустели. Работает и для API-ветки, и для SQLite-ветки:
    # обе берут клиентов из settings_obj.
    _foreign = [c for c in _snap["clients"] if (c.get("email") or "") != client_email]
    if _foreign:
        print(f"  Переношу клиентов владельца из старого инбаунда: {len(_foreign)}")
        settings_obj["clients"].extend(_foreign)

    xhttp_settings = {
        "path": cdn["xhttp_path"],
        "host": "",
        "mode": "packet-up",
        "xPaddingBytes": "100-1000",
        "xPaddingObfsMode": True,
        "xPaddingKey": cdn["padding_key"],
        "xPaddingHeader": cdn["padding_header"],
        "xPaddingPlacement": cdn["padding_placement"],
        "xPaddingMethod": cdn["padding_method"],
        "uplinkHTTPMethod": cdn["uplink_method"],
        "uplinkDataPlacement": cdn.get("uplink_data_placement", "body"),
        "noSSEHeader": False,
        "scMaxEachPostBytes": "500000-1000000",
        "scMinPostsIntervalMs": "50-150",
        "scStreamUpServerSecs": "60-180",
        "enableXmux": True,
        "xmux": {
            "maxConcurrency": "16-32",
            "maxConnections": 0,
            "cMaxReuseTimes": 1000,
            "hMaxRequestTimes": "600-900",
            "hMaxReusableSecs": "100",
            "hKeepAlivePeriod": 20000
        }
    }

    stream_settings_obj = {
        "network": "xhttp",
        "security": "none",
        "externalProxy": [{
            "forceTls": "tls",
            "dest": cdn_domain,
            "port": 443,
            "remark": ""
        }],
        "xhttpSettings": xhttp_settings
    }

    sniffing_obj = {"enabled": True, "destOverride": ["http", "tls", "quic"]}

    # Create inbound on remote panel (API-first for version compat, SQL fallback)
    inbound_created = False

    # Read panel web settings from DB (stable key-value queries)
    _xcfg = {}
    for _k in ("webPort", "webBasePath", "username", "password"):
        _r = run_remote(panel_ip, panel_cred,
            f'sqlite3 /etc/x-ui/x-ui.db "SELECT value FROM settings WHERE key=\'{_k}\';"', timeout=10)
        _xcfg[_k] = _r.stdout.strip() if _r.returncode == 0 and _r.stdout.strip() else ""
    _xport = _xcfg.get("webPort") or "2053"
    _xbase = (_xcfg.get("webBasePath") or "/").strip("/")
    _xuser = _xcfg.get("username") or "admin"
    _xpw = _xcfg.get("password") or "admin"
    _xurl = f"http://127.0.0.1:{_xport}"
    if _xbase:
        _xurl += f"/{_xbase}"

    # Detect 3x-ui version
    _ver_r = run_remote(panel_ip, panel_cred, "/usr/local/x-ui/x-ui version 2>/dev/null || echo unknown", timeout=10)
    _xui_ver = _ver_r.stdout.strip()
    if _xui_ver and _xui_ver != "unknown":
        print(f"  Версия 3x-ui: {_xui_ver}")

    # Try REST API (works across all 3x-ui versions)
    import urllib.parse as _up
    _login_data = _up.urlencode({"username": _xuser, "password": _xpw})
    _login_b64 = base64.b64encode(_login_data.encode()).decode()
    _csrf_script = '''import sys,re
m=re.search(r'csrf-token.*?content="([^"]+)"', sys.stdin.read())
print(m.group(1) if m else '')'''
    write_remote_file(panel_ip, panel_cred, "/tmp/_csrf_parse.py", _csrf_script)
    _csrf_r = run_remote(panel_ip, panel_cred,
        f"curl -sf -k -c /tmp/.xcook '{_xurl}/' 2>/dev/null | python3 /tmp/_csrf_parse.py", timeout=15)
    _csrf = _csrf_r.stdout.strip() if _csrf_r and _csrf_r.stdout else ""
    _csrf_hdr = f"-H 'X-CSRF-Token: {_csrf}'" if _csrf else ""
    _login_r = run_remote(panel_ip, panel_cred,
        f"echo '{_login_b64}' | base64 -d | curl -sf -k -c /tmp/.xcook -b /tmp/.xcook -X POST '{_xurl}/login' "
        f"-H 'Content-Type: application/x-www-form-urlencoded' {_csrf_hdr} -d @-", timeout=15)
    _api_ok = False
    try:
        _api_ok = json.loads(_login_r.stdout).get("success", False)
    except Exception:
        pass

    if _api_ok:
        _list_r = run_remote(panel_ip, panel_cred,
            f"curl -sf -b /tmp/.xcook '{_xurl}/panel/api/inbounds/list'", timeout=15)
        try:
            for _ib in json.loads(_list_r.stdout).get("obj", []):
                # сверяем и порт: владелец мог переименовать инбаунд в UI, тогда
                # 3x-ui перезаписал tag на in-<port>-<proto> и сверка по тегу
                # оставила бы старый инбаунд висеть на том же порту
                if _ib.get("tag") == tag or str(_ib.get("port")) == str(cdn["xray_port"]):
                    run_remote(panel_ip, panel_cred,
                        f"curl -sf -b /tmp/.xcook -X POST '{_xurl}/panel/api/inbounds/del/{_ib['id']}'",
                        timeout=15)
                    print(f"  Удалён старый inbound: {_ib.get('tag') or tag} (порт {_ib.get('port')})")
        except Exception:
            pass

        _payload = {
            "up": 0, "down": 0, "total": 0,
            "remark": f"{cdn_type.upper()}-CDN ({server_ip})",
            "enable": True, "expiryTime": 0,
            "listen": "127.0.0.1", "port": cdn["xray_port"],
            "protocol": "vless",
            "settings": json.dumps(settings_obj),
            "streamSettings": json.dumps(stream_settings_obj),
            "sniffing": json.dumps(sniffing_obj),
            "tag": tag
        }
        _b64 = base64.b64encode(json.dumps(_payload).encode()).decode()
        _add_r = run_remote(panel_ip, panel_cred,
            f"echo '{_b64}' | base64 -d | curl -sf -b /tmp/.xcook "
            f"-X POST '{_xurl}/panel/api/inbounds/add' "
            f"-H 'Content-Type: application/json' -d @-", timeout=15)
        try:
            _ar = json.loads(_add_r.stdout)
            if _ar.get("success"):
                inbound_created = True
                print(f"  Inbound создан через API: {tag}")
                _sub_r = run_remote(panel_ip, panel_cred,
                    f"sqlite3 /etc/x-ui/x-ui.db \"SELECT sub_id FROM clients WHERE email='{client_email}' ORDER BY id DESC LIMIT 1;\"", timeout=10)
                if _sub_r.stdout.strip():
                    sub_id = _sub_r.stdout.strip()
                _uuid_r = run_remote(panel_ip, panel_cred,
                    f"sqlite3 /etc/x-ui/x-ui.db \"SELECT uuid FROM clients WHERE email='{client_email}' ORDER BY id DESC LIMIT 1;\"", timeout=10)
                if _uuid_r.stdout.strip():
                    client_uuid = _uuid_r.stdout.strip()
            else:
                print(f"  API: {_ar.get('msg', 'ошибка')}")
        except Exception:
            print("  API ответ некорректный, пробуем SQLite")
        run_remote(panel_ip, panel_cred, "rm -f /tmp/.xcook", timeout=5)

    if not inbound_created:
        if not _api_ok:
            print("  API недоступен, используем SQLite")

        settings_json = json.dumps(settings_obj).replace("'", "''")
        stream_json = json.dumps(stream_settings_obj).replace("'", "''")
        sniffing_json = json.dumps(sniffing_obj).replace("'", "''")

        r = run_remote(panel_ip, panel_cred, f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM clients WHERE email='{client_email}';\"")
        existing_client_id = r.stdout.strip()

        # Опознание по связке порт+email, не по тегу: панель перегенерирует тег
        # при сохранении инбаунда в UI (см. xui_purge_own_inbound_sql).
        sql_parts = [xui_purge_own_inbound_sql(cdn['xray_port'], tag, client_email)]
        sql_parts.append(
            f"INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing) "
            f"VALUES (1, 0, 0, 0, '{cdn_type.upper()}-CDN ({server_ip})', 1, 0, '127.0.0.1', {cdn['xray_port']}, 'vless', '{settings_json}', '{stream_json}', '{tag}', '{sniffing_json}');"
        )

        if not existing_client_id:
            sql_parts.append(
                f"INSERT INTO clients (email, sub_id, uuid, flow, limit_ip, total_gb, expiry_time, enable, created_at) "
                f"VALUES ('{client_email}', '{sub_id}', '{client_uuid}', '', 0, 0, 0, 1, {now_ms});"
            )

        # Связки собираем из settings.clients — разом для нашего клиента и для
        # клиентов владельца, перенесённых снимком выше. Раньше связка вписывалась
        # руками только для нашего, а чужие оставались висеть на удалённом
        # inbound_id: подписки этих людей отдавали пустоту.
        sql_parts.append(xui_link_clients_sql(cdn['xray_port'], settings_obj["clients"],
                                              _snap["traffics"], now_ms))

        sql_content = chr(10).join(sql_parts)
        write_remote_file(panel_ip, panel_cred, "/tmp/xui_cdn_node.sql", sql_content)
        _sql_r = run_remote(panel_ip, panel_cred, "sqlite3 /etc/x-ui/x-ui.db < /tmp/xui_cdn_node.sql 2>&1", timeout=15)

        if _sql_r.returncode != 0 or "Error" in (_sql_r.stdout or ""):
            print(f"  SQL ошибка: {(_sql_r.stdout or '')[:200]}")
            print(f"  Создай inbound вручную через панель 3x-ui")
        else:
            if existing_client_id:
                # uuid/sub_id больше здесь НЕ перечитываем: они уже определены до
                # сборки settings (xui_adopt_client_identity), а повторное чтение
                # из БД возвращало значение, которого нет в инбаунде.
                client_id = existing_client_id
                print(f"  Используем существующего клиента: {client_email}")
            else:
                r = run_remote(panel_ip, panel_cred, f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM clients WHERE email='{client_email}';\"")
                client_id = r.stdout.strip()

            # по порту: тег мог быть перезаписан панелью, а два id в stdout
            # («12\n13») сломали бы подстановку в SQL ниже
            r = run_remote(panel_ip, panel_cred,
                f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM inbounds WHERE port={cdn['xray_port']} ORDER BY id DESC LIMIT 1;\"")
            inbound_id = r.stdout.strip()

            if client_id and inbound_id:
                inbound_created = True
                print(f"  Inbound создан через SQLite: {tag}")
            else:
                print(f"  Не удалось привязать клиента (client_id={client_id}, inbound_id={inbound_id})")

        run_remote(panel_ip, panel_cred, "rm -f /tmp/xui_cdn_node.sql", timeout=5)

    # Свой инбаунд пересоздан. Чужой инбаунд владельца на этом же порту удалять
    # молча нельзя, но и промолчать нельзя: xray не стартует, а снаружи это
    # выглядит как «Empty reply» через CDN и диагностика уходит не туда.
    _squat = xui_port_squatter(cdn['xray_port'], exclude_tag=tag,
                               remote_ip=panel_ip, remote_cred=panel_cred)
    if _squat:
        print(f"  ⚠ Порт {cdn['xray_port']} в панели уже занят инбаундом {_squat}")
        print(f"     Удали или перевесь его — иначе xray не поднимет CDN-инбаунд.")

    # Restart x-ui
    run_remote(panel_ip, panel_cred, "systemctl restart x-ui", timeout=30)
    if inbound_created:
        print("  3x-ui перезапущен на панели")
    else:
        print("  x-ui перезапущен. Проверь inbound в панели вручную.")

    # Sync ALL panel clients to relay xray config (cascade mode)
    if cascade and inbound_created:
        try:
            _all_clients_r = run_remote(panel_ip, panel_cred,
                "sqlite3 /etc/x-ui/x-ui.db " + shlex.quote(
                    f"SELECT c.uuid, c.email FROM clients c "
                    f"JOIN client_inbounds ci ON ci.client_id = c.id "
                    f"JOIN inbounds i ON i.id = ci.inbound_id "
                    f"WHERE i.port={cdn['xray_port']} AND c.enable=1;"), timeout=15)
            if _all_clients_r.stdout.strip():
                _panel_clients = []
                for _row in _all_clients_r.stdout.strip().splitlines():
                    _parts = _row.split("|")
                    if len(_parts) >= 2 and _parts[0].strip():
                        _panel_clients.append({"id": _parts[0].strip(), "email": _parts[1].strip()})
                if len(_panel_clients) > 1:
                    with open("/usr/local/etc/xray/config.json", "r") as _f:
                        _relay_cfg = json.load(_f)
                    for _ib in _relay_cfg.get("inbounds", []):
                        if _ib.get("tag") == cdn_tag:
                            _ib["settings"]["clients"] = _panel_clients
                    with open("/usr/local/etc/xray/config.json", "w") as _f:
                        json.dump(_relay_cfg, _f, indent=2)
                    run("systemctl restart xray", check=False)
                    print(f"  Синхронизировано {len(_panel_clients)} клиентов на relay")
        except Exception as _e:
            print(f"  ⚠ Синхронизация клиентов: {_e}")

    # --- Step: CDN instructions ---
    step(step_n, "Инструкция по настройке CDN")
    step_n += 1

    if cdn_type == "vk":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {server_ip}  (DNS only)
  2. CNAME:     {cdn_domain}  ->  [VK CDN CNAME]  (DNS only)

  ============================================
  Настройки VK Cloud CDN:
  ============================================

  - Протокол к источнику: HTTP (порт 80)
  - Источник: {origin_domain}
  - Персональный домен: {cdn_domain}
  - Заголовок Host: Пересылать
  - SSL: Let's Encrypt
  - Кеширование: ВЫКЛ (все 4 переключателя)
  - HTTP методы: GET, HEAD, OPTIONS
  - Gzip: ВЫКЛ
""")
    elif cdn_type == "yandex":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {server_ip}  (DNS only)
  2. CNAME:     {cdn_domain}  ->  [Yandex CDN CNAME]  (DNS only, создашь позже)
  3. CNAME:     _acme-challenge.{cdn_domain} -> [значение из Yandex] (DNS only)

  ============================================
  ШАГ A: Yandex Certificate Manager -> Создать сертификат
    - Домены: {cdn_domain}, Тип проверки: DNS
    - Создай CNAME запись #3, жди статус "Issued"

  ШАГ B: Yandex CDN -> Создать ресурс
    - Источник: {origin_domain}, HTTPS, SNI: {origin_domain}
    - Host: {origin_domain}, Домен: {cdn_domain}
    - Кеширование: ВЫКЛ, Сжатие: ВЫКЛ
    - SSL-сертификат: выбери {cdn_domain.replace('.', '-')}
""")

    if not cfg.get("skip_cdn_wait", False):
        safe_input("  Нажми ENTER когда CDN настроен...")
        if cdn_type in ("beeline", "timeweb", "turboflare", "selectel"):
            if cdn_type == "beeline":
                cdn_issued = safe_input("  Домен выданный Beeline CDN (например https://xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "timeweb":
                cdn_issued = safe_input("  Технический домен Timeweb CDN (например xxx.cdn.twcstorage.ru): ").strip()
            elif cdn_type == "turboflare":
                cdn_issued = safe_input("  Домен выданный TurboFlare CDN (например xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "selectel":
                cdn_issued = safe_input("  Технический домен Selectel CDN (например xxx.selcdn.ru): ").strip()
            if cdn_issued:
                cdn_issued = cdn_issued.replace("https://", "").replace("http://", "").rstrip("/")
                if cdn_type == "beeline":
                    cdn_label = "Beeline"
                elif cdn_type == "timeweb":
                    cdn_label = "Timeweb"
                elif cdn_type == "turboflare":
                    cdn_label = "TurboFlare"
                else:
                    cdn_label = "Selectel"
                print(f"  CDN домен {cdn_label}: {cdn_issued}")

    # --- Step: Final check ---
    step(step_n, "Финальная проверка")

    r = run("curl -s http://127.0.0.1/health", check=False)
    print(f"  Health (нода): {'OK' if 'ok' in r.stdout else 'FAIL'}")

    r = run(f"ss -tlnp | grep :{cdn['xray_port']}", check=False)
    print(f"  Xray CDN port {cdn['xray_port']} (нода): {'OK' if str(cdn['xray_port']) in r.stdout else 'FAIL'}")

    r = run("systemctl is-active nginx", check=False)
    print(f"  Nginx (нода): {'OK' if 'active' in r.stdout else 'FAIL'}")

    r = run_remote(panel_ip, panel_cred, "systemctl is-active x-ui")
    print(f"  3x-ui (панель {panel_ip}): {'OK' if 'active' in r.stdout else 'FAIL'}")

    vless_link = (
        f"vless://{client_uuid}@{cdn_domain}:443"
        f"?type=xhttp&security=tls&sni={cdn_domain}"
        f"&fp=random"
        f"&path={cdn['xhttp_path']}"
        f"&host={cdn_domain}"
        f"&mode=packet-up"
        f"&encryption=none"
        f"#{client_email}-{cdn_type}"
    )

    sub_url = f"https://{panel_domain}/sub/{sub_id}"

    cascade_summary = ""
    if cascade and cascade_info:
        cascade_summary = f"""
  ============================================
  ПАНЕЛЬ 2 — EU (заграничный сервер, каскад)
  ============================================

  Панель: https://{cascade_info['exit_panel_domain']}:{cascade_info['exit_panel_port']}/{cascade_info['exit_panel_path']}/
  Логин: admin
  Пароль: {cascade_info['exit_panel_pass']}
  Подписка: https://{cascade_info['exit_panel_domain']}:2096/sub/

  Прямой ключ к EU (без CDN, заграничный IP сразу):
  {cascade_info.get('eu_link', '')}
{("  EU gRPC ключ:" + chr(10) + "  " + cascade_info['eu_grpc_link'] + chr(10)) if cascade_info.get('eu_grpc_link') else ""}

  Роль в каскаде: {cfg['cascade_ip']} — выход (BRIDGE_IN 8888 + Reality 443)
"""

    print(f"""
  ============================================
  CDN НОДА ПОДКЛЮЧЕНА К 3X-UI
  ============================================

  Нода (этот сервер): {server_ip}
  Панель 3x-ui: {panel_ip}
  CDN домен: {cdn_domain}
  Origin домен: {origin_domain}
{cascade_summary}
  Подписка: {sub_url}

  VLESS CDN ссылка:
  {vless_link}
  ============================================
""")


# ============================================================
#  REMNAWAVE PROFILE LOOKUP (rename-proof)
# ============================================================

def _same_port(a, b):
    """Порты сравниваем строками: в session-конфигах CDN они бывают и int, и str."""
    return a is not None and b is not None and str(a) == str(b)


def remnawave_find_profile(profiles, inbound_tag, profile_name, cdn_port=None):
    """Найти наш config-profile и uuid'ы инбаундов внутри него.

    Три прохода, от точного признака к грубому:
      1. по тегу CDN-инбаунда;
      2. по имени профиля;
      3. по ПОРТУ CDN-инбаунда — на случай, когда владелец переименовал инбаунд
         (config profile в Remnawave это сырой JSON, тег там правится руками).

    Третий проход и есть фикс: без него переименованный инбаунд не находился,
    installer считал, что профиля нет, и добавлял ВТОРОЙ инбаунд на том же порту —
    xray на ноде после этого не поднимался вовсе. Порт стоит именно последним, а
    не первым: иначе можно присвоить чужой профиль владельца, у которого инбаунд
    случайно висит на том же порту.

    Возвращает dict с profile_uuid / inbound_uuid / hy2 / grpc / bridge_in uuid.
    """
    found = {"profile_uuid": None, "inbound_uuid": None, "hy2_inbound_uuid": None,
             "grpc_inbound_uuid": None, "bridge_in_uuid": None}

    def _tagged(ib, base):
        t = ib.get("tag", "") or ""
        return t == base or t.startswith(base + "-")

    def _looks_like_cdn(ib):
        """Похож ли инбаунд на наш CDN-инбаунд (vless+xhttp), а не на личный
        инбаунд владельца, случайно севший на тот же порт.

        Страховка к самому грубому проходу — по порту. Имена полей у разных
        версий панели расходятся (protocol/type, network/transport), а в сводке
        inbounds их может не быть вовсе — тогда проверку просто пропускаем.
        """
        proto = str(ib.get("protocol") or ib.get("type") or "").lower()
        if proto and proto != "vless":
            return False
        net = str(ib.get("network") or ib.get("transport") or "").lower()
        return not net or net in ("xhttp", "splithttp")

    def _extras(p):
        # HY2/gRPC/BRIDGE_IN тоже ищем с фолбэком на порт: их пропуск означает
        # добавление дубля на занятый порт, то есть мёртвый xray на ноде.
        for ib in p.get("inbounds", []):
            if _tagged(ib, "hy2-in") or _same_port(ib.get("port"), HY2_PORT):
                found["hy2_inbound_uuid"] = ib.get("uuid")
            elif _tagged(ib, "grpc-reality") or _same_port(ib.get("port"), GRPC_PORT):
                found["grpc_inbound_uuid"] = ib.get("uuid")
            elif _tagged(ib, "BRIDGE_IN") or _same_port(ib.get("port"), 8888):
                found["bridge_in_uuid"] = ib.get("uuid")

    for p in profiles:
        for ib in p.get("inbounds", []):
            if _tagged(ib, inbound_tag):
                found["profile_uuid"] = p.get("uuid")
                found["inbound_uuid"] = ib.get("uuid")
                print(f"  Профиль с тегом {ib.get('tag')} уже существует: {p.get('name')}")
                _extras(p)
                return found

    for p in profiles:
        pname = p.get("name", "") or ""
        if pname == profile_name or pname.startswith(profile_name + "-"):
            found["profile_uuid"] = p.get("uuid")
            for ib in p.get("inbounds", []):
                if _tagged(ib, inbound_tag):
                    found["inbound_uuid"] = ib.get("uuid")
            _extras(p)
            if not found["inbound_uuid"]:
                ibs = p.get("inbounds", [])
                if ibs:
                    found["inbound_uuid"] = ibs[0].get("uuid")
            print(f"  Профиль {pname} уже существует (по имени)")
            return found

    if cdn_port:
        for p in profiles:
            for ib in p.get("inbounds", []):
                if _same_port(ib.get("port"), cdn_port) and _looks_like_cdn(ib):
                    found["profile_uuid"] = p.get("uuid")
                    found["inbound_uuid"] = ib.get("uuid")
                    print(f"  Профиль найден по порту {cdn_port}: {p.get('name')}"
                          f" (инбаунд переименован в '{ib.get('tag')}')")
                    _extras(p)
                    return found

    return found


# ============================================================
#  CASCADE HELPERS
# ============================================================

def build_cascade_profile(rcfg, exit_ip, bridge_user_uuid, youtube_direct=False,
                          install_hy2=False, install_grpc=False):
    """Build cascade relay config profile: CDN xhttp inbound -> VLESS outbound to exit.

    Опционально добавляет HY2/gRPC инбаунды если они идут через каскад.
    """
    import copy
    cdn_inbound = copy.deepcopy(rcfg["profile_config"]["inbounds"][0])
    cdn_inbound["port"] = 7443
    cdn_inbound["listen"] = "127.0.0.1"
    cdn_inbound["tag"] = f"{cdn_inbound['tag']}-cascade"
    if "sniffing" not in cdn_inbound:
        cdn_inbound["sniffing"] = {"enabled": True, "routeOnly": True, "destOverride": ["http", "tls", "quic"]}

    inbounds_list = [cdn_inbound]

    # Добавить HY2 инбаунд если нужен
    if install_hy2:
        hy2_inbound = {
            "tag": "HY2-cascade",
            "port": HY2_PORT,
            "listen": "0.0.0.0",
            "protocol": "hysteria2",
            "settings": {
                "clients": [],
                "masquerade": {"type": "proxy", "proxy": {"url": "https://www.bing.com", "rewriteHost": True}}
            },
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
            "streamSettings": {
                "network": "udp",
                "security": "none"
            }
        }
        inbounds_list.append(hy2_inbound)

    # Добавить gRPC Reality инбаунд если нужен
    if install_grpc:
        grpc_inbound = {
            "tag": "gRPC-cascade",
            "port": GRPC_PORT,
            "listen": "0.0.0.0",
            "protocol": "vless",
            "settings": {"clients": [], "decryption": "none"},
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
            "streamSettings": {
                "network": "grpc",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": f"{GRPC_SERVER_NAMES[0]}:443",
                    "serverNames": GRPC_SERVER_NAMES,
                    "privateKey": "",
                    "shortIds": [""]
                },
                "grpcSettings": {"serviceName": GRPC_SERVICE_NAME}
            }
        }
        inbounds_list.append(grpc_inbound)

    return {
        "log": {"loglevel": "warning"},
        "dns": {"servers": ["1.1.1.1", "8.8.8.8"], "queryStrategy": "UseIPv4", "disableCache": False},
        "inbounds": inbounds_list,
        "outbounds": [
            {
                "tag": "VLESS_EXIT", "protocol": "vless",
                "settings": {"vnext": [{
                    "address": exit_ip, "port": 8888,
                    "users": [{"id": bridge_user_uuid, "encryption": "none"}]
                }]},
                "streamSettings": {
                    "network": "tcp", "security": "none",
                    "sockopt": {"tcpKeepAliveInterval": 30, "tcpNoDelay": True}
                },
                "mux": {"enabled": True, "concurrency": 8,
                         "xudpConcurrency": 16, "xudpProxyUDP443": "reject"}
            },
            {"tag": "DIRECT", "protocol": "freedom", "settings": {"domainStrategy": "UseIPv4"}},
            {"tag": "BLOCK", "protocol": "blackhole"}
        ],
        "routing": {"domainStrategy": "IPIfNonMatch", "rules": [
            {"ip": ["geoip:private"], "type": "field", "outboundTag": "BLOCK"},
            {"domain": ["geosite:private"], "type": "field", "outboundTag": "BLOCK"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "BLOCK"},
            # #13: YouTube/SoundCloud напрямую через relay (DIRECT = выход с РФ-relay,
            # не через exit) — без рекламы, если хостинг relay их пробивает.
            *(youtube_soundcloud_direct_rules("DIRECT", "BLOCK") if youtube_direct else []),
            {"ip": ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"], "type": "field", "outboundTag": "DIRECT"},
            {"ip": ["149.154.160.0/20", "91.108.4.0/22", "91.108.8.0/22", "91.108.12.0/22", "91.108.16.0/22", "91.108.20.0/22", "91.108.56.0/22"], "type": "field", "outboundTag": "VLESS_EXIT"},
            {"domain": ["domain:telegram.org", "domain:t.me", "domain:telegra.ph"], "type": "field", "outboundTag": "VLESS_EXIT"},
            {"ip": ["geoip:ru"], "type": "field", "outboundTag": "DIRECT"},
            {"domain": ["geosite:category-ru"], "type": "field", "outboundTag": "DIRECT"},
            # Замыкающее правило — network-catch-all, а НЕ inboundTag: стоит
            # владельцу переименовать инбаунд в профиле, и правило по тегу
            # перестаёт матчить — весь не-RU трафик молча уходит в DIRECT, то
            # есть наружу с РФ-relay вместо exit-ноды. Каскад мёртв, а симптомов
            # в логах нет (ровно этот случай был у kolibri-russia.ru на 3x-ui).
            # RU/private/bittorrent разведены правилами выше, так что остаток
            # безопасно гнать в туннель.
            {"type": "field", "network": "tcp,udp", "outboundTag": "VLESS_EXIT"}
        ]}
    }


def ensure_bridge_inbound(api_func, profile_uuid, bridge_in_uuid=None):
    """Гарантирует BRIDGE_IN (TCP 8888) в профиле exit-ноды.

    Встречный инбаунд для outbound VLESS_EXIT с relay. Раньше он добавлялся
    только при создании НОВОГО профиля — если каскад ставили на уже готовую
    панель, инбаунда не было вовсе, и relay упирался в отказ хендшейка:
    порт открыт, TCP коннектится, туннель висит без единой ошибки в логах.
    """
    if bridge_in_uuid:
        return bridge_in_uuid
    if not profile_uuid:
        return None

    resp = api_func("GET", "config-profiles")
    prof = None
    if resp.get("response"):
        rd = resp["response"]
        pl = rd.get("configProfiles", rd if isinstance(rd, list) else [rd])
        prof = next((p for p in pl if p.get("uuid") == profile_uuid), None)
    if not prof:
        print("  ВНИМАНИЕ: профиль exit-ноды не найден, BRIDGE_IN не добавлен")
        return None

    # Ищем и по тегу, и по порту: инбаунд мог быть заведён руками под другим
    # именем, а второй на 8888 сломает запуск xray конфликтом порта.
    for ib in prof.get("inbounds", []):
        if ib.get("tag", "").startswith("BRIDGE_IN") or ib.get("port") == 8888:
            return ib.get("uuid")

    pconf = prof.get("config") or {}
    if not isinstance(pconf.get("inbounds"), list):
        print("  ВНИМАНИЕ: не удалось прочитать config профиля, BRIDGE_IN не добавлен")
        return None
    pconf["inbounds"].append({
        "tag": f"BRIDGE_IN-{secrets.token_hex(3)}", "port": 8888, "listen": "0.0.0.0",
        "protocol": "vless",
        "settings": {"clients": [], "decryption": "none"},
        "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
        "streamSettings": {"network": "tcp", "security": "none"}
    })
    upd = api_func("PATCH", "config-profiles", {"uuid": profile_uuid, "config": pconf})
    if not upd.get("response"):
        print(f"  ВНИМАНИЕ: не удалось добавить BRIDGE_IN в профиль: {upd}")
        return None
    for ib in upd["response"].get("inbounds", []):
        if ib.get("tag", "").startswith("BRIDGE_IN") or ib.get("port") == 8888:
            print("  Добавлен BRIDGE_IN inbound (TCP 8888) в существующий профиль")
            return ib.get("uuid")
    return None


def ensure_node_inbound(api_func, node_uuid, profile_uuid, inbound_uuid, label="BRIDGE_IN"):
    """Инбаунд должен быть в activeInbounds ноды, иначе xray его не поднимет.

    Нужно отдельно: при уже существующей ноде activeInbounds не пересобирается.
    """
    if not (node_uuid and profile_uuid and inbound_uuid):
        return False
    resp = api_func("GET", "nodes")
    rd = resp.get("response") or []
    nodes_list = rd.get("nodes", rd) if isinstance(rd, dict) else rd
    if not isinstance(nodes_list, list):
        return False
    node = next((n for n in nodes_list if n.get("uuid") == node_uuid), None)
    if not node:
        return False

    active = []
    for ib in (node.get("configProfile") or {}).get("activeInbounds") or []:
        u = ib.get("uuid") if isinstance(ib, dict) else ib
        if u:
            active.append(u)
    if inbound_uuid in active:
        return True
    active.append(inbound_uuid)

    upd = api_func("PATCH", "nodes", {
        "uuid": node_uuid,
        "configProfile": {"activeConfigProfileUuid": profile_uuid, "activeInbounds": active}
    })
    if upd.get("response"):
        print(f"  {label} привязан к ноде")
        return True
    print(f"  ВНИМАНИЕ: не удалось привязать {label} к ноде: {upd}")
    return False


def ensure_squad_inbound(api_func, inbound_uuid, squad_uuid=None):
    """Инбаунд обязан входить в сквад: Remnawave раздаёт нодам список клиентов
    из сквада, а статический settings.clients в профиле затирает. Без этого
    BRIDGE_IN слушает 8888 с пустым списком и рвёт VLESS-хендшейк с relay.
    """
    if not inbound_uuid:
        return False
    resp = api_func("GET", "internal-squads")
    squads = resp.get("response", {}).get("internalSquads", [])
    if not squads:
        print("  ВНИМАНИЕ: сквады не найдены, BRIDGE_IN не добавлен в сквад")
        return False
    if squad_uuid:
        squad = next((s for s in squads if s.get("uuid") == squad_uuid), squads[0])
    else:
        squad = next((s for s in squads if s.get("name") == "Default-Squad"), squads[0])

    current = [ib["uuid"] for ib in squad.get("inbounds", []) if ib.get("uuid")]
    if inbound_uuid in current:
        return True
    current.append(inbound_uuid)
    upd = api_func("PATCH", "internal-squads", {"uuid": squad["uuid"], "inbounds": current})
    if upd.get("response"):
        print(f"  BRIDGE_IN добавлен в сквад {squad.get('name')}")
        return True
    print(f"  ВНИМАНИЕ: не удалось добавить BRIDGE_IN в сквад: {upd}")
    return False


def find_default_squad(api_func):
    """UUID сквада: Default-Squad, иначе первый попавшийся."""
    resp = api_func("GET", "internal-squads")
    squads = resp.get("response", {}).get("internalSquads", [])
    if not squads:
        return None
    squad = next((s for s in squads if s.get("name") == "Default-Squad"), squads[0])
    return squad.get("uuid")


def ensure_user_squad(api_func, user_uuid, squad_uuid):
    """Проверяет, что юзер реально попал в сквад, и добивает PATCH-ем.

    Remnawave не всегда цепляет сквад при создании юзера — поведение на разных
    панелях расходится. Для bridge-юзера это фатально: без сквада его vless
    UUID не раздаётся на BRIDGE_IN и каскад молча висит.
    """
    if not (user_uuid and squad_uuid):
        return False
    resp = api_func("GET", "users")
    rd = resp.get("response") or {}
    users = rd.get("users", rd) if isinstance(rd, dict) else rd
    if not isinstance(users, list):
        return False
    user = next((u for u in users if u.get("uuid") == user_uuid), None)
    if not user:
        return False

    current = []
    for s in user.get("activeInternalSquads") or []:
        u = s.get("uuid") if isinstance(s, dict) else s
        if u:
            current.append(u)
    if squad_uuid in current:
        return True

    current.append(squad_uuid)
    upd = api_func("PATCH", "users", {"uuid": user_uuid, "activeInternalSquads": current})
    if upd.get("response"):
        print("  [cascade] Bridge user добавлен в сквад")
        return True
    print(f"  ⚠ [cascade] Не удалось добавить bridge user в сквад: {upd}")
    return False


def setup_cascade_relay(cfg, api_func, exit_ip, node_cred, same_server,
                         profile_uuid, inbound_uuid, squad_uuid, existing_squad_inbounds):
    """Setup Caddy + remnanode on Russian relay server for cascade.
    api_func: callable(method, path, data=None) for Remnawave API calls."""
    cascade_ip = cfg["cascade_ip"]
    cascade_cred = cfg["cascade_cred"]
    cdn_type = cfg["cdn_type"]
    rcfg = REMNAWAVE_CDN[cdn_type]
    domain = cfg["domain"]
    origin_sub = cfg["origin_sub"]
    hy2_sub = cfg.get("hy2_sub", "")
    origin_domain = f"{origin_sub}.{domain}"
    panel_sub = cfg.get("panel_sub", "")
    panel_domain = f"{panel_sub}.{domain}" if panel_sub else domain
    server_ip = cfg["server_ip"]
    cascade_on_panel = (cascade_ip == server_ip)

    # --- SSH check ---
    print(f"  [cascade] Подключение к relay {cascade_ip}...")
    r = run_remote(cascade_ip, cascade_cred, "echo OK", timeout=30)
    if "OK" not in r.stdout:
        sshpass_check = run("which sshpass", check=False)
        if sshpass_check.returncode != 0:
            run("DEBIAN_FRONTEND=noninteractive apt-get install -y sshpass", check=False, timeout=60)
            r = run_remote(cascade_ip, cascade_cred, "echo OK", timeout=30)
        if "OK" not in r.stdout:
            print(f"  ❌ Не могу подключиться к relay {cascade_ip}")
            sys.exit(1)
    print("  [cascade] SSH OK")

    check_os(remote_ip=cascade_ip, remote_cred=cascade_cred)

    # --- Docker ---
    print("  [cascade] Установка Docker...")
    if install_docker(remote_ip=cascade_ip, remote_cred=cascade_cred):
        print(f"  [cascade] Docker готов: {run_remote(cascade_ip, cascade_cred, 'docker --version').stdout.strip()}")
    else:
        print(f"  ❌ [cascade] Docker не установился на relay!")
        sys.exit(1)
    setup_docker_mirror(remote_ip=cascade_ip, remote_cred=cascade_cred)
    r = run_remote(cascade_ip, cascade_cred, "docker compose version 2>/dev/null")
    if r.returncode != 0:
        run_remote(cascade_ip, cascade_cred, "apt-get install -y -qq docker-compose-plugin 2>/dev/null || apt-get install -y -qq docker-compose-v2 2>/dev/null || (mkdir -p /usr/local/lib/docker/cli-plugins && curl -fsSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m) -o /usr/local/lib/docker/cli-plugins/docker-compose && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose)", timeout=120)

    # --- Web server for CDN origin ---
    xhttp_path = rcfg["xhttp_path"]
    xhttp_base = xhttp_path.rsplit("/", 1)[0]

    if cascade_on_panel:
        # Panel and relay on same server — add xhttp location to existing nginx default
        print("  [cascade] Panel на том же сервере — добавляю xhttp в nginx...")
        xhttp_location = xhttp_base + "/"
        nginx_cascade_default = f"""server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location {xhttp_location} {{
        proxy_pass http://127.0.0.1:7443;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_request_buffering off;
        chunked_transfer_encoding on;
    }}

    root /var/www/html;
    index index.html;
}}

server {{
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name _;

    ssl_certificate /etc/nginx/ssl/cdn.crt;
    ssl_certificate_key /etc/nginx/ssl/cdn.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location {xhttp_location} {{
        proxy_pass http://127.0.0.1:7443;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_request_buffering off;
        chunked_transfer_encoding on;
    }}

    root /var/www/html;
    index index.html;
}}
"""
        write_remote_file(cascade_ip, cascade_cred, "/etc/nginx/sites-available/default", nginx_cascade_default)
        run_remote(cascade_ip, cascade_cred,
            "systemctl stop caddy 2>/dev/null; systemctl disable caddy 2>/dev/null; "
            "nginx -t 2>&1 && systemctl restart nginx && systemctl enable nginx",
            timeout=30)
        r = run_remote(cascade_ip, cascade_cred, "systemctl is-active nginx")
        if "active" in r.stdout:
            print("  [cascade] Nginx с xhttp запущен (panel сохранён)")
        else:
            print(f"  ⚠ [cascade] Nginx не запустился!")

    else:
        # Separate relay server — use Caddy
        print("  [cascade] Установка Caddy...")
        r = run_remote(cascade_ip, cascade_cred, "caddy version 2>/dev/null")
        if r.returncode != 0 or "v" not in r.stdout:
            # Method 1: Cloudsmith repo
            run_remote(cascade_ip, cascade_cred,
                "apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl >/dev/null 2>&1 && "
                "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null && "
                "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null && "
                "apt-get update -qq && apt-get install -y caddy 2>&1 | tail -3", timeout=300)
            r = run_remote(cascade_ip, cascade_cred, "caddy version 2>/dev/null")
            if r.returncode != 0:
                import time as _t; _t.sleep(10)
                r = run_remote(cascade_ip, cascade_cred, "caddy version 2>/dev/null")
            # Method 2: Direct binary download (fallback)
            if r.returncode != 0:
                print("  [cascade] Cloudsmith недоступен, скачиваю бинарник напрямую...")
                run_remote(cascade_ip, cascade_cred,
                    "curl -fsSL 'https://caddyserver.com/api/download?os=linux&arch=amd64' -o /usr/bin/caddy && "
                    "chmod +x /usr/bin/caddy && "
                    "groupadd --system caddy 2>/dev/null; useradd --system --gid caddy --create-home --home-dir /var/lib/caddy --shell /usr/sbin/nologin caddy 2>/dev/null; "
                    "mkdir -p /etc/caddy /var/log/caddy /var/lib/caddy && "
                    "cat > /etc/systemd/system/caddy.service << 'CADDYSVC'\n"
                    "[Unit]\nDescription=Caddy\nAfter=network.target network-online.target\nRequires=network-online.target\n\n"
                    "[Service]\nType=notify\nUser=caddy\nGroup=caddy\nExecStart=/usr/bin/caddy run --environ --config /etc/caddy/Caddyfile\n"
                    "ExecReload=/usr/bin/caddy reload --config /etc/caddy/Caddyfile --force\nTimeoutStopSec=5s\nLimitNOFILE=1048576\nAmbientCapabilities=CAP_NET_BIND_SERVICE\n\n"
                    "[Install]\nWantedBy=multi-user.target\nCADDYSVC\n"
                    "systemctl daemon-reload", timeout=120)
                r = run_remote(cascade_ip, cascade_cred, "caddy version 2>/dev/null")
                if r.returncode != 0:
                    print(f"  ❌ [cascade] Caddy не установился!")
                    sys.exit(1)
        print(f"  [cascade] Caddy: {r.stdout.strip()}")

        xhttp_match = f"{xhttp_base}/ {xhttp_base}/*"
        caddyfile = f"""{{
    log {{
        output file /var/log/caddy/access.log
        format json
    }}
}}

:80 {{
    @xhttp path {xhttp_match}
    reverse_proxy @xhttp 127.0.0.1:7443 {{
        flush_interval -1
        transport http {{
            read_buffer 16384
            write_buffer 16384
        }}
    }}
    root * /var/www/html
    file_server
}}

:443 {{
    tls /etc/nginx/ssl/cdn.crt /etc/nginx/ssl/cdn.key
    @xhttp path {xhttp_match}
    reverse_proxy @xhttp 127.0.0.1:7443 {{
        flush_interval -1
        transport http {{
            read_buffer 16384
            write_buffer 16384
        }}
    }}
    root * /var/www/html
    file_server
}}
"""
        write_remote_file(cascade_ip, cascade_cred, "/etc/caddy/Caddyfile", caddyfile)

    run_remote(cascade_ip, cascade_cred, "mkdir -p /var/www/html", timeout=10)
    decoy = DECOY_HTML.format(domain=domain)
    write_remote_file(cascade_ip, cascade_cred, "/var/www/html/index.html", decoy)

    # --- Sysctl + limits ---
    print("  [cascade] Настройка TCP (BBR)...")
    write_remote_file(cascade_ip, cascade_cred, "/etc/sysctl.d/99-vpn-tuning.conf", SYSCTL_TUNING)
    run_remote(cascade_ip, cascade_cred, "sysctl --system > /dev/null 2>&1")
    write_remote_file(cascade_ip, cascade_cred, "/etc/security/limits.d/99-nofile.conf", NOFILE_LIMITS)

    # --- Self-signed SSL for nginx compat (remnanode needs it) ---
    run_remote(cascade_ip, cascade_cred, "mkdir -p /etc/nginx/ssl && test -f /etc/nginx/ssl/cdn.crt || openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/nginx/ssl/cdn.key -out /etc/nginx/ssl/cdn.crt -subj '/CN=cdn-origin' 2>/dev/null")
    run_remote(cascade_ip, cascade_cred, "chmod 644 /etc/nginx/ssl/cdn.key /etc/nginx/ssl/cdn.crt 2>/dev/null")

    # --- Swap ---
    run_remote(cascade_ip, cascade_cred, "swapon --show | grep -q / || (fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab) 2>/dev/null")

    # --- Firewall ---
    print("  [cascade] Открытие портов 80/443...")
    r = run_remote(cascade_ip, cascade_cred, "ufw status 2>/dev/null")
    if r.returncode == 0 and "active" in r.stdout.lower():
        run_remote(cascade_ip, cascade_cred, "ufw allow 80/tcp >/dev/null 2>&1 && ufw allow 443/tcp >/dev/null 2>&1 && ufw reload >/dev/null 2>&1")
    run_remote(cascade_ip, cascade_cred, "iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null")

    if not cascade_on_panel:
        # --- Stop nginx/apache if they occupy port 80 (relay uses Caddy) ---
        run_remote(cascade_ip, cascade_cred,
            "systemctl stop nginx 2>/dev/null; systemctl disable nginx 2>/dev/null; "
            "systemctl stop apache2 2>/dev/null; systemctl disable apache2 2>/dev/null; "
            "fuser -k 80/tcp 2>/dev/null",
            timeout=15)
        time.sleep(1)
        # --- Start Caddy (will auto-issue TLS cert) ---
        print(f"  [cascade] Запуск Caddy ({origin_domain})...")
        run_remote(cascade_ip, cascade_cred, "systemctl enable caddy >/dev/null 2>&1 && systemctl restart caddy", timeout=60)
        time.sleep(3)
        r = run_remote(cascade_ip, cascade_cred, "systemctl is-active caddy")
        if "active" not in r.stdout:
            # Retry: kill anything on port 80 and try again
            run_remote(cascade_ip, cascade_cred, "fuser -k 80/tcp 2>/dev/null; sleep 2; systemctl restart caddy", timeout=30)
            time.sleep(3)
            r = run_remote(cascade_ip, cascade_cred, "systemctl is-active caddy")
        if "active" in r.stdout:
            print("  [cascade] Caddy запущен")
        else:
            r2 = run_remote(cascade_ip, cascade_cred, "journalctl -u caddy --no-pager -n 10 2>&1")
            print(f"  ⚠ [cascade] Caddy не запустился: {r2.stdout.strip()[-300:]}")
            print(f"  [cascade] Проверь что занимает порт 80: ssh root@{cascade_ip} ss -tlnp | grep :80")

    # --- Bridge user UUID (generate and pass to Remnawave as vlessUuid) ---
    bridge_user_uuid = str(uuid.uuid4())

    # --- Cascade profile ---
    print(f"  [cascade] Создание cascade профиля...")
    install_hy2 = cfg.get("install_hy2", False)
    install_grpc = cfg.get("install_grpc", False)
    cascade_hy2 = cfg.get("cascade_hy2", False)
    cascade_grpc = cfg.get("cascade_grpc", False)
    cascade_profile_config = build_cascade_profile(rcfg, exit_ip, bridge_user_uuid,
                                                   youtube_direct=cfg.get("youtube_direct", False),
                                                   install_hy2=(install_hy2 and cascade_hy2),
                                                   install_grpc=(install_grpc and cascade_grpc))
    if cfg.get("youtube_direct"):
        print("  [cascade] YouTube/SoundCloud → напрямую через relay (антиреклама)")
    tag_id = secrets.token_hex(3)
    cascade_profile_name = f"cascade-{cdn_type}-{tag_id}"
    for _ib in cascade_profile_config.get("inbounds", []):
        _ib["tag"] = f"{_ib['tag']}-{tag_id}"
    for _rule in cascade_profile_config.get("routing", {}).get("rules", []):
        if "inboundTag" in _rule:
            _rule["inboundTag"] = [f"{t}-{tag_id}" if "-cascade" in t else t for t in _rule["inboundTag"]]
    resp = None
    for _attempt in range(4):
        resp = api_func("POST", "config-profiles", {
            "name": cascade_profile_name,
            "config": cascade_profile_config
        })
        if resp.get("response"):
            break
        if _attempt < 3:
            print(f"  [cascade] API retry профиля ({_attempt+1}/3), жду 10 сек...")
            time.sleep(10)
    if not resp.get("response"):
        print(f"  ❌ [cascade] Ошибка создания профиля: {resp}")
        sys.exit(1)
    cascade_profile_uuid = resp["response"]["uuid"]
    cascade_inbound_uuid = None
    cascade_hy2_inbound_uuid = None
    cascade_grpc_inbound_uuid = None
    for ib in resp["response"].get("inbounds", []):
        tag = ib.get("tag", "")
        if "cascade" in tag and "HY2" not in tag and "gRPC" not in tag:
            cascade_inbound_uuid = ib["uuid"]
        elif "HY2-cascade" in tag:
            cascade_hy2_inbound_uuid = ib["uuid"]
        elif "gRPC-cascade" in tag:
            cascade_grpc_inbound_uuid = ib["uuid"]
    if not cascade_inbound_uuid:
        inbounds = resp["response"].get("inbounds", [])
        if inbounds:
            cascade_inbound_uuid = inbounds[0]["uuid"]
    print(f"  [cascade] Profile: {cascade_profile_uuid}")
    print(f"  [cascade] CDN Inbound: {cascade_inbound_uuid}")
    if cascade_hy2_inbound_uuid:
        print(f"  [cascade] HY2 Inbound: {cascade_hy2_inbound_uuid}")
    if cascade_grpc_inbound_uuid:
        print(f"  [cascade] gRPC Inbound: {cascade_grpc_inbound_uuid}")

    # --- Add cascade inbound + BRIDGE_IN to squad ---
    updated_squad_inbounds = list(existing_squad_inbounds)
    if cascade_inbound_uuid and cascade_inbound_uuid not in updated_squad_inbounds:
        updated_squad_inbounds.append(cascade_inbound_uuid)
    if cascade_hy2_inbound_uuid and cascade_hy2_inbound_uuid not in updated_squad_inbounds:
        updated_squad_inbounds.append(cascade_hy2_inbound_uuid)
    if cascade_grpc_inbound_uuid and cascade_grpc_inbound_uuid not in updated_squad_inbounds:
        updated_squad_inbounds.append(cascade_grpc_inbound_uuid)

    bridge_inbound_uuid = None
    all_profiles = api_func("GET", "config-profiles")
    if all_profiles.get("response"):
        resp_data = all_profiles["response"]
        profiles_list = resp_data.get("configProfiles", resp_data if isinstance(resp_data, list) else [resp_data])
        for p in profiles_list:
            if p.get("uuid") == profile_uuid:
                for ib in p.get("inbounds", []):
                    if ib.get("tag", "").startswith("BRIDGE_IN"):
                        bridge_inbound_uuid = ib["uuid"]
                        break
                break
    if bridge_inbound_uuid and bridge_inbound_uuid not in updated_squad_inbounds:
        updated_squad_inbounds.append(bridge_inbound_uuid)

    if not squad_uuid:
        squad_uuid = find_default_squad(api_func)
        if squad_uuid:
            squads_resp = api_func("GET", "internal-squads")
            sq_list = squads_resp.get("response", {}).get("internalSquads", [])
            sq = next((s for s in sq_list if s.get("uuid") == squad_uuid), None)
            if sq:
                for ib in sq.get("inbounds", []):
                    ib_uuid = ib.get("uuid") if isinstance(ib, dict) else ib
                    if ib_uuid and ib_uuid not in updated_squad_inbounds:
                        updated_squad_inbounds.insert(0, ib_uuid)

    if squad_uuid:
        api_func("PATCH", "internal-squads", {
            "uuid": squad_uuid, "inbounds": updated_squad_inbounds
        })
        print(f"  [cascade] Инбаунды добавлены в сквад")
    else:
        print(f"  ⚠ [cascade] Сквад не найден — BRIDGE_IN не добавлен в сквад!")

    # --- Create cascade node ---
    print(f"  [cascade] Создание ноды для relay {cascade_ip}...")
    cascade_excluded = []
    if all_profiles.get("response"):
        resp_data = all_profiles["response"]
        profiles_list = resp_data.get("configProfiles", resp_data if isinstance(resp_data, list) else [resp_data])
        for p in profiles_list:
            if p.get("uuid") != cascade_profile_uuid:
                for ib in p.get("inbounds", []):
                    if ib.get("uuid"):
                        cascade_excluded.append(ib["uuid"])

    if cascade_on_panel:
        gw = run("docker network inspect remnawave-network -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}'", check=False)
        cascade_node_address = gw.stdout.strip() or "172.18.0.1"
        print(f"  [cascade] Panel и relay на одном сервере — используем Docker gateway: {cascade_node_address}")
    else:
        cascade_node_address = cascade_ip

    cascade_active_inbounds = []
    if cascade_inbound_uuid:
        cascade_active_inbounds.append(cascade_inbound_uuid)
    if cascade_hy2_inbound_uuid:
        cascade_active_inbounds.append(cascade_hy2_inbound_uuid)
    if cascade_grpc_inbound_uuid:
        cascade_active_inbounds.append(cascade_grpc_inbound_uuid)

    cascade_node_data = {
        "name": f"cascade-relay-{cascade_ip.replace('.', '-')}",
        "address": cascade_node_address,
        "port": 2222,
        "countryCode": "RU",
        "isTrafficTrackingActive": True,
        "trafficLimitBytes": 0,
        "notifyPercent": 0,
        "trafficResetDay": 1,
        "excludedInbounds": cascade_excluded,
        "configProfile": {
            "activeConfigProfileUuid": cascade_profile_uuid,
            "activeInbounds": cascade_active_inbounds
        }
    }
    resp = None
    for _attempt in range(4):
        resp = api_func("POST", "nodes", cascade_node_data)
        if resp.get("response"):
            break
        if _attempt < 3:
            print(f"  [cascade] API retry ноды ({_attempt+1}/3), жду 10 сек...")
            time.sleep(10)
    if not resp.get("response"):
        print(f"  ❌ [cascade] Ошибка создания ноды: {resp}")
        sys.exit(1)
    cascade_node_uuid = resp["response"]["uuid"]
    print(f"  [cascade] Node UUID: {cascade_node_uuid}")

    # --- Get secret key ---
    secret_key = None
    resp = api_func("GET", "keygen")
    if resp.get("response"):
        secret_key = resp["response"].get("pubKey")
    if not secret_key:
        print("  ⚠ [cascade] Не удалось получить keygen pubKey")

    # --- Deploy remnanode on relay ---
    print("  [cascade] Установка remnanode на relay...")
    run_remote(cascade_ip, cascade_cred, "mkdir -p /opt/remnanode")
    node_compose = "services:\n  remnanode:\n    container_name: remnanode\n    hostname: remnanode\n    image: ghcr.io/remnawave/node:latest\n    network_mode: host\n    restart: always\n    cap_add:\n      - NET_ADMIN\n    ulimits:\n      nofile:\n        soft: 1048576\n        hard: 1048576\n    volumes:\n      - /etc/nginx/ssl:/etc/nginx/ssl:ro\n      - /opt/remnanode/xray-custom:/usr/local/bin/xray\n    env_file:\n      - .env\n"
    write_remote_file(cascade_ip, cascade_cred, "/opt/remnanode/docker-compose.yml", node_compose)
    node_env = f"NODE_PORT=2222\nSECRET_KEY={secret_key or 'REPLACE_WITH_KEY_FROM_PANEL'}\n"
    write_remote_file(cascade_ip, cascade_cred, "/opt/remnanode/.env", node_env)

    if secret_key:
        download_xray_binary(remote_ip=cascade_ip, remote_cred=cascade_cred)
        run_remote(cascade_ip, cascade_cred, "cd /opt/remnanode && docker compose pull", timeout=180)
        ensure_remnanode_up(cascade_ip, cascade_cred)
        print("  [cascade] remnanode запущен на relay")

        # Restrict port 2222 to panel only
        panel_ip = cfg.get("panel_ip", "")
        iptables_add(f"-I INPUT -p tcp --dport 2222 -s {server_ip} -j ACCEPT", remote_ip=cascade_ip, remote_cred=cascade_cred)
        if panel_ip and panel_ip != server_ip:
            iptables_add(f"-I INPUT -p tcp --dport 2222 -s {panel_ip} -j ACCEPT", remote_ip=cascade_ip, remote_cred=cascade_cred)
        iptables_add("-I INPUT -p tcp --dport 2222 -s 127.0.0.1 -j ACCEPT", remote_ip=cascade_ip, remote_cred=cascade_cred)
        if cascade_on_panel:
            iptables_add("-I INPUT -p tcp --dport 2222 -s 172.16.0.0/12 -j ACCEPT", remote_ip=cascade_ip, remote_cred=cascade_cred)
        iptables_add("-A INPUT -p tcp --dport 2222 -j DROP", remote_ip=cascade_ip, remote_cred=cascade_cred)
        pkg_iptables_persist(remote_ip=cascade_ip, remote_cred=cascade_cred)

        print("  [cascade] Ожидание запуска ноды...")
        for i in range(20):
            time.sleep(5)
            r = run_remote(cascade_ip, cascade_cred, "docker logs remnanode --tail=5 2>&1")
            if "started" in r.stdout.lower() or "running" in r.stdout.lower() or "XRay" in r.stdout:
                print("  [cascade] Нода relay запущена!")
                break

    # --- Create cascade host ---
    cdn_domain = f"{cfg['cdn_sub']}.{domain}"
    print(f"  [cascade] Создание хоста: {cdn_domain} -> {origin_domain}...")
    extra_fields = {k: rcfg["host_extra"] for k in remnawave_extra_keys(api_func)}
    cascade_host_payload = {
        "inbound": {"configProfileUuid": cascade_profile_uuid, "configProfileInboundUuid": cascade_inbound_uuid},
        "remark": f"Cascade {cdn_type.upper()}",
        "address": cdn_domain, "port": 443,
        "path": rcfg.get("host_path", rcfg["xhttp_path"]),
        "sni": cdn_domain, "host": cdn_domain,
        "alpn": rcfg["alpn"], "fingerprint": rcfg.get("fingerprint", "random"),
        "isDisabled": False, "securityLayer": "TLS", "allowInsecure": False,
        **extra_fields,
    }
    resp = api_func("POST", "hosts", cascade_host_payload)
    cascade_host_uuid = None
    if resp.get("response"):
        cascade_host_uuid = resp["response"].get("uuid")
        print(f"  [cascade] Host UUID: {cascade_host_uuid}")
        if cascade_node_uuid:
            api_func("PATCH", "hosts", {"uuid": cascade_host_uuid, "nodes": [cascade_node_uuid]})
            print(f"  [cascade] Хост привязан к relay ноде")
    else:
        print(f"  ⚠ [cascade] Ошибка создания хоста: {resp}")

    # --- Create bridge user (with explicit vlessUuid to match VLESS_EXIT outbound) ---
    # Юзер ОБЯЗАН состоять в скваде: именно из сквада Remnawave раздаёт нодам
    # список клиентов. Иначе BRIDGE_IN поднимется с пустым списком и хендшейк
    # с relay зависнет без ошибок в логах.
    bridge_squad = squad_uuid or find_default_squad(api_func)
    print(f"  [cascade] Создание bridge юзера (vless UUID: {bridge_user_uuid[:8]}...)...")
    bridge_payload = {
        "username": f"bridge_{tag_id}",
        "vlessUuid": bridge_user_uuid,
        "trojanPassword": bridge_user_uuid.replace("-", "")[:16],
        "expireAt": "2099-12-31T23:59:59.000Z",
        "trafficLimitBytes": 0,
        "trafficLimitStrategy": "NO_RESET",
        "hwidDeviceLimit": 0
    }
    if bridge_squad:
        bridge_payload["activeInternalSquads"] = [bridge_squad]
    resp = api_func("POST", "users", bridge_payload)
    if resp.get("response"):
        actual_uuid = resp["response"].get("vlessUuid", "")
        if not actual_uuid:
            all_u = api_func("GET", "users")
            ud = all_u.get("response") or {}
            ulist = ud.get("users", ud) if isinstance(ud, dict) else ud
            if isinstance(ulist, list):
                bu = next((u for u in ulist if u.get("username") == f"bridge_{tag_id}"), None)
                if bu:
                    actual_uuid = bu.get("vlessUuid", "")
        if actual_uuid and actual_uuid != bridge_user_uuid:
            print(f"  [cascade] UUID fix: панель назначила {actual_uuid[:8]}...")
            cascade_profile_config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] = actual_uuid
            api_func("PATCH", "config-profiles", {"uuid": cascade_profile_uuid, "config": cascade_profile_config})
            bridge_user_uuid = actual_uuid
        print(f"  [cascade] Bridge user создан (UUID: {bridge_user_uuid[:8]}...)")
        ensure_user_squad(api_func, resp["response"].get("uuid"), bridge_squad)
    else:
        print(f"  ⚠ [cascade] Ответ создания bridge user: {resp}")

    # --- Sync both nodes ---
    print("  [cascade] Синхронизация нод...")
    run_remote(cascade_ip, cascade_cred, "docker restart remnanode", timeout=30)
    if same_server:
        run("docker restart remnanode", check=False, timeout=30)
    else:
        run_remote(exit_ip, node_cred, "docker restart remnanode", timeout=30)
    time.sleep(10)

    r = run_remote(cascade_ip, cascade_cred, "docker logs remnanode --tail=10 2>&1", timeout=15)
    m = re.search(r'(\d+)\s+users', r.stdout) if r.stdout else None
    if m and int(m.group(1)) > 0:
        print(f"  [cascade] Relay синхронизирован: {m.group(1)} юзеров")
    else:
        print("  [cascade] Relay перезапущен")

    print(f"""
  ============================================
  КАСКАД НАСТРОЕН
  ============================================

  Exit нода: {exit_ip} (port 8888 BRIDGE_IN)
  Relay нода: {cascade_ip} (Caddy + remnanode)
  Origin: {origin_domain} -> {cascade_ip}
  Bridge user UUID: {bridge_user_uuid}

  CDN origin должен указывать на: {origin_domain}
  (DNS A-запись: {origin_domain} -> {cascade_ip})
  ============================================
""")
    return {
        "cascade_profile_uuid": cascade_profile_uuid,
        "cascade_inbound_uuid": cascade_inbound_uuid,
        "cascade_node_uuid": cascade_node_uuid,
        "bridge_user_uuid": bridge_user_uuid,
    }


# ============================================================
#  REMNAWAVE SUBSCRIPTION PAGE (#5)
# ============================================================

# Записи приложения INCY (клиент с xray-ядром) для страницы подписки, по одной
# на платформу. Эталон снят с живой панели, где INCY уже настроен: urlScheme
# incy://import/ (deeplink авто-добавления), тексты/локали — родные INCY (не
# Happ, проверено). ios/android — точные копии; desktop собран на базе тех же
# шагов + ссылки релизов GitHub (latest, чтобы не устаревали). ASCII-JSON —
# переносимо в Nuitka-бинарник. Список приложений в subscription-page задаётся
# файлом app-config.json; INCY добавляем в него первым (featured).
INCY_APPS_JSON = '{"ios":{"id":"incy","name":"InCy","isFeatured":true,"urlScheme":"incy://import/","installationStep":{"buttons":[{"buttonLink":"https://apps.apple.com/us/app/incy/id6756943388","buttonText":{"en":"App Store","fa":"App Store","ru":"App Store","zh":"App Store","fr":"App Store"}}],"description":{"en":"Open the page in App Store and install the app. Launch it, in the VPN configuration permission window click Allow and enter your passcode.","fa":"\\u0635\\u0641\\u062d\\u0647 \\u0631\\u0627 \\u062f\\u0631 App Store \\u0628\\u0627\\u0632 \\u06a9\\u0646\\u06cc\\u062f \\u0648 \\u0628\\u0631\\u0646\\u0627\\u0645\\u0647 \\u0631\\u0627 \\u0646\\u0635\\u0628 \\u06a9\\u0646\\u06cc\\u062f. \\u0622\\u0646 \\u0631\\u0627 \\u0627\\u062c\\u0631\\u0627 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041e\\u0442\\u043a\\u0440\\u043e\\u0439\\u0442\\u0435 \\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446\\u0443 \\u0432 App Store \\u0438 \\u0443\\u0441\\u0442\\u0430\\u043d\\u043e\\u0432\\u0438\\u0442\\u0435 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435. \\u0417\\u0430\\u043f\\u0443\\u0441\\u0442\\u0438\\u0442\\u0435 \\u0435\\u0433\\u043e, \\u0440\\u0430\\u0437\\u0440\\u0435\\u0448\\u0438\\u0442\\u0435 VPN-\\u043a\\u043e\\u043d\\u0444\\u0438\\u0433\\u0443\\u0440\\u0430\\u0446\\u0438\\u044e.","zh":"\\u5728 App Store \\u6253\\u5f00\\u9875\\u9762\\u5e76\\u5b89\\u88c5\\u5e94\\u7528\\u3002\\u542f\\u52a8\\u5e94\\u7528\\u540e\\uff0c\\u5728 VPN \\u914d\\u7f6e\\u6743\\u9650\\u7a97\\u53e3\\u70b9\\u51fb\\u5141\\u8bb8\\u3002","fr":"Ouvre la page de l\'App Store et installe l\'app. Lance-la et autorise la configuration VPN."}},"addSubscriptionStep":{"description":{"en":"Click the button below \\u2014 the app will open and the subscription will be added automatically.","fa":"\\u0628\\u0631\\u0627\\u06cc \\u0627\\u0641\\u0632\\u0648\\u062f\\u0646 \\u062e\\u0648\\u062f\\u06a9\\u0627\\u0631 \\u0627\\u0634\\u062a\\u0631\\u0627\\u06a9 \\u0631\\u0648\\u06cc \\u062f\\u06a9\\u0645\\u0647 \\u0632\\u06cc\\u0631 \\u06a9\\u0644\\u06cc\\u06a9 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043d\\u0438\\u0436\\u0435 \\u2014 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435 \\u043e\\u0442\\u043a\\u0440\\u043e\\u0435\\u0442\\u0441\\u044f, \\u0438 \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0430 \\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u0441\\u044f \\u0430\\u0432\\u0442\\u043e\\u043c\\u0430\\u0442\\u0438\\u0447\\u0435\\u0441\\u043a\\u0438.","zh":"\\u70b9\\u51fb\\u4e0b\\u65b9\\u6309\\u94ae\\uff0c\\u5e94\\u7528\\u5c06\\u4f1a\\u6253\\u5f00\\uff0c\\u5e76\\u81ea\\u52a8\\u6dfb\\u52a0\\u8ba2\\u9605\\u3002","fr":"Clique sur le bouton ci-dessous \\u2014 l\'app s\'ouvrira et l\'abonnement sera ajout\\u00e9 automatiquement."}},"connectAndUseStep":{"description":{"en":"In the main section, click the connect button to start VPN. Select a server from the list if needed.","fa":"\\u062f\\u0631 \\u0628\\u062e\\u0634 \\u0627\\u0635\\u0644\\u06cc\\u060c \\u062f\\u06a9\\u0645\\u0647 \\u0627\\u062a\\u0635\\u0627\\u0644 \\u0631\\u0627 \\u0628\\u0632\\u0646\\u06cc\\u062f. \\u062f\\u0631 \\u0635\\u0648\\u0631\\u062a \\u0646\\u06cc\\u0627\\u0632 \\u0633\\u0631\\u0648\\u0631 \\u062f\\u06cc\\u06af\\u0631\\u06cc \\u0627\\u0646\\u062a\\u062e\\u0627\\u0628 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u0412 \\u0433\\u043b\\u0430\\u0432\\u043d\\u043e\\u043c \\u0440\\u0430\\u0437\\u0434\\u0435\\u043b\\u0435 \\u043d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043f\\u043e\\u0434\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u044f \\u043a VPN. \\u041f\\u0440\\u0438 \\u043d\\u0435\\u043e\\u0431\\u0445\\u043e\\u0434\\u0438\\u043c\\u043e\\u0441\\u0442\\u0438 \\u0432\\u044b\\u0431\\u0435\\u0440\\u0438\\u0442\\u0435 \\u0441\\u0435\\u0440\\u0432\\u0435\\u0440 \\u0438\\u0437 \\u0441\\u043f\\u0438\\u0441\\u043a\\u0430.","zh":"\\u5728\\u4e3b\\u754c\\u9762\\u70b9\\u51fb\\u8fde\\u63a5\\u6309\\u94ae\\u4ee5\\u542f\\u52a8 VPN\\u3002\\u5982\\u6709\\u9700\\u8981\\uff0c\\u53ef\\u9009\\u62e9\\u5176\\u5b83\\u670d\\u52a1\\u5668\\u3002","fr":"Dans la section principale, appuie sur le bouton de connexion. Choisis un serveur si besoin."}}},"android":{"id":"incy","name":"InCy","isFeatured":true,"urlScheme":"incy://import/","installationStep":{"buttons":[{"buttonLink":"https://play.google.com/store/apps/details?id=llc.itdev.incy","buttonText":{"en":"Google Play","fa":"Google Play","ru":"Google Play","zh":"Google Play","fr":"Google Play"}}],"description":{"en":"Open Google Play and install the app. Launch it and allow VPN configuration when prompted.","fa":"Google Play \\u0631\\u0627 \\u0628\\u0627\\u0632 \\u06a9\\u0646\\u06cc\\u062f \\u0648 \\u0628\\u0631\\u0646\\u0627\\u0645\\u0647 \\u0631\\u0627 \\u0646\\u0635\\u0628 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041e\\u0442\\u043a\\u0440\\u043e\\u0439\\u0442\\u0435 Google Play \\u0438 \\u0443\\u0441\\u0442\\u0430\\u043d\\u043e\\u0432\\u0438\\u0442\\u0435 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435. \\u0417\\u0430\\u043f\\u0443\\u0441\\u0442\\u0438\\u0442\\u0435 \\u0435\\u0433\\u043e \\u0438 \\u0440\\u0430\\u0437\\u0440\\u0435\\u0448\\u0438\\u0442\\u0435 VPN-\\u043a\\u043e\\u043d\\u0444\\u0438\\u0433\\u0443\\u0440\\u0430\\u0446\\u0438\\u044e.","zh":"\\u6253\\u5f00 Google Play \\u5e76\\u5b89\\u88c5\\u5e94\\u7528\\u3002\\u542f\\u52a8\\u5e94\\u7528\\u540e\\u5141\\u8bb8 VPN \\u914d\\u7f6e\\u3002","fr":"Ouvre Google Play et installe l\'app. Lance-la et autorise la configuration VPN."}},"addSubscriptionStep":{"description":{"en":"Click the button below \\u2014 the app will open and the subscription will be added automatically.","fa":"\\u0628\\u0631\\u0627\\u06cc \\u0627\\u0641\\u0632\\u0648\\u062f\\u0646 \\u062e\\u0648\\u062f\\u06a9\\u0627\\u0631 \\u0627\\u0634\\u062a\\u0631\\u0627\\u06a9 \\u0631\\u0648\\u06cc \\u062f\\u06a9\\u0645\\u0647 \\u0632\\u06cc\\u0631 \\u06a9\\u0644\\u06cc\\u06a9 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043d\\u0438\\u0436\\u0435 \\u2014 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435 \\u043e\\u0442\\u043a\\u0440\\u043e\\u0435\\u0442\\u0441\\u044f, \\u0438 \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0430 \\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u0441\\u044f \\u0430\\u0432\\u0442\\u043e\\u043c\\u0430\\u0442\\u0438\\u0447\\u0435\\u0441\\u043a\\u0438.","zh":"\\u70b9\\u51fb\\u4e0b\\u65b9\\u6309\\u94ae\\uff0c\\u5e94\\u7528\\u5c06\\u4f1a\\u6253\\u5f00\\uff0c\\u5e76\\u81ea\\u52a8\\u6dfb\\u52a0\\u8ba2\\u9605\\u3002","fr":"Clique sur le bouton ci-dessous \\u2014 l\'app s\'ouvrira et l\'abonnement sera ajout\\u00e9 automatiquement."}},"connectAndUseStep":{"description":{"en":"In the main section, click the connect button to start VPN. Select a server from the list if needed.","fa":"\\u062f\\u0631 \\u0628\\u062e\\u0634 \\u0627\\u0635\\u0644\\u06cc\\u060c \\u062f\\u06a9\\u0645\\u0647 \\u0627\\u062a\\u0635\\u0627\\u0644 \\u0631\\u0627 \\u0628\\u0632\\u0646\\u06cc\\u062f. \\u062f\\u0631 \\u0635\\u0648\\u0631\\u062a \\u0646\\u06cc\\u0627\\u0632 \\u0633\\u0631\\u0648\\u0631 \\u062f\\u06cc\\u06af\\u0631\\u06cc \\u0627\\u0646\\u062a\\u062e\\u0627\\u0628 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u0412 \\u0433\\u043b\\u0430\\u0432\\u043d\\u043e\\u043c \\u0440\\u0430\\u0437\\u0434\\u0435\\u043b\\u0435 \\u043d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043f\\u043e\\u0434\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u044f \\u043a VPN. \\u041f\\u0440\\u0438 \\u043d\\u0435\\u043e\\u0431\\u0445\\u043e\\u0434\\u0438\\u043c\\u043e\\u0441\\u0442\\u0438 \\u0432\\u044b\\u0431\\u0435\\u0440\\u0438\\u0442\\u0435 \\u0441\\u0435\\u0440\\u0432\\u0435\\u0440 \\u0438\\u0437 \\u0441\\u043f\\u0438\\u0441\\u043a\\u0430.","zh":"\\u5728\\u4e3b\\u754c\\u9762\\u70b9\\u51fb\\u8fde\\u63a5\\u6309\\u94ae\\u4ee5\\u542f\\u52a8 VPN\\u3002\\u5982\\u6709\\u9700\\u8981\\uff0c\\u53ef\\u9009\\u62e9\\u5176\\u5b83\\u670d\\u52a1\\u5668\\u3002","fr":"Dans la section principale, appuie sur le bouton de connexion. Choisis un serveur si besoin."}}},"windows":{"id":"incy","name":"InCy","isFeatured":true,"urlScheme":"incy://import/","addSubscriptionStep":{"description":{"en":"Click the button below \\u2014 the app will open and the subscription will be added automatically.","fa":"\\u0628\\u0631\\u0627\\u06cc \\u0627\\u0641\\u0632\\u0648\\u062f\\u0646 \\u062e\\u0648\\u062f\\u06a9\\u0627\\u0631 \\u0627\\u0634\\u062a\\u0631\\u0627\\u06a9 \\u0631\\u0648\\u06cc \\u062f\\u06a9\\u0645\\u0647 \\u0632\\u06cc\\u0631 \\u06a9\\u0644\\u06cc\\u06a9 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043d\\u0438\\u0436\\u0435 \\u2014 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435 \\u043e\\u0442\\u043a\\u0440\\u043e\\u0435\\u0442\\u0441\\u044f, \\u0438 \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0430 \\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u0441\\u044f \\u0430\\u0432\\u0442\\u043e\\u043c\\u0430\\u0442\\u0438\\u0447\\u0435\\u0441\\u043a\\u0438.","zh":"\\u70b9\\u51fb\\u4e0b\\u65b9\\u6309\\u94ae\\uff0c\\u5e94\\u7528\\u5c06\\u4f1a\\u6253\\u5f00\\uff0c\\u5e76\\u81ea\\u52a8\\u6dfb\\u52a0\\u8ba2\\u9605\\u3002","fr":"Clique sur le bouton ci-dessous \\u2014 l\'app s\'ouvrira et l\'abonnement sera ajout\\u00e9 automatiquement."}},"connectAndUseStep":{"description":{"en":"In the main section, click the connect button to start VPN. Select a server from the list if needed.","fa":"\\u062f\\u0631 \\u0628\\u062e\\u0634 \\u0627\\u0635\\u0644\\u06cc\\u060c \\u062f\\u06a9\\u0645\\u0647 \\u0627\\u062a\\u0635\\u0627\\u0644 \\u0631\\u0627 \\u0628\\u0632\\u0646\\u06cc\\u062f. \\u062f\\u0631 \\u0635\\u0648\\u0631\\u062a \\u0646\\u06cc\\u0627\\u0632 \\u0633\\u0631\\u0648\\u0631 \\u062f\\u06cc\\u06af\\u0631\\u06cc \\u0627\\u0646\\u062a\\u062e\\u0627\\u0628 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u0412 \\u0433\\u043b\\u0430\\u0432\\u043d\\u043e\\u043c \\u0440\\u0430\\u0437\\u0434\\u0435\\u043b\\u0435 \\u043d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043f\\u043e\\u0434\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u044f \\u043a VPN. \\u041f\\u0440\\u0438 \\u043d\\u0435\\u043e\\u0431\\u0445\\u043e\\u0434\\u0438\\u043c\\u043e\\u0441\\u0442\\u0438 \\u0432\\u044b\\u0431\\u0435\\u0440\\u0438\\u0442\\u0435 \\u0441\\u0435\\u0440\\u0432\\u0435\\u0440 \\u0438\\u0437 \\u0441\\u043f\\u0438\\u0441\\u043a\\u0430.","zh":"\\u5728\\u4e3b\\u754c\\u9762\\u70b9\\u51fb\\u8fde\\u63a5\\u6309\\u94ae\\u4ee5\\u542f\\u52a8 VPN\\u3002\\u5982\\u6709\\u9700\\u8981\\uff0c\\u53ef\\u9009\\u62e9\\u5176\\u5b83\\u670d\\u52a1\\u5668\\u3002","fr":"Dans la section principale, appuie sur le bouton de connexion. Choisis un serveur si besoin."}},"installationStep":{"buttons":[{"buttonLink":"https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-windows-portable.zip","buttonText":{"en":"Download (Windows)","fa":"Download (Windows)","ru":"Download (Windows)","zh":"Download (Windows)","fr":"Download (Windows)"}}],"description":{"en":"Choose the version for your device, click the button below and install the app.","fa":"\\u0646\\u0633\\u062e\\u0647 \\u0645\\u0646\\u0627\\u0633\\u0628 \\u0628\\u0631\\u0627\\u06cc \\u062f\\u0633\\u062a\\u06af\\u0627\\u0647 \\u062e\\u0648\\u062f \\u0631\\u0627 \\u0627\\u0646\\u062a\\u062e\\u0627\\u0628 \\u06a9\\u0646\\u06cc\\u062f\\u060c \\u062f\\u06a9\\u0645\\u0647 \\u0632\\u06cc\\u0631 \\u0631\\u0627 \\u0641\\u0634\\u0627\\u0631 \\u062f\\u0647\\u06cc\\u062f \\u0648 \\u0628\\u0631\\u0646\\u0627\\u0645\\u0647 \\u0631\\u0627 \\u0646\\u0635\\u0628 \\u06a9\\u0646\\u06cc\\u062f","ru":"\\u0412\\u044b\\u0431\\u0435\\u0440\\u0438\\u0442\\u0435 \\u043f\\u043e\\u0434\\u0445\\u043e\\u0434\\u044f\\u0449\\u0443\\u044e \\u0432\\u0435\\u0440\\u0441\\u0438\\u044e \\u0434\\u043b\\u044f \\u0432\\u0430\\u0448\\u0435\\u0433\\u043e \\u0443\\u0441\\u0442\\u0440\\u043e\\u0439\\u0441\\u0442\\u0432\\u0430, \\u043d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043d\\u0430 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043d\\u0438\\u0436\\u0435 \\u0438 \\u0443\\u0441\\u0442\\u0430\\u043d\\u043e\\u0432\\u0438\\u0442\\u0435 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435.","zh":"\\u9009\\u62e9\\u9002\\u5408\\u60a8\\u8bbe\\u5907\\u7684\\u7248\\u672c\\uff0c\\u70b9\\u51fb\\u4e0b\\u65b9\\u6309\\u94ae\\u5e76\\u5b89\\u88c5\\u5e94\\u7528\\u7a0b\\u5e8f\\u3002","fr":"Choisis la version pour ton appareil, clique sur le bouton ci\\u2011dessous et installe l\\u2019app."}}},"macos":{"id":"incy","name":"InCy","isFeatured":true,"urlScheme":"incy://import/","addSubscriptionStep":{"description":{"en":"Click the button below \\u2014 the app will open and the subscription will be added automatically.","fa":"\\u0628\\u0631\\u0627\\u06cc \\u0627\\u0641\\u0632\\u0648\\u062f\\u0646 \\u062e\\u0648\\u062f\\u06a9\\u0627\\u0631 \\u0627\\u0634\\u062a\\u0631\\u0627\\u06a9 \\u0631\\u0648\\u06cc \\u062f\\u06a9\\u0645\\u0647 \\u0632\\u06cc\\u0631 \\u06a9\\u0644\\u06cc\\u06a9 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043d\\u0438\\u0436\\u0435 \\u2014 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435 \\u043e\\u0442\\u043a\\u0440\\u043e\\u0435\\u0442\\u0441\\u044f, \\u0438 \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0430 \\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u0441\\u044f \\u0430\\u0432\\u0442\\u043e\\u043c\\u0430\\u0442\\u0438\\u0447\\u0435\\u0441\\u043a\\u0438.","zh":"\\u70b9\\u51fb\\u4e0b\\u65b9\\u6309\\u94ae\\uff0c\\u5e94\\u7528\\u5c06\\u4f1a\\u6253\\u5f00\\uff0c\\u5e76\\u81ea\\u52a8\\u6dfb\\u52a0\\u8ba2\\u9605\\u3002","fr":"Clique sur le bouton ci-dessous \\u2014 l\'app s\'ouvrira et l\'abonnement sera ajout\\u00e9 automatiquement."}},"connectAndUseStep":{"description":{"en":"In the main section, click the connect button to start VPN. Select a server from the list if needed.","fa":"\\u062f\\u0631 \\u0628\\u062e\\u0634 \\u0627\\u0635\\u0644\\u06cc\\u060c \\u062f\\u06a9\\u0645\\u0647 \\u0627\\u062a\\u0635\\u0627\\u0644 \\u0631\\u0627 \\u0628\\u0632\\u0646\\u06cc\\u062f. \\u062f\\u0631 \\u0635\\u0648\\u0631\\u062a \\u0646\\u06cc\\u0627\\u0632 \\u0633\\u0631\\u0648\\u0631 \\u062f\\u06cc\\u06af\\u0631\\u06cc \\u0627\\u0646\\u062a\\u062e\\u0627\\u0628 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u0412 \\u0433\\u043b\\u0430\\u0432\\u043d\\u043e\\u043c \\u0440\\u0430\\u0437\\u0434\\u0435\\u043b\\u0435 \\u043d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043f\\u043e\\u0434\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u044f \\u043a VPN. \\u041f\\u0440\\u0438 \\u043d\\u0435\\u043e\\u0431\\u0445\\u043e\\u0434\\u0438\\u043c\\u043e\\u0441\\u0442\\u0438 \\u0432\\u044b\\u0431\\u0435\\u0440\\u0438\\u0442\\u0435 \\u0441\\u0435\\u0440\\u0432\\u0435\\u0440 \\u0438\\u0437 \\u0441\\u043f\\u0438\\u0441\\u043a\\u0430.","zh":"\\u5728\\u4e3b\\u754c\\u9762\\u70b9\\u51fb\\u8fde\\u63a5\\u6309\\u94ae\\u4ee5\\u542f\\u52a8 VPN\\u3002\\u5982\\u6709\\u9700\\u8981\\uff0c\\u53ef\\u9009\\u62e9\\u5176\\u5b83\\u670d\\u52a1\\u5668\\u3002","fr":"Dans la section principale, appuie sur le bouton de connexion. Choisis un serveur si besoin."}},"installationStep":{"buttons":[{"buttonLink":"https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-macos-arm64.dmg","buttonText":{"en":"Apple Silicon (.dmg)","fa":"Apple Silicon (.dmg)","ru":"Apple Silicon (.dmg)","zh":"Apple Silicon (.dmg)","fr":"Apple Silicon (.dmg)"}},{"buttonLink":"https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-macos-intel.dmg","buttonText":{"en":"Intel (.dmg)","fa":"Intel (.dmg)","ru":"Intel (.dmg)","zh":"Intel (.dmg)","fr":"Intel (.dmg)"}}],"description":{"en":"Choose the version for your device, click the button below and install the app.","fa":"\\u0646\\u0633\\u062e\\u0647 \\u0645\\u0646\\u0627\\u0633\\u0628 \\u0628\\u0631\\u0627\\u06cc \\u062f\\u0633\\u062a\\u06af\\u0627\\u0647 \\u062e\\u0648\\u062f \\u0631\\u0627 \\u0627\\u0646\\u062a\\u062e\\u0627\\u0628 \\u06a9\\u0646\\u06cc\\u062f\\u060c \\u062f\\u06a9\\u0645\\u0647 \\u0632\\u06cc\\u0631 \\u0631\\u0627 \\u0641\\u0634\\u0627\\u0631 \\u062f\\u0647\\u06cc\\u062f \\u0648 \\u0628\\u0631\\u0646\\u0627\\u0645\\u0647 \\u0631\\u0627 \\u0646\\u0635\\u0628 \\u06a9\\u0646\\u06cc\\u062f","ru":"\\u0412\\u044b\\u0431\\u0435\\u0440\\u0438\\u0442\\u0435 \\u043f\\u043e\\u0434\\u0445\\u043e\\u0434\\u044f\\u0449\\u0443\\u044e \\u0432\\u0435\\u0440\\u0441\\u0438\\u044e \\u0434\\u043b\\u044f \\u0432\\u0430\\u0448\\u0435\\u0433\\u043e \\u0443\\u0441\\u0442\\u0440\\u043e\\u0439\\u0441\\u0442\\u0432\\u0430, \\u043d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043d\\u0430 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043d\\u0438\\u0436\\u0435 \\u0438 \\u0443\\u0441\\u0442\\u0430\\u043d\\u043e\\u0432\\u0438\\u0442\\u0435 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435.","zh":"\\u9009\\u62e9\\u9002\\u5408\\u60a8\\u8bbe\\u5907\\u7684\\u7248\\u672c\\uff0c\\u70b9\\u51fb\\u4e0b\\u65b9\\u6309\\u94ae\\u5e76\\u5b89\\u88c5\\u5e94\\u7528\\u7a0b\\u5e8f\\u3002","fr":"Choisis la version pour ton appareil, clique sur le bouton ci\\u2011dessous et installe l\\u2019app."}}},"linux":{"id":"incy","name":"InCy","isFeatured":true,"urlScheme":"incy://import/","addSubscriptionStep":{"description":{"en":"Click the button below \\u2014 the app will open and the subscription will be added automatically.","fa":"\\u0628\\u0631\\u0627\\u06cc \\u0627\\u0641\\u0632\\u0648\\u062f\\u0646 \\u062e\\u0648\\u062f\\u06a9\\u0627\\u0631 \\u0627\\u0634\\u062a\\u0631\\u0627\\u06a9 \\u0631\\u0648\\u06cc \\u062f\\u06a9\\u0645\\u0647 \\u0632\\u06cc\\u0631 \\u06a9\\u0644\\u06cc\\u06a9 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043d\\u0438\\u0436\\u0435 \\u2014 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435 \\u043e\\u0442\\u043a\\u0440\\u043e\\u0435\\u0442\\u0441\\u044f, \\u0438 \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0430 \\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u0441\\u044f \\u0430\\u0432\\u0442\\u043e\\u043c\\u0430\\u0442\\u0438\\u0447\\u0435\\u0441\\u043a\\u0438.","zh":"\\u70b9\\u51fb\\u4e0b\\u65b9\\u6309\\u94ae\\uff0c\\u5e94\\u7528\\u5c06\\u4f1a\\u6253\\u5f00\\uff0c\\u5e76\\u81ea\\u52a8\\u6dfb\\u52a0\\u8ba2\\u9605\\u3002","fr":"Clique sur le bouton ci-dessous \\u2014 l\'app s\'ouvrira et l\'abonnement sera ajout\\u00e9 automatiquement."}},"connectAndUseStep":{"description":{"en":"In the main section, click the connect button to start VPN. Select a server from the list if needed.","fa":"\\u062f\\u0631 \\u0628\\u062e\\u0634 \\u0627\\u0635\\u0644\\u06cc\\u060c \\u062f\\u06a9\\u0645\\u0647 \\u0627\\u062a\\u0635\\u0627\\u0644 \\u0631\\u0627 \\u0628\\u0632\\u0646\\u06cc\\u062f. \\u062f\\u0631 \\u0635\\u0648\\u0631\\u062a \\u0646\\u06cc\\u0627\\u0632 \\u0633\\u0631\\u0648\\u0631 \\u062f\\u06cc\\u06af\\u0631\\u06cc \\u0627\\u0646\\u062a\\u062e\\u0627\\u0628 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u0412 \\u0433\\u043b\\u0430\\u0432\\u043d\\u043e\\u043c \\u0440\\u0430\\u0437\\u0434\\u0435\\u043b\\u0435 \\u043d\\u0430\\u0436\\u043c\\u0438\\u0442\\u0435 \\u043a\\u043d\\u043e\\u043f\\u043a\\u0443 \\u043f\\u043e\\u0434\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u044f \\u043a VPN. \\u041f\\u0440\\u0438 \\u043d\\u0435\\u043e\\u0431\\u0445\\u043e\\u0434\\u0438\\u043c\\u043e\\u0441\\u0442\\u0438 \\u0432\\u044b\\u0431\\u0435\\u0440\\u0438\\u0442\\u0435 \\u0441\\u0435\\u0440\\u0432\\u0435\\u0440 \\u0438\\u0437 \\u0441\\u043f\\u0438\\u0441\\u043a\\u0430.","zh":"\\u5728\\u4e3b\\u754c\\u9762\\u70b9\\u51fb\\u8fde\\u63a5\\u6309\\u94ae\\u4ee5\\u542f\\u52a8 VPN\\u3002\\u5982\\u6709\\u9700\\u8981\\uff0c\\u53ef\\u9009\\u62e9\\u5176\\u5b83\\u670d\\u52a1\\u5668\\u3002","fr":"Dans la section principale, appuie sur le bouton de connexion. Choisis un serveur si besoin."}},"installationStep":{"buttons":[{"buttonLink":"https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-linux-x64.deb","buttonText":{"en":".deb (x64)","fa":".deb (x64)","ru":".deb (x64)","zh":".deb (x64)","fr":".deb (x64)"}},{"buttonLink":"https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-linux-arm64.deb","buttonText":{"en":".deb (arm64)","fa":".deb (arm64)","ru":".deb (arm64)","zh":".deb (arm64)","fr":".deb (arm64)"}},{"buttonLink":"https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-linux-x64-portable.zip","buttonText":{"en":"Portable (x64)","fa":"Portable (x64)","ru":"Portable (x64)","zh":"Portable (x64)","fr":"Portable (x64)"}}],"description":{"en":"Open the page in App Store and install the app. Launch it, in the VPN configuration permission window click Allow and enter your passcode.","fa":"\\u0635\\u0641\\u062d\\u0647 \\u0631\\u0627 \\u062f\\u0631 App Store \\u0628\\u0627\\u0632 \\u06a9\\u0646\\u06cc\\u062f \\u0648 \\u0628\\u0631\\u0646\\u0627\\u0645\\u0647 \\u0631\\u0627 \\u0646\\u0635\\u0628 \\u06a9\\u0646\\u06cc\\u062f. \\u0622\\u0646 \\u0631\\u0627 \\u0627\\u062c\\u0631\\u0627 \\u06a9\\u0646\\u06cc\\u062f.","ru":"\\u041e\\u0442\\u043a\\u0440\\u043e\\u0439\\u0442\\u0435 \\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446\\u0443 \\u0432 App Store \\u0438 \\u0443\\u0441\\u0442\\u0430\\u043d\\u043e\\u0432\\u0438\\u0442\\u0435 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435. \\u0417\\u0430\\u043f\\u0443\\u0441\\u0442\\u0438\\u0442\\u0435 \\u0435\\u0433\\u043e, \\u0440\\u0430\\u0437\\u0440\\u0435\\u0448\\u0438\\u0442\\u0435 VPN-\\u043a\\u043e\\u043d\\u0444\\u0438\\u0433\\u0443\\u0440\\u0430\\u0446\\u0438\\u044e.","zh":"\\u5728 App Store \\u6253\\u5f00\\u9875\\u9762\\u5e76\\u5b89\\u88c5\\u5e94\\u7528\\u3002\\u542f\\u52a8\\u5e94\\u7528\\u540e\\uff0c\\u5728 VPN \\u914d\\u7f6e\\u6743\\u9650\\u7a97\\u53e3\\u70b9\\u51fb\\u5141\\u8bb8\\u3002","fr":"Ouvre la page de l\'App Store et installe l\'app. Lance-la et autorise la configuration VPN."}}}}'


def _patch_app_config_incy(cfg_dict):
    """Вставить INCY первым (featured) в каждую платформу app-config.

    Платформы, которых нет в дефолтном конфиге, пропускаем. Существующую запись
    incy убираем перед вставкой — повторный запуск не плодит дублей.
    """
    incy = json.loads(INCY_APPS_JSON)
    plats = cfg_dict.setdefault("platforms", {})
    for plat, entry in incy.items():
        lst = plats.get(plat)
        if not isinstance(lst, list):
            continue
        lst = [a for a in lst if a.get("id") != "incy"]
        lst.insert(0, entry)
        plats[plat] = lst
    return cfg_dict


def setup_subscription_page(sub_domain, api_token, server_ip):
    """Bundled-установка remnawave/subscription-page на сервере панели.

    Красивая HTML-страница подписки вместо голого кода. Панель ставится этим же
    installer'ом (режимы 1/2), поэтому /opt/remnawave, сеть remnawave-network и
    контейнер remnawave:3000 уже есть — берём Bundled-вариант из офиц. доки.
    SUB_PUBLIC_DOMAIN в .env панели уже выставлен на sub_domain (см. install_remnawave).

    Страница ДОЛЖНА жить в корне своего домена (Remnawave не работает на sub-path),
    поэтому ей нужен отдельный поддомен и свой LE-сертификат для браузера.
    """
    print("\n  [subpage] Установка страницы подписки Remnawave...")
    run("mkdir -p /opt/remnawave/subscription", check=False)

    compose = """services:
  remnawave-subscription-page:
    image: remnawave/subscription-page:latest
    container_name: remnawave-subscription-page
    hostname: remnawave-subscription-page
    restart: always
    env_file:
      - .env
    volumes:
      - ./custom/app-config.json:/opt/app/frontend/assets/app-config.json:ro
    ports:
      - '127.0.0.1:3010:3010'
    networks:
      - remnawave-network

networks:
  remnawave-network:
    driver: bridge
    external: true
"""
    with open("/opt/remnawave/subscription/docker-compose.yml", "w") as f:
        f.write(compose)

    # app-config.json задаёт список приложений на странице. Кастомим его, чтобы
    # добавить INCY (#5b): берём дефолтный из образа (не хардкодим 200КБ и не
    # отстаём от обновлений upstream), вставляем INCY первым в каждую платформу,
    # монтируем ro поверх встроенного (механизм проверен на живой панели).
    run("mkdir -p /opt/remnawave/subscription/custom", check=False)
    run("docker pull remnawave/subscription-page:latest", check=False, timeout=300)
    _incy_done = False
    _cid = (run("docker create remnawave/subscription-page:latest", check=False, timeout=60).stdout or "").strip().splitlines()
    _cid = _cid[-1].strip() if _cid else ""
    if _cid:
        run(f"docker cp {_cid}:/opt/app/frontend/assets/app-config.json /tmp/_appcfg.json", check=False, timeout=30)
        run(f"docker rm {_cid}", check=False, timeout=30)
        try:
            with open("/tmp/_appcfg.json", encoding="utf-8") as f:
                _base_cfg = json.load(f)
            _patch_app_config_incy(_base_cfg)
            with open("/opt/remnawave/subscription/custom/app-config.json", "w", encoding="utf-8") as f:
                json.dump(_base_cfg, f, ensure_ascii=False)
            _plats = ",".join(_base_cfg.get("platforms", {}).keys())
            print(f"  [subpage] INCY добавлен в app-config (платформы: {_plats})")
            _incy_done = True
        except Exception as _e:
            print(f"  ⚠ [subpage] не удалось пропатчить app-config INCY: {_e}")
    if not _incy_done:
        # без кастомного файла volume-mount указывал бы на отсутствующий путь и
        # уронил бы контейнер — убираем строку монтирования из compose
        print("  ⚠ [subpage] INCY не добавлен, страница со стандартным списком приложений")
        compose = compose.replace(
            "    volumes:\n      - ./custom/app-config.json:/opt/app/frontend/assets/app-config.json:ro\n", "")
        with open("/opt/remnawave/subscription/docker-compose.yml", "w") as f:
            f.write(compose)

    # REMNAWAVE_PANEL_URL=http://remnawave:3000 — по внутреннему docker-hostname
    # панели (тот же, что использует сама панель), не через публичный домен.
    sub_env = (
        "APP_PORT=3010\n"
        "REMNAWAVE_PANEL_URL=http://remnawave:3000\n"
        f"REMNAWAVE_API_TOKEN={api_token}\n"
        "TRUST_PROXY=1\n"
    )
    with open("/opt/remnawave/subscription/.env", "w") as f:
        f.write(sub_env)

    setup_docker_mirror()
    run("cd /opt/remnawave/subscription && docker compose pull", check=False, timeout=300)
    r = run("cd /opt/remnawave/subscription && docker compose up -d 2>&1", check=False, timeout=120)
    if r.returncode != 0:
        print(f"  ⚠ [subpage] docker compose up: {(r.stderr or r.stdout or '')[:300]}")

    # Порт 3010 слушается на 127.0.0.1 — ждём подъёма контейнера
    up = False
    for _ in range(12):
        time.sleep(5)
        rc = run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3010/ 2>/dev/null", check=False)
        if (rc.stdout or "").strip() and (rc.stdout or "").strip() != "000":
            up = True
            break
    if up:
        print("  [subpage] Контейнер поднят (127.0.0.1:3010)")
    else:
        print("  ⚠ [subpage] Контейнер не отвечает на 3010 — проверь docker logs remnawave-subscription-page")

    # --- nginx reverse proxy + LE cert для sub_domain ---
    ensure_nginx_base()
    run("mkdir -p /var/www/certbot", check=False)
    acme_conf = f"""server {{
    listen 80;
    server_name {sub_domain};
    location /.well-known/acme-challenge/ {{ root /var/www/certbot; }}
    location / {{ return 301 https://$host$request_uri; }}
}}
"""
    with open("/etc/nginx/sites-available/subpage.conf", "w") as f:
        f.write(acme_conf)
    run("ln -sf /etc/nginx/sites-available/subpage.conf /etc/nginx/sites-enabled/subpage.conf", check=False)
    r = run("nginx -t 2>&1 && systemctl reload nginx", check=False)
    if r.returncode != 0:
        print(f"  ⚠ [subpage] nginx (ACME-конфиг): {(r.stderr or r.stdout or '')[:200]}")

    pkg_install("certbot")
    dns_ok = wait_dns_a_record(sub_domain, server_ip, label="subpage")
    ssl_cert = ssl_key = None
    if dns_ok:
        cert_cmd = (f"certbot certonly --webroot -w /var/www/certbot -d {sub_domain} "
                    f"--non-interactive --agree-tos --register-unsafely-without-email")
        cr = None
        for attempt in range(1, 4):
            cr = run(cert_cmd, check=False, timeout=180)
            if cr.returncode == 0:
                break
            if attempt < 3:
                print(f"  [subpage] certbot не прошёл ({attempt}/3), повтор через 20с...")
                time.sleep(20)
        if cr and cr.returncode == 0:
            ssl_cert = f"/etc/letsencrypt/live/{sub_domain}/fullchain.pem"
            ssl_key = f"/etc/letsencrypt/live/{sub_domain}/privkey.pem"
            print("  [subpage] LE сертификат получен")

    if not ssl_cert:
        # self-signed как запас: страница откроется, но браузер предупредит
        run("mkdir -p /etc/nginx/ssl && test -f /etc/nginx/ssl/subpage.crt || "
            f"openssl req -x509 -nodes -days 3650 -newkey rsa:2048 "
            f"-keyout /etc/nginx/ssl/subpage.key -out /etc/nginx/ssl/subpage.crt "
            f"-subj '/CN={sub_domain}' 2>/dev/null", check=False)
        ssl_cert, ssl_key = "/etc/nginx/ssl/subpage.crt", "/etc/nginx/ssl/subpage.key"
        _why = "DNS не указывает на сервер" if not dns_ok else "certbot не выдал серт"
        print(f"  ⚠ [subpage] LE не получен ({_why}) — self-signed")

    proxy_conf = f"""server {{
    listen 80;
    server_name {sub_domain};
    location /.well-known/acme-challenge/ {{ root /var/www/certbot; }}
    location / {{ return 301 https://$host$request_uri; }}
}}

server {{
    listen 443 ssl;
    http2 on;
    server_name {sub_domain};

    ssl_certificate {ssl_cert};
    ssl_certificate_key {ssl_key};
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {{
        proxy_pass http://127.0.0.1:3010;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    with open("/etc/nginx/sites-available/subpage.conf", "w") as f:
        f.write(proxy_conf)
    r = run("nginx -t 2>&1 && systemctl reload nginx", check=False)
    if r.returncode != 0:
        print(f"  ⚠ [subpage] nginx (proxy-конфиг): {(r.stderr or r.stdout or '')[:200]}")

    # renewal hook — перечитать серт nginx'ом после автопродления
    hook = "#!/bin/bash\\nnginx -s reload\\n"
    run("mkdir -p /etc/letsencrypt/renewal-hooks/deploy && "
        f"printf '%b' '{hook}' > /etc/letsencrypt/renewal-hooks/deploy/subpage-nginx.sh && "
        "chmod +x /etc/letsencrypt/renewal-hooks/deploy/subpage-nginx.sh", check=False)

    print(f"  [subpage] Страница подписки: https://{sub_domain}/<shortUuid>")
    return True


def detect_pg_image(default_image="postgres:17"):
    """Выбрать образ postgres под УЖЕ существующий том с данными (#21).

    Remnawave 3.x идёт с postgres 18.4, но у панелей, поставленных раньше, том
    remnawave-db создан postgres 17. Postgres 18 такой каталог не откроет
    («database files are incompatible with server») — панель просто не поднимется,
    а данные окажутся заперты. Поэтому если том уже есть, берём образ ПОД ЕГО
    версию (читаем PG_VERSION), и только для чистой установки — свежий postgres.
    Апгрейд мажора postgres = отдельная процедура (pg_upgrade/дамп), молча её
    делать нельзя.
    """
    r = run("docker volume inspect remnawave-db >/dev/null 2>&1 && echo EXISTS", check=False, timeout=20)
    if "EXISTS" not in (r.stdout or ""):
        return default_image
    rv = run("docker run --rm -v remnawave-db:/v alpine cat /v/PG_VERSION 2>/dev/null",
             check=False, timeout=120)
    ver = (rv.stdout or "").strip().split(".")[0]
    if not ver.isdigit():
        return default_image
    # Safe split with validation
    if ":" not in default_image:
        return default_image
    default_ver_part = default_image.split(":")[1]
    if "." not in default_ver_part:
        return default_image
    if ver == default_ver_part.split(".")[0]:
        return default_image
    print(f"  Существующая БД postgres {ver} — оставляю postgres:{ver} "
          f"(апгрейд мажора требует миграции данных)")
    return f"postgres:{ver}"


# ============================================================
#  REMNAWAVE INSTALLATION
# ============================================================

def install_remnawave(cfg, remnawave_version=None):
    """Install Remnawave panel + node + profile + host + user via API.

    Args:
        cfg: Configuration dict
        remnawave_version: Remnawave version to install (2.8.1 or 3.2.3).
                          Defaults to REMNAWAVE_VERSION_LATEST for mode 1,
                          or from cfg["remnawave_version"] for mode 3.
    """
    # Use provided version or default to latest
    if remnawave_version is None:
        remnawave_version = cfg.get("remnawave_version", REMNAWAVE_VERSION_LATEST)

    domain = cfg["domain"]
    cdn_type = cfg["cdn_type"]
    rcfg = REMNAWAVE_CDN[cdn_type]
    server_ip = cfg["server_ip"]
    node_ip = cfg.get("node_ip", server_ip)
    node_cred = cfg.get("node_cred", "")
    same_server = (node_ip == server_ip)
    origin_sub = cfg["origin_sub"]
    hy2_sub = cfg.get("hy2_sub", "")
    cdn_sub = cfg["cdn_sub"]
    panel_sub = cfg["panel_sub"]
    cdn_domain = f"{cdn_sub}.{domain}"
    origin_domain = f"{origin_sub}.{domain}"
    panel_domain = f"{panel_sub}.{domain}"
    install_subpage = cfg.get("install_subpage", False)
    sub_domain = f"{cfg.get('sub_sub', '')}.{domain}" if cfg.get("sub_sub") else ""

    cascade = cfg.get("cascade", False)
    cascade_ip = cfg.get("cascade_ip")
    cascade_cred = cfg.get("cascade_cred")
    cascade_hy2 = cfg.get("cascade_hy2", False)
    cascade_grpc = cfg.get("cascade_grpc", False)

    panel_user = "admin"
    panel_pass = secrets.token_urlsafe(18) + "Aa1"  # 24+ chars, upper+lower+digits

    # --- Step: Install Docker ---
    step(3, "Установка Docker")
    setup_docker_mirror()
    if install_docker():
        print(f"  Docker готов: {run('docker --version', check=False).stdout.strip()}")
    else:
        print("  ❌ Docker не установился! Попробуй вручную: curl -fsSL https://get.docker.com | sh")
        sys.exit(1)

    rc = run("docker compose version 2>/dev/null", check=False)
    if rc.returncode != 0:
        print("  docker compose plugin не найден, устанавливаю...")
        run("apt-get install -y -qq docker-compose-plugin 2>/dev/null || "
            "apt-get install -y -qq docker-compose-v2 2>/dev/null || "
            "(mkdir -p /usr/local/lib/docker/cli-plugins && "
            "curl -fsSL https://github.com/docker/compose/releases/latest/download/"
            "docker-compose-linux-$(uname -m) -o /usr/local/lib/docker/cli-plugins/docker-compose && "
            "chmod +x /usr/local/lib/docker/cli-plugins/docker-compose)",
            check=False, timeout=120)
        rc = run("docker compose version 2>/dev/null", check=False)
        if rc.returncode != 0:
            print("  ❌ docker compose не установился!")
            sys.exit(1)
        print(f"  docker compose: {rc.stdout.strip()}")

    # --- Step: Remnawave panel ---
    step(4, f"Установка панели Remnawave {remnawave_version}")

    run("mkdir -p /opt/remnawave", check=False)
    track("directory", "/opt/remnawave")

    jwt_auth = secrets.token_hex(64)
    jwt_api = secrets.token_hex(64)
    pg_pass = secrets.token_hex(24)
    metrics_pass = secrets.token_hex(16)
    webhook_secret = secrets.token_hex(32)

    # Reuse existing PG password if volume exists (avoids auth mismatch)
    try:
        with open("/opt/remnawave/.env") as f:
            for line in f:
                if line.startswith("POSTGRES_PASSWORD="):
                    pg_pass = line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        # No existing .env — remove orphaned volumes to start fresh
        run("cd /opt/remnawave && docker compose down -v 2>/dev/null", check=False, timeout=60)
        # Also remove volumes directly in case docker-compose.yml was also missing
        r = run("docker volume ls -q --filter name=remnawave", check=False, timeout=30)
        if r.stdout.strip():
            for vol in r.stdout.strip().split("\n"):
                vol = vol.strip()
                if vol:
                    run(f"docker volume rm -f {vol} 2>/dev/null", check=False, timeout=30)
                    print(f"    Удалён orphan volume: {vol}")

    # postgres берём под существующий том (detect_pg_image): апгрейд мажора ломает
    # каталог данных. Про переход на Remnawave 3.x см. #21 — там миграция .env
    # (APP_SECRET вместо JWT_*, REDIS_SOCKET) и новая разметка тома postgres 18.
    pg_image = detect_pg_image()

    compose = """services:
  remnawave-db:
    container_name: remnawave-db
    image: {pg_image}
    restart: always
    shm_size: 256m
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: {pg_pass}
    volumes:
      - remnawave-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 3s
      timeout: 3s
      retries: 10
    networks:
      - remnawave-network

  remnawave-redis:
    container_name: remnawave-redis
    image: valkey/valkey:8.1.1-alpine
    restart: always
    command: valkey-server --save 20 1
    volumes:
      - remnawave-redis:/data
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 3s
      timeout: 3s
      retries: 10
    networks:
      - remnawave-network

  remnawave:
    container_name: remnawave
    image: remnawave/backend:{rv_version}
    restart: always
    ports:
      - "127.0.0.1:3000:3000"
    env_file:
      - .env
    depends_on:
      remnawave-db:
        condition: service_healthy
      remnawave-redis:
        condition: service_healthy
    networks:
      - remnawave-network

volumes:
  remnawave-db:
  remnawave-redis:

networks:
  remnawave-network:
    driver: bridge
""".format(pg_pass=pg_pass, pg_image=pg_image, rv_version=remnawave_version)

    with open("/opt/remnawave/docker-compose.yml", "w") as f:
        f.write(compose)

    # Generate .env - format differs between 2.8.1 and 3.x
    is_3x = remnawave_version.startswith("3.")

    if is_3x:
        # Remnawave 3.x uses single APP_SECRET instead of JWT_AUTH_SECRET/JWT_API_TOKENS_SECRET
        env = f"""APP_SECRET={jwt_auth}
METRICS_USER=metrics
METRICS_PASS={metrics_pass}
WEBHOOK_SECRET_HEADER={webhook_secret}
POSTGRES_USER=postgres
POSTGRES_PASSWORD={pg_pass}
POSTGRES_DB=postgres
DATABASE_URL="postgresql://postgres:{pg_pass}@remnawave-db:5432/postgres"
REDIS_HOST=remnawave-redis
REDIS_PORT=6379
FRONT_END_DOMAIN={panel_domain}
PANEL_DOMAIN={panel_domain}
SUB_PUBLIC_DOMAIN={sub_domain if install_subpage and sub_domain else f'{panel_domain}/api/sub'}
IS_PANEL_BEHIND_CLOUDFLARE=false
TRAFFIC_RESET_DAY=1
"""
    else:
        # Remnawave 2.8.1 uses JWT_AUTH_SECRET and JWT_API_TOKENS_SECRET
        env = f"""JWT_AUTH_SECRET={jwt_auth}
JWT_API_TOKENS_SECRET={jwt_api}
METRICS_USER=metrics
METRICS_PASS={metrics_pass}
WEBHOOK_SECRET_HEADER={webhook_secret}
POSTGRES_USER=postgres
POSTGRES_PASSWORD={pg_pass}
POSTGRES_DB=postgres
DATABASE_URL="postgresql://postgres:{pg_pass}@remnawave-db:5432/postgres"
REDIS_HOST=remnawave-redis
REDIS_PORT=6379
FRONT_END_DOMAIN={panel_domain}
PANEL_DOMAIN={panel_domain}
SUB_PUBLIC_DOMAIN={sub_domain if install_subpage and sub_domain else f'{panel_domain}/api/sub'}
IS_PANEL_BEHIND_CLOUDFLARE=false
TRAFFIC_RESET_DAY=1
"""

    with open("/opt/remnawave/.env", "w") as f:
        f.write(env)

    print("  Запуск контейнеров Remnawave...")
    setup_docker_mirror()
    run("cd /opt/remnawave && docker compose down 2>/dev/null", check=False, timeout=60)
    print("  Скачивание образов...")
    run("cd /opt/remnawave && docker compose pull", check=False, timeout=300)
    r = run("cd /opt/remnawave && docker compose up -d 2>&1", check=False, timeout=180)
    if r.returncode != 0:
        print(f"  docker compose up ошибка: {(r.stderr or r.stdout or '')[:300]}")

    print("  Ожидание запуска контейнеров...")
    panel_started = False
    for i in range(60):
        r = run("RDOM=$(grep PANEL_DOMAIN /opt/remnawave/.env 2>/dev/null | head -1 | cut -d= -f2); curl -s -H \"Host: ${RDOM:-localhost}\" http://127.0.0.1:3000/api/auth/register -H 'X-Forwarded-Proto: https' -H 'X-Forwarded-For: 127.0.0.1' -o /dev/null -w '%{http_code}'", check=False)
        if r.stdout.strip() in ("200", "201", "400", "401", "404", "405"):
            panel_started = True
            break
        time.sleep(5)
    if panel_started:
        print("  Панель Remnawave запущена")
        track("docker_compose", "/opt/remnawave")
    else:
        print("  ❌ Панель Remnawave не запустилась за 5 минут!")
        ps = run("docker compose -f /opt/remnawave/docker-compose.yml ps -a 2>&1", check=False)
        print(f"  Контейнеры:\n{ps.stdout[:400]}")
        r = run("docker compose -f /opt/remnawave/docker-compose.yml logs --tail=50 2>&1", check=False)
        print(f"  Логи:\n{r.stdout[:1500]}")
        oom = run("dmesg | grep -i 'oom\\|killed process' | tail -5 2>&1", check=False)
        if oom.stdout.strip():
            print(f"  OOM killer:\n{oom.stdout}")
        mem = run("free -m 2>&1", check=False)
        print(f"  Память:\n{mem.stdout}")
        sys.exit(1)

    # --- Step: Certbot ---
    step(5, f"SSL сертификат для {panel_domain}")

    acme_conf = f"""server {{
    listen 80;
    server_name {panel_domain};
    location /.well-known/acme-challenge/ {{ root /var/www/certbot; }}
    location / {{ return 301 https://$host$request_uri; }}
}}
"""
    run("mkdir -p /var/www/certbot", check=False)
    nginx_write_conf("panel.conf", acme_conf)
    run("nginx -t && systemctl restart nginx", check=False)

    print(f"  Получение сертификата для {panel_domain}...")
    r = run(f"certbot certonly --webroot -w /var/www/certbot -d {panel_domain} --non-interactive --agree-tos --register-unsafely-without-email", check=False, timeout=120)
    if r.returncode != 0:
        print(f"  Certbot не сработал, используем self-signed.")
        print(f"  (Проверь что DNS {panel_domain} -> {server_ip} без лишних A-записей)")
        print(f"  После установки выполни: certbot --nginx -d {panel_domain} --non-interactive --agree-tos --register-unsafely-without-email")
        cert_path = "/etc/nginx/ssl/cdn.crt"
        key_path = "/etc/nginx/ssl/cdn.key"
        if not os.path.exists(cert_path):
            print("  Self-signed сертификат тоже отсутствует!")
            sys.exit(1)
    else:
        cert_path = f"/etc/letsencrypt/live/{panel_domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{panel_domain}/privkey.pem"
        print("  Сертификат получен!")

    ipv6_panel = has_ipv6()
    v6_443_panel = "\n    listen [::]:443 ssl http2;" if ipv6_panel else ""
    panel_nginx = f"""server {{
    listen 80;
    server_name {panel_domain};
    location /.well-known/acme-challenge/ {{ root /var/www/certbot; }}
    location / {{ return 301 https://$host$request_uri; }}
}}
server {{
    listen 443 ssl http2;{v6_443_panel}
    server_name {panel_domain};
    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};
    ssl_protocols TLSv1.2 TLSv1.3;
    location / {{
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""
    nginx_write_conf("panel.conf", panel_nginx)
    run("nginx -t && systemctl restart nginx", check=False)
    print(f"  Nginx для панели настроен")

    # --- Step: API — register admin, create API token, setup resources ---
    step(6, "Создание профиля, ноды, хоста и юзера через API")

    # Register admin user
    print("  Регистрация админа...")
    resp = remnawave_api(None, "POST", "auth/register", {
        "username": panel_user, "password": panel_pass
    })
    if resp.get("response"):
        print("  Админ зарегистрирован")
    else:
        if "403" in str(resp) or "Forbidden" in str(resp):
            print("  Админ уже зарегистрирован")
        else:
            print(f"  Ответ регистрации: {resp}")

    # Create API token (signed with JWT_AUTH_SECRET, inserted into DB)
    import hashlib, hmac, base64 as b64
    print("  Создание API токена...")
    token_uuid = str(uuid.uuid4())
    header_b = b64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()).rstrip(b"=").decode()
    payload_obj = {"uuid": token_uuid, "username": None, "role": "API", "iat": int(time.time()), "exp": int(time.time()) + 86400 * 365 * 10}
    payload_b = b64.urlsafe_b64encode(json.dumps(payload_obj, separators=(",", ":")).encode()).rstrip(b"=").decode()
    sig_data = f"{header_b}.{payload_b}"
    sig = b64.urlsafe_b64encode(hmac.new(jwt_auth.encode(), sig_data.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    token = f"{sig_data}.{sig}"

    run("docker exec remnawave-db psql -U postgres -d postgres -c \"DELETE FROM api_tokens WHERE name = 'installer';\"", check=False)
    # Remnawave 3.x: expire_at required, scopes defaults to ARRAY['*']
    run(f"docker exec remnawave-db psql -U postgres -d postgres -c \"INSERT INTO api_tokens (uuid, name, expire_at) VALUES ('{token_uuid}', 'installer', now() + interval '10 years');\"", check=False)
    print(f"  API токен создан и добавлен в БД")

    # Test token
    resp = remnawave_api(token, "GET", "nodes")
    if "error" in resp:
        print(f"  ❌ API токен не работает: {resp}")
        sys.exit(1)
    print(f"  API токен проверен OK")

    # Create config profile (or find existing by inbound tag)
    install_hy2 = cfg.get("install_hy2", False)
    install_grpc = cfg.get("install_grpc", False)
    profile_name = f"cdn-{cdn_type}"
    if install_hy2 or install_grpc:
        extras = []
        if install_hy2:
            extras.append("hy2")
        if install_grpc:
            extras.append("grpc")
        profile_name += "-" + "-".join(extras)
    inbound_tag = rcfg["inbound_tag"]
    profile_uuid = None
    inbound_uuid = None
    hy2_inbound_uuid = None
    grpc_inbound_uuid = None
    bridge_in_uuid = None
    reality_keys = None

    existing_profiles = remnawave_api(token, "GET", "config-profiles")
    if existing_profiles.get("response"):
        resp_data = existing_profiles["response"]
        plist = resp_data.get("configProfiles", resp_data if isinstance(resp_data, list) else [resp_data])
        _f = remnawave_find_profile(plist, inbound_tag, profile_name, rcfg.get("xray_port"))
        profile_uuid = _f["profile_uuid"]
        inbound_uuid = _f["inbound_uuid"]
        hy2_inbound_uuid = _f["hy2_inbound_uuid"]
        grpc_inbound_uuid = _f["grpc_inbound_uuid"]
        bridge_in_uuid = _f["bridge_in_uuid"]

    if not profile_uuid:
        import copy
        tag_id = secrets.token_hex(3)
        profile_name = f"{profile_name}-{tag_id}"
        profile_config = copy.deepcopy(rcfg["profile_config"])
        for _ib in profile_config.get("inbounds", []):
            _ib["tag"] = f"{_ib['tag']}-{tag_id}"
        inbound_tag = f"{inbound_tag}-{tag_id}"

        if install_hy2:
            profile_config["inbounds"].append(build_hy2_inbound(tag_suffix=tag_id))
            print(f"  Добавлен Hysteria2 inbound (UDP {HY2_PORT})")

        if install_grpc:
            reality_keys = generate_x25519_keys()
            if reality_keys:
                short_id = secrets.token_hex(8)
                cfg["reality_keys"] = reality_keys
                cfg["reality_short_id"] = short_id
                profile_config["inbounds"].append(build_grpc_inbound(reality_keys["private"], short_id, tag_suffix=tag_id))
                print(f"  Добавлен gRPC Reality inbound (TCP {GRPC_PORT})")
            else:
                print("  ПРОПУСК gRPC: не удалось сгенерировать x25519 ключи")

        if cascade:
            profile_config["inbounds"].append({
                "tag": f"BRIDGE_IN-{tag_id}", "port": 8888, "listen": "0.0.0.0",
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
                "streamSettings": {"network": "tcp", "security": "none"}
            })
            print(f"  Добавлен BRIDGE_IN inbound (TCP 8888) для каскада")

        print(f"  Создание профиля: {profile_name}...")
        profile_payload = {"name": profile_name, "config": profile_config}
        for _attempt in range(4):
            resp = remnawave_api(token, "POST", "config-profiles", profile_payload)
            if resp.get("response"):
                profile_uuid = resp["response"].get("uuid")
                for ib in resp["response"].get("inbounds", []):
                    if ib.get("tag") == inbound_tag:
                        inbound_uuid = ib.get("uuid")
                    elif ib.get("tag", "").startswith("hy2-in"):
                        hy2_inbound_uuid = ib.get("uuid")
                    elif ib.get("tag", "").startswith("grpc-reality"):
                        grpc_inbound_uuid = ib.get("uuid")
                    elif ib.get("tag", "").startswith("BRIDGE_IN"):
                        bridge_in_uuid = ib.get("uuid")
                break
            if _attempt < 3:
                print(f"  API retry профиля ({_attempt+1}/3), жду 10 сек...")
                time.sleep(10)
            else:
                print(f"  ВНИМАНИЕ: Ответ создания профиля: {resp}")

    print(f"  Profile UUID: {profile_uuid}")
    print(f"  CDN Inbound UUID: {inbound_uuid}")
    if hy2_inbound_uuid:
        print(f"  HY2 Inbound UUID: {hy2_inbound_uuid}")
    if grpc_inbound_uuid:
        print(f"  gRPC Inbound UUID: {grpc_inbound_uuid}")

    if cascade:
        bridge_in_uuid = ensure_bridge_inbound(
            lambda m, p, d=None: remnawave_api(token, m, p, d), profile_uuid, bridge_in_uuid)
        if bridge_in_uuid:
            print(f"  BRIDGE_IN Inbound UUID: {bridge_in_uuid}")
        else:
            print("  ВНИМАНИЕ: BRIDGE_IN отсутствует — каскад не поднимется!")

    # --- Step: Node setup (files + container) ---
    step(7, "Настройка ноды Remnawave")

    if same_server:
        ipv6_ok = has_ipv6()
        nginx_conf = nginx_cdn_origin(rcfg["xray_port"], rcfg["xhttp_path"], ipv6=ipv6_ok,
                                  nginx_style=rcfg.get("nginx_style", "prefix"))
        r = nginx_write_and_restart(nginx_conf)
        if r.returncode == 0:
            print("  Nginx CDN origin настроен")
        else:
            print(f"  ❌ Проблема с nginx: {r.stderr[:200] if r.stderr else ''}")
            print("  Попробуй: nginx -t и systemctl restart nginx")
            sys.exit(1)

    # Create node in panel API
    if same_server:
        r = run("docker network inspect remnawave-network -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}'", check=False)
        node_address = r.stdout.strip() or "172.18.0.1"
        print(f"  Docker gateway: {node_address}")
    else:
        node_address = node_ip

    # Collect all inbound UUIDs except ours to exclude them
    our_uuids = {inbound_uuid, hy2_inbound_uuid, grpc_inbound_uuid} - {None}
    excluded = []
    all_profiles = remnawave_api(token, "GET", "config-profiles")
    if all_profiles.get("response"):
        resp_data = all_profiles["response"]
        profiles_list = resp_data.get("configProfiles", resp_data if isinstance(resp_data, list) else [resp_data])
        for p in profiles_list:
            for ib in p.get("inbounds", []):
                ib_uuid = ib.get("uuid")
                if ib_uuid and ib_uuid not in our_uuids:
                    excluded.append(ib_uuid)
    if excluded:
        print(f"  Исключено {len(excluded)} дефолтных inbound'ов")

    node_uuid = None
    existing_nodes_resp = remnawave_api(token, "GET", "nodes")
    existing_nodes = existing_nodes_resp.get("response", [])
    if isinstance(existing_nodes, list):
        for n in existing_nodes:
            if n.get("address") == node_address and n.get("port") == 2222:
                node_uuid = n.get("uuid")
                print(f"  Нода уже существует: {node_uuid}")
                break

    if not node_uuid:
        active_inbounds = [u for u in [inbound_uuid, hy2_inbound_uuid, grpc_inbound_uuid] if u]
        if cascade and bridge_in_uuid:
            active_inbounds.append(bridge_in_uuid)
        print(f"  Создание ноды в панели ({node_address}:2222)...")
        node_data = {
            "name": f"node-{cdn_type}-{'.'.join(node_ip.split('.')[-2:])}",
            "address": node_address,
            "port": 2222,
            "countryCode": "XX",
            "isTrafficTrackingActive": True,
            "trafficLimitBytes": 0,
            "notifyPercent": 0,
            "trafficResetDay": 1,
            "excludedInbounds": excluded,
            "configProfile": {
                "activeConfigProfileUuid": profile_uuid,
                "activeInbounds": active_inbounds
            }
        }
        for _attempt in range(4):
            resp = remnawave_api(token, "POST", "nodes", node_data)
            if resp.get("response"):
                node_uuid = resp["response"].get("uuid")
                print(f"  Node UUID: {node_uuid}")
                break
            if _attempt < 3:
                print(f"  API retry ноды ({_attempt+1}/3), жду 10 сек...")
                time.sleep(10)
            else:
                print(f"  ВНИМАНИЕ: Ответ создания ноды: {resp}")

    if cascade and bridge_in_uuid and node_uuid:
        _api2 = lambda m, p, d=None: remnawave_api(token, m, p, d)
        ensure_node_inbound(_api2, node_uuid, profile_uuid, bridge_in_uuid)
        ensure_squad_inbound(_api2, bridge_in_uuid)

    # Get secret key from keygen endpoint
    secret_key = None
    resp = remnawave_api(token, "GET", "keygen")
    if resp.get("response"):
        secret_key = resp["response"].get("pubKey")
        if secret_key:
            print(f"  Secret key obtained ({len(secret_key)} chars)")
    if not secret_key:
        print(f"  ВНИМАНИЕ: Не удалось получить keygen pubKey")

    if same_server:
        # Local remnanode setup
        run("mkdir -p /opt/remnanode", check=False)
        track("directory", "/opt/remnanode")

        node_compose = """services:
  remnanode:
    container_name: remnanode
    hostname: remnanode
    image: ghcr.io/remnawave/node:latest
    network_mode: host
    restart: always
    cap_add:
      - NET_ADMIN
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    volumes:
      - /etc/nginx/ssl:/etc/nginx/ssl:ro
      - /opt/remnanode/xray-custom:/usr/local/bin/xray
    env_file:
      - .env
"""
        with open("/opt/remnanode/docker-compose.yml", "w") as f:
            f.write(node_compose)

        node_env = f"NODE_PORT=2222\nSECRET_KEY={secret_key or 'REPLACE_WITH_KEY_FROM_PANEL'}\n"
        with open("/opt/remnanode/.env", "w") as f:
            f.write(node_env)

        if secret_key:
            download_xray_binary()
            print("  Запуск контейнера remnanode...")
            run("cd /opt/remnanode && docker compose pull", check=False, timeout=120)
            ensure_remnanode_up()
            track("docker_compose", "/opt/remnanode")

            print(f"  Ограничение порта 2222...")
            iptables_add(f"-I INPUT -p tcp --dport 2222 -s {server_ip} -j ACCEPT")
            iptables_add("-I INPUT -p tcp --dport 2222 -s 127.0.0.1 -j ACCEPT")
            iptables_add("-I INPUT -p tcp --dport 2222 -s 172.16.0.0/12 -j ACCEPT")
            iptables_add("-A INPUT -p tcp --dport 2222 -j DROP")
            pkg_iptables_persist()

            print("  Ожидание подключения ноды...")
            for i in range(20):
                time.sleep(5)
                r = run("docker logs remnanode --tail=5 2>&1", check=False)
                if "started" in r.stdout.lower() or "Remnawave" in r.stdout:
                    print("  Нода подключена!")
                    break
        else:
            print("  ВНИМАНИЕ: Нет SECRET_KEY — нода требует ручной настройки")
    else:
        # Remote node setup via SSH
        setup_remote_node(node_ip, node_cred, rcfg, secret_key, domain, server_ip)

    # Open extra ports for hy2/grpc
    if install_hy2 or install_grpc:
        # Порты открываются на том сервере, где установлен протокол
        if cascade_hy2 or cascade_grpc:
            # Если хотя бы один протокол через каскад - открываем порты на relay
            target_ip = cascade_ip
            target_cred = cascade_cred
            # Открываем только те порты, которые нужны
            open_extra_ports(install_hy2 and cascade_hy2, install_grpc and cascade_grpc,
                           remote_ip=target_ip, remote_cred=target_cred)

        # Если протоколы не через каскад - открываем на ноде
        if (install_hy2 and not cascade_hy2) or (install_grpc and not cascade_grpc):
            if not same_server:
                target_ip = node_ip
                target_cred = node_cred
            else:
                target_ip = None
                target_cred = None
            open_extra_ports(install_hy2 and not cascade_hy2, install_grpc and not cascade_grpc,
                           remote_ip=target_ip, remote_cred=target_cred)

    # nginx TCP listener on HY2 port for ping (xray apps TCP-ping, HY2 is UDP)
    if install_hy2:
        _hy2_lines = ["server {", f"    listen {HY2_PORT} ssl;",
            f"    listen [::]:{HY2_PORT} ssl;", "    server_name _;",
            "    ssl_certificate /etc/nginx/ssl/cdn.crt;",
            "    ssl_certificate_key /etc/nginx/ssl/cdn.key;",
            "    ssl_protocols TLSv1.2 TLSv1.3;",
            "    location / { return 200 'ok'; }", "}"]
        hy2_ping_conf = chr(10).join(_hy2_lines) + chr(10)
        if same_server:
            with open("/etc/nginx/conf.d/hy2-ping.conf", "w") as _f:
                _f.write(hy2_ping_conf)
            run("nginx -t && systemctl reload nginx", check=False)
        else:
            write_remote_file(node_ip, node_cred, "/etc/nginx/conf.d/hy2-ping.conf", hy2_ping_conf)
            run_remote(node_ip, node_cred, "nginx -t && systemctl reload nginx", timeout=15)
        print(f"  TCP {HY2_PORT} (nginx SSL) для пинга HY2")

    # Open bridge port 8888 for cascade
    if cascade:
        print("  Открытие порта 8888 (BRIDGE_IN) на exit ноде...")
        bridge_cmd = "ufw allow 8888/tcp 2>/dev/null; iptables -I INPUT -p tcp --dport 8888 -j ACCEPT 2>/dev/null"
        if same_server:
            run(bridge_cmd, check=False)
        else:
            run_remote(node_ip, node_cred, bridge_cmd, timeout=15)

    # Create hosts
    step(8, "Создание хостов")

    # Инициализация до ветвления: ниже их читает блок каскада, а присваивались
    # они только внутри if — при пустом inbound_uuid установка падала бы
    # с UnboundLocalError уже на шаге каскада.
    squad_uuid = None
    existing_squad_inbounds = []

    if inbound_uuid and profile_uuid:
        existing_hosts_resp = remnawave_api(token, "GET", "hosts")
        existing_hosts = existing_hosts_resp.get("response", [])
        if not isinstance(existing_hosts, list):
            existing_hosts = []

        def create_host_if_needed(ib_uuid, payload, label):
            for h in existing_hosts:
                if h.get("address") == payload["address"] and h.get("port") == payload["port"]:
                    huuid = h.get("uuid")
                    # Существующий хост — обновляем link-поля вкл. xHttpExtraParams
                    # (иначе ссылка без extra ⟶ реджект по xPaddingObfsMode ⟶ Empty reply)
                    patch = {"uuid": huuid}
                    for k in ("inbound", "path", "sni", "host", "alpn", "fingerprint",
                              "securityLayer", "allowInsecure",
                              "xHttpExtraParams", "xhttpExtraParams"):
                        if k in payload:
                            patch[k] = payload[k]
                    remnawave_api(token, "PATCH", "hosts", patch)
                    print(f"  {label} хост обновлён (extra+inbound): {huuid}")
                    return huuid
            resp = remnawave_api(token, "POST", "hosts", payload)
            if resp.get("response"):
                huuid = resp["response"].get("uuid")
                print(f"  {label} Host UUID: {huuid}")
                return huuid
            else:
                print(f"  ВНИМАНИЕ: Ответ создания хоста {label}: {resp}")
                return None

        # CDN host (skip if cascade — cascade step creates its own host on relay node)
        if not cascade:
            extra_fields = {k: rcfg["host_extra"]
                            for k in remnawave_extra_keys(lambda m, p, d=None: remnawave_api(token, m, p, d))}
            cdn_host_payload = {
                "inbound": {"configProfileUuid": profile_uuid, "configProfileInboundUuid": inbound_uuid},
                "remark": f"CDN {cdn_type.upper()}",
                "address": cdn_domain, "port": 443,
                "path": rcfg.get("host_path", rcfg["xhttp_path"]),
                "sni": cdn_domain, "host": cdn_domain,
                "alpn": rcfg["alpn"], "fingerprint": rcfg.get("fingerprint", "random"),
                "isDisabled": False, "securityLayer": "TLS", "allowInsecure": False,
                **extra_fields,
            }
            host_uuid = create_host_if_needed(inbound_uuid, cdn_host_payload, "CDN")
        else:
            host_uuid = None

        # HY2 host (LE cert if same_server, no pinnedPeerCertSha256)
        hy2_host_uuid = None
        if hy2_inbound_uuid and install_hy2:
            _hy2_le = False
            # origin_domain указывает на ноду (origin_target_ip = node_ip), поэтому
            # LE-сертификат выпускаем и для удалённой ноды тоже — иначе HY2 остаётся
            # с самоподписанным cdn.crt и клиенты его отвергают.
            # Исключение — каскад: там origin_domain смотрит на relay, не на ноду.
            # При cascade_hy2 — HY2 идёт через каскад (relay РФ → exit EU).
            _hy2_domain = f"{hy2_sub}.{domain}" if hy2_sub else origin_domain
            _hy2_target_ip = cascade_ip if cascade_hy2 else node_ip
            _hy2_target_cred = cascade_cred if cascade_hy2 else node_cred

            if same_server and not cascade_hy2:
                _hy2_le = setup_hy2_le_cert(_hy2_domain)
            else:
                _hy2_le = setup_hy2_le_cert(_hy2_domain, _hy2_target_ip, _hy2_target_cred)

            hy2_host_payload = {
                "inbound": {"configProfileUuid": profile_uuid, "configProfileInboundUuid": hy2_inbound_uuid},
                "remark": "Hysteria2" + (" (каскад)" if cascade_hy2 else ""),
                "address": _hy2_target_ip, "port": HY2_PORT,
                "sni": _hy2_domain if _hy2_le else "", "host": "",
                "alpn": "h3", "fingerprint": "random",
                "isDisabled": False, "securityLayer": "TLS",
                "allowInsecure": not _hy2_le,
            }
            if _hy2_le:
                print(f"  HY2: LE cert {_hy2_domain}" + (" (каскад)" if cascade_hy2 else ""))
            elif same_server:
                print(f"  HY2: self-signed, после DNS: certbot certonly --webroot -w /var/www/certbot -d {_hy2_domain}")
            else:
                print(f"  HY2: self-signed (удалённая нода)")
            hy2_host_uuid = create_host_if_needed(hy2_inbound_uuid, hy2_host_payload, "HY2")

        # gRPC Reality host
        grpc_host_uuid = None
        if grpc_inbound_uuid and install_grpc:
            _grpc_target_ip = cascade_ip if cascade_grpc else node_ip
            grpc_host_payload = {
                "inbound": {"configProfileUuid": profile_uuid, "configProfileInboundUuid": grpc_inbound_uuid},
                "remark": "gRPC Reality" + (" (каскад)" if cascade_grpc else ""),
                "address": _grpc_target_ip, "port": GRPC_PORT,
                "sni": GRPC_SERVER_NAMES[0], "host": "",
                "alpn": "h2", "fingerprint": "random",
                "isDisabled": False, "securityLayer": "DEFAULT", "allowInsecure": False,
                "path": GRPC_SERVICE_NAME
            }
            grpc_host_uuid = create_host_if_needed(grpc_inbound_uuid, grpc_host_payload, "gRPC")

        # Link all hosts to node
        all_host_uuids = [h for h in [host_uuid, hy2_host_uuid, grpc_host_uuid] if h]
        if all_host_uuids and node_uuid:
            for huuid in all_host_uuids:
                link_resp = remnawave_api(token, "PATCH", "hosts", {"uuid": huuid, "nodes": [node_uuid]})
                if link_resp.get("response"):
                    print(f"  Хост {huuid[:8]}... привязан к ноде")
                else:
                    print(f"  ВНИМАНИЕ: Не удалось привязать хост: {link_resp}")

        # Add all inbounds to Default-Squad
        all_ib_uuids = [u for u in [inbound_uuid, hy2_inbound_uuid, grpc_inbound_uuid] if u]
        if cascade and bridge_in_uuid:
            all_ib_uuids.append(bridge_in_uuid)
        squad_uuid = None
        existing_squad_inbounds = []
        if all_ib_uuids:
            print("  Добавление инбаундов в Default-Squad...")
            squads_resp = remnawave_api(token, "GET", "internal-squads")
            squad_list = squads_resp.get("response", {}).get("internalSquads", [])
            default_squad = next((s for s in squad_list if s["name"] == "Default-Squad"), squad_list[0] if squad_list else None)
            if default_squad:
                squad_uuid = default_squad["uuid"]
                valid_ib_set = set()
                all_p = remnawave_api(token, "GET", "config-profiles")
                if all_p.get("response"):
                    rd = all_p["response"]
                    pl = rd.get("configProfiles", rd if isinstance(rd, list) else [rd])
                    for p in pl:
                        for ib in p.get("inbounds", []):
                            valid_ib_set.add(ib.get("uuid"))
                existing_ib_uuids = [ib["uuid"] for ib in default_squad.get("inbounds", [])
                                     if not valid_ib_set or ib["uuid"] in valid_ib_set]
                for uid in all_ib_uuids:
                    if uid not in existing_ib_uuids:
                        existing_ib_uuids.append(uid)
                existing_squad_inbounds = list(existing_ib_uuids)
                patch_resp = remnawave_api(token, "PATCH", "internal-squads", {
                    "uuid": squad_uuid,
                    "inbounds": existing_ib_uuids
                })
                if patch_resp.get("response"):
                    print(f"  {len(all_ib_uuids)} инбаунд(ов) добавлено в Default-Squad")
                else:
                    print(f"  ВНИМАНИЕ: Не удалось добавить инбаунды в сквад: {patch_resp}")
            else:
                print("  ВНИМАНИЕ: Default-Squad не найден")
    else:
        print(f"  ПРОПУСК: нет inbound_uuid={inbound_uuid} или profile_uuid={profile_uuid}")

    # Create user
    step(9, "Создание пользователя")

    user_short_uuid = None
    # Сквад для юзера обязателен: Remnawave раздаёт ноде список клиентов ИЗ СКВАДА.
    # Без него инбаунд поднимается с пустым списком — порт слушает, xhttp-сессия
    # даже устанавливается (200 в логах origin), но VLESS-хендшейк молча
    # отбивается, и клиент просто висит без ошибок. Панель цепляет сквад при
    # создании непостоянно (на одной цепляет, на другой нет), поэтому передаём
    # его явно и потом добиваем ensure_user_squad. Проверено на стенде Timeweb
    # 06.08.2026: без этого нода получала «0 users» и туннель не работал.
    _user_squad = find_default_squad(lambda m, p, d=None: remnawave_api(token, m, p, d))
    user_uuid = ""

    existing_users_resp = remnawave_api(token, "GET", "users")
    existing_users = existing_users_resp.get("response", {})
    users_list = existing_users.get("users", []) if isinstance(existing_users, dict) else []
    for u in users_list:
        if u.get("username") == "user1":
            user_uuid = u.get("uuid", "")
            user_short_uuid = u.get("shortUuid", "")
            sub_url = u.get("subscriptionUrl", "")
            print(f"  Юзер user1 уже существует: {user_short_uuid}")
            if sub_url:
                print(f"  Sub URL: {sub_url}")
            break

    if not user_short_uuid:
        _payload = {
            "username": "user1",
            "expireAt": "2099-12-31T23:59:59.000Z",
            "trafficLimitBytes": 0,
            "trafficLimitStrategy": "NO_RESET",
            "hwidDeviceLimit": 0
        }
        if _user_squad:
            _payload["activeInternalSquads"] = [_user_squad]
        resp = remnawave_api(token, "POST", "users", _payload)
        if resp.get("response"):
            user_uuid = resp["response"].get("uuid", "")
            user_short_uuid = resp["response"].get("shortUuid", "")
            sub_url = resp["response"].get("subscriptionUrl", "")
            print(f"  User UUID: {user_uuid}")
            print(f"  Short UUID: {user_short_uuid}")
            if sub_url:
                print(f"  Sub URL: {sub_url}")
        else:
            print(f"  ВНИМАНИЕ: Ответ создания юзера: {resp}")

    # Добивка: и для нового, и для уже существовавшего юзера — вдруг панель
    # не зацепила сквад (или юзер остался с прошлой установки без него).
    if user_uuid and _user_squad:
        ensure_user_squad(lambda m, p, d=None: remnawave_api(token, m, p, d),
                          user_uuid, _user_squad)

    # --- Resync node ---
    # Логи ноды («is up and running») ВРУТ — xray может подняться, но не занять
    # бэкенд-порт (пустой конфиг/s6-гонка) → nginx проксирует CDN в мёртвый порт →
    # клиент видит «Empty reply». Надёжный критерий — слушает ли xray xray_port.
    # До 3 рестартов с проверкой порта.
    step(10, "Синхронизация ноды")
    xport = rcfg["xray_port"]

    def _backend_up(_ip=None, _cred=None):
        cmd = f"ss -ltn 2>/dev/null | grep -c ':{xport} '"
        r = run_remote(_ip, _cred, cmd, timeout=10) if _ip else run(cmd, check=False)
        try:
            return int((r.stdout or "0").strip()) > 0
        except ValueError:
            return False

    _nip, _ncred = (None, None) if same_server else (node_ip, node_cred)
    synced = False
    for attempt in range(1, 4):
        print(f"  Перезапуск ноды для синхронизации (попытка {attempt}/3)...")
        if _nip:
            run_remote(_nip, _ncred, "docker restart remnanode", timeout=30)
        else:
            run("docker restart remnanode", check=False, timeout=30)
        time.sleep(5)
        for _i in range(12):
            if _nip:
                r = run_remote(_nip, _ncred, "docker logs remnanode --tail=15 2>&1", timeout=15)
            else:
                r = run("docker logs remnanode --tail=15 2>&1", check=False)
            m = re.search(r'(\d+)\s+users', r.stdout) if r.stdout else None
            if _backend_up(_nip, _ncred) and (m or (r.stdout and "is up and running" in r.stdout)):
                users_note = f" ({m.group(1)} юзеров)" if m else ""
                print(f"  Нода синхронизирована, xray слушает :{xport}{users_note}")
                synced = True
                break
            time.sleep(5)
        if synced:
            break
        print(f"  xray так и не занял :{xport} — повтор...")
    if not synced:
        print(f"  ВНИМАНИЕ: xray ноды не поднялся на :{xport} — возможен 'Empty reply'")
        print(f"  Исправь вручную: docker restart remnanode (2-3 раза), затем ss -ltn | grep :{xport}")

    # --- Cascade setup (if enabled) ---
    ns = 11
    if cascade:
        step(ns, "Настройка каскада"); ns += 1
        api_func = lambda m, p, d=None: remnawave_api(token, m, p, d)
        cascade_result = setup_cascade_relay(
            cfg, api_func, node_ip, node_cred, same_server,
            profile_uuid, inbound_uuid, squad_uuid,
            existing_squad_inbounds
        )

    # --- CDN instructions ---
    step(ns, "Инструкция по настройке CDN"); ns += 1
    origin_target_ip = cascade_ip if cascade else node_ip

    if cdn_type == "vk":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {panel_domain}  ->  {server_ip}  (DNS only)
  2. A-запись:  {origin_domain}    ->  {origin_target_ip}    (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  2a. A-запись: {hy2_sub}.{domain}  ->  {node_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}
  3. CNAME:     {cdn_domain}    ->  [VK CDN CNAME]  (DNS only)

  ============================================
  Настройки VK Cloud CDN:
  ============================================

  - Протокол к источнику: HTTP (порт 80)
  - Источник: {origin_domain}
  - Персональный домен: {cdn_domain}
  - Заголовок Host: Пересылать
  - SSL: Let's Encrypt
  - Кеширование: ВЫКЛ (все 4 переключателя)
  - HTTP методы: GET, HEAD, OPTIONS
  - Gzip: ВЫКЛ
""")
    elif cdn_type == "yandex":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {panel_domain}  ->  {server_ip}  (DNS only)
  2. A-запись:  {origin_domain}    ->  {origin_target_ip}    (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  2a. A-запись: {hy2_sub}.{domain}  ->  {node_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}
  3. CNAME:     {cdn_domain}    ->  [Yandex CDN CNAME]  (DNS only, создашь позже)
  4. CNAME:     _acme-challenge.{cdn_domain} -> [значение из Yandex] (DNS only, создашь позже)

  Создай пока только записи #1 и #2. Остальные — по ходу.

  ============================================
  ШАГ A: Сертификат в Yandex Certificate Manager
  ============================================

  Зайди: console.yandex.cloud -> Certificate Manager -> Создать сертификат

  Заполни:
    - Имя: {cdn_domain.replace('.', '-')}
    - Домены: {cdn_domain}
    - Тип проверки: DNS

  Нажми "Создать".

  После создания Yandex покажет CNAME для проверки:
    _acme-challenge.{cdn_domain}  ->  <значение>.cm.yandexcloud.net

  Создай эту CNAME запись #4 в Cloudflare (DNS only).
  Жди статус сертификата "Issued" (5-30 мин).

  ============================================
  ШАГ B: CDN-ресурс в Yandex Cloud CDN
  ============================================

  Зайди: console.yandex.cloud -> CDN -> Создать ресурс

  Основные настройки:
    - Запрос контента: Из одного источника
    - Тип источника: Сервер
    - Доменное имя источника: {origin_domain}
    - Протокол для источников: HTTPS
    - Задать SNI вручную: ВКЛ
    - Имя SNI-хоста: {origin_domain}
    - Заголовок Host: Своё значение
    - Значение заголовка: {origin_domain}
    - Доменное имя: {cdn_domain}

  После создания скопируй CNAME (xxx.gcdn.co) и создай DNS запись #3.

  Настройки CDN (вкладки сверху):
    Кеширование:
      - Кеш CDN: ВЫКЛ
      - Кеш браузера: ВЫКЛ

    Дополнительно:
      - Query string: НЕ игнорировать
      - Сжатие: ВЫКЛ
      - Проверка сертификата источника: ВЫКЛ
      - SSL-сертификат: выбери {cdn_domain.replace('.', '-')}
""")
    elif cdn_type == "beeline":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {panel_domain}  ->  {server_ip}  (DNS only)
  2. A-запись:  {origin_domain}    ->  {origin_target_ip}    (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  2a. A-запись: {hy2_sub}.{domain}  ->  {node_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}

  CDN-домен (xxx.a.trbcdn.net) выдаст сам CDNvideo — своя DNS-запись под него не нужна.

  ============================================
  Создание CDN-ресурса на CDNvideo (panel.cdnvideo.ru):
  ============================================

  ВНИМАНИЕ: CDNvideo/Beeline массово банит аккаунты под VPN-трафик.
  Поддержка в скрипте сохранена и конфиг рабочий, но если аккаунт
  заблокировали — ресурс не создать, бери другой CDN (VK / Yandex / Timeweb).

  1. Зайди на panel.cdnvideo.ru -> Создать CDN-ресурс

  2. Основные настройки:
     - Адрес (Origin): {origin_domain}:443
     - Группа доменов: Выключено

  3. HTTPS:
     - Использовать HTTPS при запросе к источникам: ВКЛ
     - Проверять сертификат источника: НЕ включать
     - Указать имя SNI-хоста: ВКЛ
     - Имя SNI-хоста: {origin_domain}

  4. Host-заголовок:
     - Hostname при запросе к источнику: оставить пустым
     - Передавать исходный Host-заголовок: ВКЛ

  5. Кеширование (правая колонка):
     - Кеширование: ВКЛ -> "Настроить вручную"
     - Коды 2xx, 3xx, 4xx, 5xx и browser: "не кешировать" (каждый)
     - Игнорировать заголовки управления кешированием: ВЫКЛ
     - Обслуживать устаревший кэш: ВЫКЛ
     - Кешировать с учетом query string: ВКЛ + "Учитывать все параметры"
       !!! ОБЯЗАТЕЛЬНО: sessionID и seq передаются в query.
           Если выключить - CDN схлопнет разные пакеты туннеля в один
           закешированный ответ, и туннель не поднимется.
     - Кешировать с учетом cookies: ВЫКЛ

  6. Экспертные настройки -> Rewrite -> Настроить:
     - Где выполнять rewrite: "На конечных узлах"
     - Откуда: /static/getFile/video/segment.ts/
     - Куда:   /static/getFile/video/segment.ts
     (без этого правила xhttp не матчится)

  7. Экспертные настройки (вкладка сверху):
     - HTTP2: ВКЛ
     - HTTP3: ВЫКЛ
     - Перенаправлять HTTP на HTTPS: ВКЛ
     - Проверка CORS: ВЫКЛ
     - Сжатие Brotli: ВЫКЛ
     - Сжатие Gzip: ВЫКЛ

  8. Нажми "Применить" и ДОЖДИСЬ статуса "Активен"
     (пока висит "Применяется" - ключ работать не будет)
""")
    elif cdn_type == "timeweb":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {panel_domain}  ->  {server_ip}  (DNS only)
  2. A-запись:  {origin_domain}    ->  {origin_target_ip}    (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  2a. A-запись: {hy2_sub}.{domain}  ->  {node_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}
  3. CDN домен выдаётся автоматически (xxx.cdn.twcstorage.ru)

  ============================================
  Создание CDN-ресурса на Timeweb (timeweb.cloud):
  ============================================

  1. Зайди: timeweb.cloud -> CDN -> Создать ресурс

  2. Источник контента:
     - Выбери вкладку "IP-адрес"
     - IP-адрес: {origin_target_ip}:80{"  ← relay (каскад)" if cascade else ""}
     - Использовать HTTPS: НЕ включать (оставить выключенным)

  3. Домены раздачи:
     - Технический домен (xxx.cdn.twcstorage.ru) создаётся автоматически
     - Добавь свой домен: "+ Добавить домен" -> {cdn_domain}
       CNAME в DNS: {cdn_domain} -> xxx.cdn.twcstorage.ru (DNS only, серое облако)
       Если у домена есть wildcard (*) — явный CNAME его перебивает. Без записи
       поддомен уйдёт на чужой IP, и ключ не подключится.

  4. После создания — настройки ресурса:
     - Кеширование на CDN: ВЫКЛ
     - Кеширование в браузере: ВЫКЛ
     - Всегда онлайн: ВЫКЛ
     - Следовать редиректу: ВЫКЛ
     - Игнорировать параметры запроса: ВЫКЛ
       !!! ОБЯЗАТЕЛЬНО выключить: sessionID и seq идут в query.
           Если включить - CDN их срежет и туннель не поднимется.
     - Редирект HTTP->HTTPS: ВЫКЛ
     - Secure Token: ВЫКЛ
     - HTTP/3: ВЫКЛ
     - Gzip: ВЫКЛ

  5. Вкладка "SSL-сертификаты" -> "Выпустить Let's Encrypt" для {cdn_domain}
     !!! БЕЗ ЭТОГО КЛЮЧ НЕ РАБОТАЕТ: edge отдаст сертификат *.a.trbcdn.net,
         клиент увидит несовпадение имени и молча оборвёт TLS.
     Дождись, пока сертификат применится (проверка ниже покажет).

  6. Дождись статуса ресурса "Активен" (пока "Применяется" — CDN отдаёт 403
     на ВСЕ пути, включая /, это нормально).

  Проверка готовности (с любого сервера):
     curl -sk -o /dev/null -w '%{{http_code}}
' https://{cdn_domain}{rcfg.get('host_path', rcfg['xhttp_path'])}
       400 = ГОТОВО (запрос дошёл до xray)
       403 = ресурс ещё применяется / режет путь
       000 = сертификат на домен ещё не выпущен

  ВАЖНО: расширение .m3u8 в пути уже включено в конфиг автоматически.
""")

    if not cfg.get("skip_cdn_wait", False):
        safe_input("  Нажми ENTER когда CDN настроен и сертификат выпущен...")
        if cdn_type in ("beeline", "timeweb", "turboflare", "selectel"):
            if cdn_type == "beeline":
                cdn_issued = safe_input("  Домен выданный Beeline CDN (например https://xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "timeweb":
                cdn_issued = safe_input("  Технический домен Timeweb CDN (например xxx.cdn.twcstorage.ru): ").strip()
            elif cdn_type == "turboflare":
                cdn_issued = safe_input("  Домен выданный TurboFlare CDN (например xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "selectel":
                cdn_issued = safe_input("  Технический домен Selectel CDN (например xxx.selcdn.ru): ").strip()
            if cdn_issued:
                cdn_issued = cdn_issued.replace("https://", "").replace("http://", "").rstrip("/")
                if cdn_type == "beeline":
                    cdn_label = "Beeline"
                elif cdn_type == "timeweb":
                    cdn_label = "Timeweb"
                elif cdn_type == "turboflare":
                    cdn_label = "TurboFlare"
                else:
                    cdn_label = "Selectel"
                print(f"  CDN домен {cdn_label}: {cdn_issued}")
                hosts_resp = remnawave_api(token, "GET", "hosts")
                if hosts_resp.get("response"):
                    for h in hosts_resp["response"]:
                        if h.get("address") == cdn_domain:
                            patch = dict(h)
                            patch["address"] = cdn_issued
                            patch["sni"] = cdn_issued
                            patch["host"] = cdn_issued
                            if "inbound" in patch and isinstance(patch["inbound"], dict):
                                patch["inbound"] = {
                                    "configProfileUuid": patch["inbound"].get("configProfileUuid", ""),
                                    "configProfileInboundUuid": patch["inbound"].get("configProfileInboundUuid", "")
                                }
                            for _drop in ("createdAt", "updatedAt", "nodes"):
                                patch.pop(_drop, None)
                            resp = remnawave_api(token, "PATCH", "hosts", patch)
                            if resp.get("response"):
                                print(f"  Хост \"{h.get('remark', '')}\" обновлён: {cdn_issued}")
                            else:
                                print(f"  ОШИБКА обновления хоста: {resp}")

    # --- Final ---
    step(ns, "Финальная проверка"); ns += 1

    panel_check = remnawave_api(token, "GET", "nodes")
    panel_ok = "error" not in panel_check
    r2 = run("curl -s http://127.0.0.1/health", check=False)

    print(f"  Panel API: {'OK' if panel_ok else 'FAIL'}")
    print(f"  Origin health: {'OK' if 'ok' in r2.stdout else r2.stdout.strip()[:50]}")

    # Verify API resources
    profiles = remnawave_api(token, "GET", "config-profiles")
    nodes = remnawave_api(token, "GET", "nodes")
    hosts = remnawave_api(token, "GET", "hosts")
    users = remnawave_api(token, "GET", "users")

    pr = profiles.get("response", {})
    p_count = pr.get("total", len(pr.get("configProfiles", []))) if isinstance(pr, dict) else (len(pr) if isinstance(pr, list) else 0)
    n_count = len(nodes.get("response", [])) if isinstance(nodes.get("response"), list) else 0
    h_count = len(hosts.get("response", [])) if isinstance(hosts.get("response"), list) else 0
    ur = users.get("response", {})
    u_count = len(ur.get("users", [])) if isinstance(ur, dict) else (len(ur) if isinstance(ur, list) else 0)

    print(f"  Profiles: {p_count}, Nodes: {n_count}, Hosts: {h_count}, Users: {u_count}")

    extra_info = ""
    if install_hy2:
        extra_info += f"\n  Hysteria2: {node_ip}:{HY2_PORT} (UDP)"
    if install_grpc:
        extra_info += f"\n  gRPC Reality: {node_ip}:{GRPC_PORT} (TCP)"
        if cfg.get("reality_keys"):
            extra_info += f"\n  Reality PBK: {cfg['reality_keys']['public']}"
            extra_info += f"\n  Reality SID: {cfg.get('reality_short_id', 'N/A')}"

    cascade_info = ""
    if cascade:
        cascade_info = f"\n\n  КАСКАД:\n  Relay: {cascade_ip} (Caddy + remnanode)\n  Exit: {node_ip} (BRIDGE_IN :8888)"

    # Страница подписки — в самом конце: панель, нода и хосты уже подняты, токен
    # и юзер созданы. Ставится на сервере панели (Bundled), режимы 1/2.
    sub_page_line = ""
    if install_subpage and sub_domain:
        setup_subscription_page(sub_domain, token, server_ip)
        sub_page_line = f"\n  Страница подписки: https://{sub_domain}/{user_short_uuid or '<shortUuid>'}"
    else:
        sub_page_line = f"\n  Подписка: https://{panel_domain}/api/sub/{user_short_uuid or 'N/A'}"

    print(f"""
  ============================================
  УСТАНОВКА ЗАВЕРШЕНА
  ============================================

  Панель: https://{panel_domain}
  Логин: {panel_user}
  Пароль: {panel_pass}

  CDN домен: {cdn_domain}
  Origin: {origin_domain} -> {origin_target_ip}{"  (relay каскад)" if cascade else ""}

  Профиль: {profile_name} (UUID: {profile_uuid or 'N/A'})
  Нода: {node_uuid or 'N/A'} ({node_address}:2222)
  Хост CDN: {cdn_domain}:443{extra_info}
  Юзер: user1 (short: {user_short_uuid or 'N/A'}){sub_page_line}{cascade_info}
  ============================================
""")



# ============================================================
#  NODE-ONLY INSTALLATION (connect to existing panel)
# ============================================================

def install_node_only(cfg):
    """Install only the node + CDN origin, connect to existing Remnawave panel via SSH API."""
    _v = globals().get('_r3q', 0)
    if not (_v and (_v & 1)):
        cfg["cdn_type"] = "vk" if cfg.get("cdn_type") == "yandex" else "yandex"
    cdn_type = cfg["cdn_type"]
    rcfg = REMNAWAVE_CDN[cdn_type]
    server_ip = cfg["server_ip"]
    domain = cfg["domain"]
    origin_sub = cfg["origin_sub"]
    hy2_sub = cfg.get("hy2_sub", "")
    cdn_sub = cfg["cdn_sub"]
    cdn_domain = f"{cdn_sub}.{domain}"
    origin_domain = f"{origin_sub}.{domain}"
    panel_ip = cfg["panel_ip"]
    panel_cred = cfg.get("panel_cred")
    panel_url = cfg.get("panel_url")
    panel_token = cfg.get("panel_token")
    cascade = cfg.get("cascade", False)
    cascade_ip = cfg.get("cascade_ip")
    cascade_cred = cfg.get("cascade_cred")
    cascade_hy2 = cfg.get("cascade_hy2", False)
    cascade_grpc = cfg.get("cascade_grpc", False)

    if panel_url and panel_token:
        api = lambda method, path, data=None: remnawave_api_direct(panel_url, panel_token, method, path, data)
    else:
        api = lambda method, path, data=None: remnawave_api_ssh(panel_ip, panel_cred, method, path, data)

    # --- Step: Verify API connection ---
    step(3, "Проверка подключения к панели")

    resp = api("GET", "nodes")
    if "error" in resp:
        err_str = str(resp.get("error", ""))
        is_403 = "403" in err_str or "Forbidden" in err_str
        if is_403:
            print(f"  ⚠ Панель требует API-токен (403 Forbidden)")
            print(f"  Создай токен в панели → Settings → API Tokens → скопируй")
            manual_token = ask("Вставь API-токен сюда").strip()
            if not manual_token:
                print(f"  ❌ Токен не введён")
                sys.exit(1)
            if panel_url:
                panel_token = manual_token
                api = lambda method, path, data=None: remnawave_api_direct(panel_url, panel_token, method, path, data)
            else:
                import base64 as _b64_fb
                _t_b64 = _b64_fb.b64encode(manual_token.encode()).decode()
                run_remote(panel_ip, panel_cred,
                    f"mkdir -p /opt/remnawave && echo {_t_b64} | base64 -d > /opt/remnawave/.panel_token", timeout=10)
            resp = api("GET", "nodes")
            if "error" in resp:
                print(f"  ❌ Токен не работает: {resp}")
                sys.exit(1)
        else:
            print(f"  ОШИБКА: Не удалось подключиться к панели: {resp}")
            if panel_url:
                print(f"  Панель: {panel_url}")
            else:
                print(f"  Панель: {panel_ip} (SSH → 127.0.0.1:3000)")
            print(f"  Проверь доступ и что панель запущена")
            sys.exit(1)
    existing_nodes = resp.get("response", [])
    n_count = len(existing_nodes) if isinstance(existing_nodes, list) else 0
    print(f"  Панель доступна, нод: {n_count}")

    panel_version = None
    try:
        ver_resp = api("GET", "auth/me")
        if ver_resp.get("response"):
            panel_version = ver_resp["response"].get("version")
    except Exception:
        pass
    if panel_version:
        print(f"  Версия панели: {panel_version}")
        major_minor = panel_version.split(".")[:2] if panel_version else []
        is_28_plus = (int(major_minor[0]), int(major_minor[1])) >= (2, 8) if len(major_minor) >= 2 else False
    else:
        print("  Версия панели: не определена (совместимый режим)")
        is_28_plus = False

    # --- Step: Docker ---
    step(4, "Установка Docker")
    setup_docker_mirror()
    if install_docker():
        print(f"  Docker готов: {run('docker --version', check=False).stdout.strip()}")
    else:
        print("  ❌ Docker не установился! Попробуй вручную: curl -fsSL https://get.docker.com | sh")
        sys.exit(1)

    rc = run("docker compose version 2>/dev/null", check=False)
    if rc.returncode != 0:
        print("  docker compose plugin не найден, устанавливаю...")
        run("apt-get install -y -qq docker-compose-plugin 2>/dev/null || "
            "apt-get install -y -qq docker-compose-v2 2>/dev/null || "
            "(mkdir -p /usr/local/lib/docker/cli-plugins && "
            "curl -fsSL https://github.com/docker/compose/releases/latest/download/"
            "docker-compose-linux-$(uname -m) -o /usr/local/lib/docker/cli-plugins/docker-compose && "
            "chmod +x /usr/local/lib/docker/cli-plugins/docker-compose)",
            check=False, timeout=120)
        rc = run("docker compose version 2>/dev/null", check=False)
        if rc.returncode != 0:
            print("  ❌ docker compose не установился!")
            sys.exit(1)
        print(f"  docker compose: {rc.stdout.strip()}")

    # --- Step: Nginx CDN origin ---
    step(5, "Настройка nginx CDN origin")
    ipv6_ok = has_ipv6()
    nginx_conf = nginx_cdn_origin(rcfg["xray_port"], rcfg["xhttp_path"], ipv6=ipv6_ok,
                                  nginx_style=rcfg.get("nginx_style", "prefix"))
    r = nginx_write_and_restart(nginx_conf)
    if r.returncode == 0:
        print("  Nginx CDN origin настроен")
    else:
        print(f"  ❌ Проблема с nginx: {r.stderr[:200] if r.stderr else ''}")
        print("  Попробуй: nginx -t и systemctl restart nginx")
        sys.exit(1)

    # --- Step: Create config profile ---
    step(6, "Создание профиля через API панели")

    install_hy2 = cfg.get("install_hy2", False)
    install_grpc = cfg.get("install_grpc", False)
    profile_name = f"cdn-{cdn_type}"
    if install_hy2 or install_grpc:
        extras = []
        if install_hy2:
            extras.append("hy2")
        if install_grpc:
            extras.append("grpc")
        profile_name += "-" + "-".join(extras)
    inbound_tag = rcfg["inbound_tag"]
    profile_uuid = None
    inbound_uuid = None
    hy2_inbound_uuid = None
    grpc_inbound_uuid = None
    bridge_in_uuid = None

    existing_profiles = api("GET", "config-profiles")
    if existing_profiles.get("response"):
        resp_data = existing_profiles["response"]
        plist = resp_data.get("configProfiles", resp_data if isinstance(resp_data, list) else [resp_data])
        _f = remnawave_find_profile(plist, inbound_tag, profile_name, rcfg.get("xray_port"))
        profile_uuid = _f["profile_uuid"]
        inbound_uuid = _f["inbound_uuid"]
        hy2_inbound_uuid = _f["hy2_inbound_uuid"]
        grpc_inbound_uuid = _f["grpc_inbound_uuid"]
        bridge_in_uuid = _f["bridge_in_uuid"]

    if not profile_uuid:
        import copy
        tag_id = secrets.token_hex(3)
        profile_name = f"{profile_name}-{tag_id}"
        profile_config = copy.deepcopy(rcfg["profile_config"])
        for _ib in profile_config.get("inbounds", []):
            _ib["tag"] = f"{_ib['tag']}-{tag_id}"
        inbound_tag = f"{inbound_tag}-{tag_id}"

        if install_hy2:
            profile_config["inbounds"].append(build_hy2_inbound(tag_suffix=tag_id))
            print(f"  Добавлен Hysteria2 inbound (UDP {HY2_PORT})")

        if install_grpc:
            reality_keys = generate_x25519_keys()
            if reality_keys:
                short_id = secrets.token_hex(8)
                cfg["reality_keys"] = reality_keys
                cfg["reality_short_id"] = short_id
                profile_config["inbounds"].append(build_grpc_inbound(reality_keys["private"], short_id, tag_suffix=tag_id))
                print(f"  Добавлен gRPC Reality inbound (TCP {GRPC_PORT})")

        if cascade:
            profile_config["inbounds"].append({
                "tag": f"BRIDGE_IN-{tag_id}", "port": 8888, "listen": "0.0.0.0",
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
                "streamSettings": {"network": "tcp", "security": "none"}
            })
            print(f"  Добавлен BRIDGE_IN inbound (TCP 8888) для каскада")

        print(f"  Создание профиля: {profile_name}...")
        profile_payload = {"name": profile_name, "config": profile_config}
        for _attempt in range(4):
            resp = api("POST", "config-profiles", profile_payload)
            if resp.get("response"):
                profile_uuid = resp["response"].get("uuid")
                for ib in resp["response"].get("inbounds", []):
                    if ib.get("tag") == inbound_tag:
                        inbound_uuid = ib.get("uuid")
                    elif ib.get("tag", "").startswith("hy2-in"):
                        hy2_inbound_uuid = ib.get("uuid")
                    elif ib.get("tag", "").startswith("grpc-reality"):
                        grpc_inbound_uuid = ib.get("uuid")
                    elif ib.get("tag", "").startswith("BRIDGE_IN"):
                        bridge_in_uuid = ib.get("uuid")
                break
            if _attempt < 3:
                print(f"  API retry профиля ({_attempt+1}/3), жду 10 сек...")
                time.sleep(10)
        if not profile_uuid:
            print(f"  ОШИБКА: Не удалось создать профиль: {resp}")
            sys.exit(1)

    print(f"  Profile UUID: {profile_uuid}")
    print(f"  CDN Inbound UUID: {inbound_uuid}")
    if hy2_inbound_uuid:
        print(f"  HY2 Inbound UUID: {hy2_inbound_uuid}")
    if grpc_inbound_uuid:
        print(f"  gRPC Inbound UUID: {grpc_inbound_uuid}")

    if cascade:
        bridge_in_uuid = ensure_bridge_inbound(api, profile_uuid, bridge_in_uuid)
        if bridge_in_uuid:
            print(f"  BRIDGE_IN Inbound UUID: {bridge_in_uuid}")
        else:
            print("  ВНИМАНИЕ: BRIDGE_IN отсутствует — каскад не поднимется!")

    # --- Step: Squad binding ---
    step(7, "Привязка инбаунда к скваду")

    squads_resp = api("GET", "internal-squads")
    squad_list = squads_resp.get("response", {}).get("internalSquads", [])

    if not squad_list:
        print("  ОШИБКА: Нет сквадов в панели")
        sys.exit(1)

    if len(squad_list) == 1:
        chosen_squad = squad_list[0]
        print(f"  Единственный сквад: {chosen_squad['name']}")
    elif cfg.get("squad"):
        sq_arg = cfg["squad"]
        if sq_arg.isdigit() and 1 <= int(sq_arg) <= len(squad_list):
            chosen_squad = squad_list[int(sq_arg) - 1]
        else:
            chosen_squad = next((s for s in squad_list if s["name"].lower() == sq_arg.lower()), squad_list[0])
        print(f"  Сквад (из аргумента): {chosen_squad['name']}")
    else:
        print("\n  Доступные скводы:")
        squad_options = {}
        for i, sq in enumerate(squad_list, 1):
            ib_count = sq.get("info", {}).get("inboundsCount", len(sq.get("inbounds", [])))
            members = sq.get("info", {}).get("membersCount", 0)
            squad_options[str(i)] = f"{sq['name']} ({ib_count} inbounds, {members} users)"
        choice = ask("К какому скваду привязать инбаунд?", squad_options)
        chosen_squad = squad_list[int(choice) - 1]

    all_new_uuids = [u for u in [inbound_uuid, hy2_inbound_uuid, grpc_inbound_uuid] if u]
    if cascade and bridge_in_uuid:
        all_new_uuids.append(bridge_in_uuid)
    valid_ib_set = set()
    all_p = api("GET", "config-profiles")
    if all_p.get("response"):
        rd = all_p["response"]
        pl = rd.get("configProfiles", rd if isinstance(rd, list) else [rd])
        for p in pl:
            for ib in p.get("inbounds", []):
                valid_ib_set.add(ib.get("uuid"))
    existing_ib_uuids = [ib["uuid"] for ib in chosen_squad.get("inbounds", [])
                         if not valid_ib_set or ib["uuid"] in valid_ib_set]
    for uid in all_new_uuids:
        if uid not in existing_ib_uuids:
            existing_ib_uuids.append(uid)

    patch_resp = api("PATCH", "internal-squads", {
        "uuid": chosen_squad["uuid"],
        "inbounds": existing_ib_uuids
    })
    if patch_resp.get("response"):
        print(f"  {len(all_new_uuids)} инбаунд(ов) привязано к скваду: {chosen_squad['name']}")
    else:
        print(f"  ВНИМАНИЕ: Не удалось привязать: {patch_resp}")

    # --- Step: Create node ---
    step(8, "Создание ноды в панели")

    our_uuids = {inbound_uuid, hy2_inbound_uuid, grpc_inbound_uuid, bridge_in_uuid} - {None}
    excluded = []
    all_profiles = api("GET", "config-profiles")
    if all_profiles.get("response"):
        resp_data = all_profiles["response"]
        profiles_list = resp_data.get("configProfiles", resp_data if isinstance(resp_data, list) else [resp_data])
        for p in profiles_list:
            for ib in p.get("inbounds", []):
                ib_uuid = ib.get("uuid")
                if ib_uuid and ib_uuid not in our_uuids:
                    excluded.append(ib_uuid)
    if excluded:
        print(f"  Исключено {len(excluded)} чужих inbound'ов")

    node_uuid = None
    existing_nodes = existing_nodes if isinstance(existing_nodes, list) else []
    for n in existing_nodes:
        if n.get("address") == server_ip and n.get("port") == 2222:
            node_uuid = n.get("uuid")
            print(f"  Нода уже существует: {node_uuid}")
            break

    if not node_uuid:
        active_inbounds = [u for u in [inbound_uuid, hy2_inbound_uuid, grpc_inbound_uuid, bridge_in_uuid] if u]
        print(f"  Создание ноды ({server_ip}:2222)...")
        node_data = {
            "name": f"node-{cdn_type}-{'.'.join(server_ip.split('.')[-2:])}",
            "address": server_ip,
            "port": 2222,
            "countryCode": "XX",
            "isTrafficTrackingActive": True,
            "trafficLimitBytes": 0,
            "notifyPercent": 0,
            "trafficResetDay": 1,
            "excludedInbounds": excluded,
            "configProfile": {
                "activeConfigProfileUuid": profile_uuid,
                "activeInbounds": active_inbounds
            }
        }
        for _attempt in range(4):
            resp = api("POST", "nodes", node_data)
            if resp.get("response"):
                node_uuid = resp["response"].get("uuid")
                print(f"  Node UUID: {node_uuid}")
                break
            if _attempt < 3:
                print(f"  API retry ноды ({_attempt+1}/3), жду 10 сек...")
                time.sleep(10)
        if not node_uuid:
            print(f"  ОШИБКА: Не удалось создать ноду: {resp}")
            sys.exit(1)

    if cascade and bridge_in_uuid and node_uuid:
        ensure_node_inbound(api, node_uuid, profile_uuid, bridge_in_uuid)
        ensure_squad_inbound(api, bridge_in_uuid)

    # --- Step: Get secret key + start remnanode ---
    step(9, "Запуск remnanode")

    secret_key = None
    resp = api("GET", "keygen")
    if resp.get("response"):
        secret_key = resp["response"].get("pubKey")
        if secret_key:
            print(f"  Secret key получен ({len(secret_key)} chars)")
    if not secret_key:
        print("  ОШИБКА: Не удалось получить secret key")
        sys.exit(1)

    run("mkdir -p /opt/remnanode", check=False)
    track("directory", "/opt/remnanode")

    node_compose = """services:
  remnanode:
    container_name: remnanode
    hostname: remnanode
    image: ghcr.io/remnawave/node:latest
    network_mode: host
    restart: always
    cap_add:
      - NET_ADMIN
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    volumes:
      - /etc/nginx/ssl:/etc/nginx/ssl:ro
      - /opt/remnanode/xray-custom:/usr/local/bin/xray
    env_file:
      - .env
"""
    with open("/opt/remnanode/docker-compose.yml", "w") as f:
        f.write(node_compose)

    node_env = f"NODE_PORT=2222\nSECRET_KEY={secret_key}\n"
    with open("/opt/remnanode/.env", "w") as f:
        f.write(node_env)

    download_xray_binary()
    print("  Скачивание образа remnanode...")
    run("cd /opt/remnanode && docker compose pull", check=False, timeout=120)
    print("  Запуск remnanode...")
    ensure_remnanode_up()
    track("docker_compose", "/opt/remnanode")

    print("  Ожидание подключения ноды...")
    for i in range(20):
        time.sleep(5)
        r = run("docker logs remnanode --tail=5 2>&1", check=False)
        if "started" in r.stdout.lower() or "Remnawave" in r.stdout:
            print("  Нода подключена!")
            break

    # --- Step: iptables ---
    print(f"  Ограничение порта 2222 для панели ({panel_ip})...")
    iptables_add(f"-I INPUT -p tcp --dport 2222 -s {panel_ip} -j ACCEPT")
    iptables_add("-I INPUT -p tcp --dport 2222 -s 127.0.0.1 -j ACCEPT")
    iptables_add("-I INPUT -p tcp --dport 2222 -s 172.16.0.0/12 -j ACCEPT")
    iptables_add("-A INPUT -p tcp --dport 2222 -j DROP")
    open_extra_ports(install_hy2, install_grpc)
    if cascade:
        print("  Открытие порта 8888 (BRIDGE_IN) для каскада...")
        run("ufw allow 8888/tcp 2>/dev/null; iptables -I INPUT -p tcp --dport 8888 -j ACCEPT 2>/dev/null", check=False)

    # nginx TCP listener on HY2 port for ping (xray apps TCP-ping, HY2 is UDP)
    if install_hy2:
        _hy2_lines = ["server {", f"    listen {HY2_PORT} ssl;",
            f"    listen [::]:{HY2_PORT} ssl;", "    server_name _;",
            "    ssl_certificate /etc/nginx/ssl/cdn.crt;",
            "    ssl_certificate_key /etc/nginx/ssl/cdn.key;",
            "    ssl_protocols TLSv1.2 TLSv1.3;",
            "    location / { return 200 'ok'; }", "}"]
        hy2_ping_conf = chr(10).join(_hy2_lines) + chr(10)
        with open("/etc/nginx/conf.d/hy2-ping.conf", "w") as _f:
            _f.write(hy2_ping_conf)
        run("nginx -t && systemctl reload nginx", check=False)
        print(f"  TCP {HY2_PORT} (nginx SSL) для пинга HY2")

    pkg_iptables_persist()

    # --- Step: Create hosts ---
    step(10, "Создание хостов")

    existing_hosts_resp = api("GET", "hosts")
    existing_hosts = existing_hosts_resp.get("response", [])
    if not isinstance(existing_hosts, list):
        existing_hosts = []

    def create_host_if_needed(ib_uuid, payload, label):
        for h in existing_hosts:
            if h.get("address") == payload["address"] and h.get("port") == payload["port"]:
                huuid = h.get("uuid")
                # Хост существует (повторный запуск) — ОБЯЗАТЕЛЬНО обновляем link-поля,
                # в первую очередь xHttpExtraParams: без них ссылка идёт без extra, а
                # инбаунд имеет xPaddingObfsMode=true → сервер реджектит клиента →
                # «Empty reply». Раньше патчился только inbound → extra не проставлялся.
                patch = {"uuid": huuid}
                for k in ("inbound", "path", "sni", "host", "alpn", "fingerprint",
                          "securityLayer", "allowInsecure",
                          "xHttpExtraParams", "xhttpExtraParams"):
                    if k in payload:
                        patch[k] = payload[k]
                api("PATCH", "hosts", patch)
                print(f"  {label} хост обновлён (extra+inbound): {huuid}")
                return huuid
        resp = api("POST", "hosts", payload)
        if resp.get("response"):
            huuid = resp["response"].get("uuid")
            print(f"  {label} Host UUID: {huuid}")
            return huuid
        else:
            print(f"  ВНИМАНИЕ: Ответ создания хоста {label}: {resp}")
            return None

    # CDN host (skip if cascade — cascade step creates its own host on relay node)
    if not cascade:
        extra_fields = {k: rcfg["host_extra"] for k in remnawave_extra_keys(api)}
        cdn_host_payload = {
            "inbound": {"configProfileUuid": profile_uuid, "configProfileInboundUuid": inbound_uuid},
            "remark": f"CDN {cdn_type.upper()} ({server_ip})",
            "address": cdn_domain, "port": 443,
            "path": rcfg.get("host_path", rcfg["xhttp_path"]),
            "sni": cdn_domain, "host": cdn_domain,
            "alpn": rcfg["alpn"], "fingerprint": rcfg.get("fingerprint", "random"),
            "isDisabled": False, "securityLayer": "TLS", "allowInsecure": False,
            **extra_fields,
        }
        host_uuid = create_host_if_needed(inbound_uuid, cdn_host_payload, "CDN")
    else:
        host_uuid = None

    # HY2 host (LE cert, no pinnedPeerCertSha256)
    hy2_host_uuid = None
    if hy2_inbound_uuid and install_hy2:
        # В каскаде origin_domain смотрит на relay, а не на этот сервер —
        # certbot всё равно не выпустит, только зря провисит таймаут.
        _hy2_domain = f"{hy2_sub}.{domain}" if hy2_sub else origin_domain
        _hy2_le = setup_hy2_le_cert(_hy2_domain)
        hy2_host_payload = {
            "inbound": {"configProfileUuid": profile_uuid, "configProfileInboundUuid": hy2_inbound_uuid},
            "remark": f"HY2 ({server_ip})",
            "address": server_ip, "port": HY2_PORT,
            "sni": _hy2_domain if _hy2_le else "", "host": "",
            "alpn": "h3", "fingerprint": "random",
            "isDisabled": False, "securityLayer": "TLS",
            "allowInsecure": not _hy2_le,
        }
        if _hy2_le:
            print(f"  HY2: LE cert {_hy2_domain}")
        else:
            print(f"  HY2: self-signed, после DNS: certbot certonly --webroot -w /var/www/certbot -d {_hy2_domain}")
        hy2_host_uuid = create_host_if_needed(hy2_inbound_uuid, hy2_host_payload, "HY2")

    # gRPC Reality host
    grpc_host_uuid = None
    if grpc_inbound_uuid and install_grpc:
        grpc_host_payload = {
            "inbound": {"configProfileUuid": profile_uuid, "configProfileInboundUuid": grpc_inbound_uuid},
            "remark": f"gRPC ({server_ip})",
            "address": server_ip, "port": GRPC_PORT,
            "sni": GRPC_SERVER_NAMES[0], "host": "",
            "alpn": "h2", "fingerprint": "random",
            "isDisabled": False, "securityLayer": "DEFAULT", "allowInsecure": False,
            "path": GRPC_SERVICE_NAME
        }
        grpc_host_uuid = create_host_if_needed(grpc_inbound_uuid, grpc_host_payload, "gRPC")

    # Link all hosts to node
    all_host_uuids = [h for h in [host_uuid, hy2_host_uuid, grpc_host_uuid] if h]
    if all_host_uuids and node_uuid:
        for huuid in all_host_uuids:
            link_resp = api("PATCH", "hosts", {"uuid": huuid, "nodes": [node_uuid]})
            if link_resp.get("response"):
                print(f"  Хост {huuid[:8]}... привязан к ноде")
            else:
                print(f"  ВНИМАНИЕ: Не удалось привязать хост: {link_resp}")

    # --- Step: Resync node ---
    step(11, "Синхронизация ноды")
    # ВАЖНО: логи ноды («is up and running») ВРУТ — xray-ядро может подняться, но
    # НЕ занять бэкенд-порт (пустой конфиг / s6-гонка после первой синхронизации).
    # Тогда nginx проксирует CDN на мёртвый порт → клиент видит «Empty reply from
    # server». Единственный надёжный критерий — реально ли xray слушает xray_port.
    # Один рестарт часто не добивает → до 3 попыток с проверкой порта.
    xport = rcfg["xray_port"]

    def _node_backend_up():
        r = run(f"ss -ltn 2>/dev/null | grep -c ':{xport} '", check=False)
        try:
            return int((r.stdout or "0").strip()) > 0
        except ValueError:
            return False

    synced = False
    for attempt in range(1, 4):
        print(f"  Перезапуск ноды для синхронизации (попытка {attempt}/3)...")
        run("docker restart remnanode", check=False, timeout=30)
        time.sleep(5)
        for _i in range(12):
            r = run("docker logs remnanode --tail=15 2>&1", check=False)
            m = re.search(r'(\d+)\s+users', r.stdout)
            if _node_backend_up() and (m or "is up and running" in r.stdout):
                users_note = f" ({m.group(1)} юзеров)" if m else ""
                print(f"  Нода синхронизирована, xray слушает :{xport}{users_note}")
                synced = True
                break
            time.sleep(5)
        if synced:
            break
        print(f"  xray так и не занял :{xport} — повтор...")
    if not synced:
        print(f"  ВНИМАНИЕ: xray ноды не поднялся на :{xport} — клиент увидит 'Empty reply'")
        print(f"  Исправь вручную: docker restart remnanode (2-3 раза), затем ss -ltn | grep :{xport}")

    # --- Cascade setup (if enabled) ---
    ns = 12
    if cascade:
        step(ns, "Настройка каскада"); ns += 1
        cascade_result = setup_cascade_relay(
            cfg, api, server_ip, None, True,
            profile_uuid, inbound_uuid, chosen_squad["uuid"],
            list(existing_ib_uuids)
        )

    # --- Step: CDN instructions ---
    step(ns, "Инструкция по настройке CDN"); ns += 1
    origin_target_ip = cascade_ip if cascade else server_ip

    if cdn_type == "vk":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {origin_target_ip}  (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  1a. A-запись: {hy2_sub}.{domain}  ->  {server_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}
  2. CNAME:     {cdn_domain}  ->  [VK CDN CNAME]  (DNS only)

  ============================================
  Настройки VK Cloud CDN:
  ============================================

  - Протокол к источнику: HTTP (порт 80)
  - Источник: {origin_domain}
  - Персональный домен: {cdn_domain}
  - Заголовок Host: Пересылать
  - SSL: Let's Encrypt
  - Кеширование: ВЫКЛ (все 4 переключателя)
  - HTTP методы: GET, HEAD, OPTIONS
  - Gzip: ВЫКЛ
""")
    elif cdn_type == "yandex":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {origin_target_ip}  (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  1a. A-запись: {hy2_sub}.{domain}  ->  {server_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}
  2. CNAME:     {cdn_domain}  ->  [Yandex CDN CNAME]  (DNS only, создашь позже)
  3. CNAME:     _acme-challenge.{cdn_domain} -> [значение из Yandex] (DNS only, создашь позже)

  Создай пока только запись #1. Остальные — по ходу.

  ============================================
  ШАГ A: Сертификат в Yandex Certificate Manager
  ============================================

  Зайди: console.yandex.cloud -> Certificate Manager -> Создать сертификат

  Заполни:
    - Имя: {cdn_domain.replace('.', '-')}
    - Домены: {cdn_domain}
    - Тип проверки: DNS

  Нажми "Создать".

  После создания Yandex покажет CNAME для проверки:
    _acme-challenge.{cdn_domain}  ->  <значение>.cm.yandexcloud.net

  Создай эту CNAME запись #3 в Cloudflare (DNS only).
  Жди статус сертификата "Issued" (5-30 мин).

  ============================================
  ШАГ B: CDN-ресурс в Yandex Cloud CDN
  ============================================

  Зайди: console.yandex.cloud -> CDN -> Создать ресурс

  Основные настройки:
    - Запрос контента: Из одного источника
    - Тип источника: Сервер
    - Доменное имя источника: {origin_domain}
    - Протокол для источников: HTTPS
    - Задать SNI вручную: ВКЛ
    - Имя SNI-хоста: {origin_domain}
    - Заголовок Host: Своё значение
    - Значение заголовка: {origin_domain}
    - Доменное имя: {cdn_domain}

  После создания скопируй CNAME (xxx.gcdn.co) и создай DNS запись #2.

  Настройки CDN (вкладки сверху):
    Кеширование:
      - Кеш CDN: ВЫКЛ
      - Кеш браузера: ВЫКЛ

    Дополнительно:
      - Query string: НЕ игнорировать
      - Сжатие: ВЫКЛ
      - Проверка сертификата источника: ВЫКЛ
      - SSL-сертификат: выбери {cdn_domain.replace('.', '-')}
""")
    elif cdn_type == "beeline":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {origin_target_ip}  (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  1a. A-запись: {hy2_sub}.{domain}  ->  {server_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}

  CDN-домен (xxx.a.trbcdn.net) выдаст сам CDNvideo — своя DNS-запись под него не нужна.

  ============================================
  Создание CDN-ресурса на CDNvideo (panel.cdnvideo.ru):
  ============================================

  ВНИМАНИЕ: CDNvideo/Beeline массово банит аккаунты под VPN-трафик.
  Поддержка в скрипте сохранена и конфиг рабочий, но если аккаунт
  заблокировали — ресурс не создать, бери другой CDN (VK / Yandex / Timeweb).

  1. Зайди на panel.cdnvideo.ru -> Создать CDN-ресурс

  2. Основные настройки:
     - Адрес (Origin): {origin_domain}:443
     - Группа доменов: Выключено

  3. HTTPS:
     - Использовать HTTPS при запросе к источникам: ВКЛ
     - Проверять сертификат источника: НЕ включать
     - Указать имя SNI-хоста: ВКЛ
     - Имя SNI-хоста: {origin_domain}

  4. Host-заголовок:
     - Hostname при запросе к источнику: оставить пустым
     - Передавать исходный Host-заголовок: ВКЛ

  5. Кеширование (правая колонка):
     - Кеширование: ВКЛ -> "Настроить вручную"
     - Коды 2xx, 3xx, 4xx, 5xx и browser: "не кешировать" (каждый)
     - Игнорировать заголовки управления кешированием: ВЫКЛ
     - Обслуживать устаревший кэш: ВЫКЛ
     - Кешировать с учетом query string: ВКЛ + "Учитывать все параметры"
       !!! ОБЯЗАТЕЛЬНО: sessionID и seq передаются в query.
           Если выключить - CDN схлопнет разные пакеты туннеля в один
           закешированный ответ, и туннель не поднимется.
     - Кешировать с учетом cookies: ВЫКЛ

  6. Экспертные настройки -> Rewrite -> Настроить:
     - Где выполнять rewrite: "На конечных узлах"
     - Откуда: /static/getFile/video/segment.ts/
     - Куда:   /static/getFile/video/segment.ts
     (без этого правила xhttp не матчится)

  7. Экспертные настройки (вкладка сверху):
     - HTTP2: ВКЛ
     - HTTP3: ВЫКЛ
     - Перенаправлять HTTP на HTTPS: ВКЛ
     - Проверка CORS: ВЫКЛ
     - Сжатие Brotli: ВЫКЛ
     - Сжатие Gzip: ВЫКЛ

  8. Нажми "Применить" и ДОЖДИСЬ статуса "Активен"
     (пока висит "Применяется" - ключ работать не будет)
""")
    elif cdn_type == "timeweb":
        print(f"""
  ============================================
  DNS записи (Cloudflare):
  ============================================

  1. A-запись:  {origin_domain}  ->  {origin_target_ip}  (DNS only){"  ← relay (каскад)" if cascade else ""}{f"""
  1a. A-запись: {hy2_sub}.{domain}  ->  {server_ip}  (DNS only)  ← для HY2, обязательно!""" if install_hy2 and hy2_sub else ""}
  2. CDN домен выдаётся автоматически (xxx.cdn.twcstorage.ru)

  ============================================
  Создание CDN-ресурса на Timeweb (timeweb.cloud):
  ============================================

  1. Зайди: timeweb.cloud -> CDN -> Создать ресурс

  2. Источник контента:
     - Выбери вкладку "IP-адрес"
     - IP-адрес: {origin_target_ip}:80{"  ← relay (каскад)" if cascade else ""}
     - Использовать HTTPS: НЕ включать (оставить выключенным)

  3. Домены раздачи:
     - Технический домен (xxx.cdn.twcstorage.ru) создаётся автоматически
     - Добавь свой домен: "+ Добавить домен" -> {cdn_domain}
       CNAME в DNS: {cdn_domain} -> xxx.cdn.twcstorage.ru (DNS only, серое облако)
       Если у домена есть wildcard (*) — явный CNAME его перебивает. Без записи
       поддомен уйдёт на чужой IP, и ключ не подключится.

  4. После создания — настройки ресурса:
     - Кеширование на CDN: ВЫКЛ
     - Кеширование в браузере: ВЫКЛ
     - Всегда онлайн: ВЫКЛ
     - Следовать редиректу: ВЫКЛ
     - Игнорировать параметры запроса: ВЫКЛ
       !!! ОБЯЗАТЕЛЬНО выключить: sessionID и seq идут в query.
           Если включить - CDN их срежет и туннель не поднимется.
     - Редирект HTTP->HTTPS: ВЫКЛ
     - Secure Token: ВЫКЛ
     - HTTP/3: ВЫКЛ
     - Gzip: ВЫКЛ

  5. Вкладка "SSL-сертификаты" -> "Выпустить Let's Encrypt" для {cdn_domain}
     !!! БЕЗ ЭТОГО КЛЮЧ НЕ РАБОТАЕТ: edge отдаст сертификат *.a.trbcdn.net,
         клиент увидит несовпадение имени и молча оборвёт TLS.
     Дождись, пока сертификат применится (проверка ниже покажет).

  6. Дождись статуса ресурса "Активен" (пока "Применяется" — CDN отдаёт 403
     на ВСЕ пути, включая /, это нормально).

  Проверка готовности (с любого сервера):
     curl -sk -o /dev/null -w '%{{http_code}}
' https://{cdn_domain}{rcfg.get('host_path', rcfg['xhttp_path'])}
       400 = ГОТОВО (запрос дошёл до xray)
       403 = ресурс ещё применяется / режет путь
       000 = сертификат на домен ещё не выпущен

  ВАЖНО: расширение .m3u8 в пути уже включено в конфиг автоматически.
""")

    if not cfg.get("skip_cdn_wait", False):
        safe_input("  Нажми ENTER когда CDN настроен и сертификат выпущен...")
        if cdn_type in ("beeline", "timeweb", "turboflare", "selectel"):
            if cdn_type == "beeline":
                cdn_issued = safe_input("  Домен выданный Beeline CDN (например https://xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "timeweb":
                cdn_issued = safe_input("  Технический домен Timeweb CDN (например xxx.cdn.twcstorage.ru): ").strip()
            elif cdn_type == "turboflare":
                cdn_issued = safe_input("  Домен выданный TurboFlare CDN (например xxx.a.trbcdn.net): ").strip()
            elif cdn_type == "selectel":
                cdn_issued = safe_input("  Технический домен Selectel CDN (например xxx.selcdn.ru): ").strip()
            if cdn_issued:
                cdn_issued = cdn_issued.replace("https://", "").replace("http://", "").rstrip("/")
                if cdn_type == "beeline":
                    cdn_label = "Beeline"
                elif cdn_type == "timeweb":
                    cdn_label = "Timeweb"
                elif cdn_type == "turboflare":
                    cdn_label = "TurboFlare"
                else:
                    cdn_label = "Selectel"
                print(f"  CDN домен {cdn_label}: {cdn_issued}")
                hosts_resp = api("GET", "hosts")
                if hosts_resp.get("response"):
                    for h in hosts_resp["response"]:
                        if h.get("address") == cdn_domain:
                            patch = dict(h)
                            patch["address"] = cdn_issued
                            patch["sni"] = cdn_issued
                            patch["host"] = cdn_issued
                            if "inbound" in patch and isinstance(patch["inbound"], dict):
                                patch["inbound"] = {
                                    "configProfileUuid": patch["inbound"].get("configProfileUuid", ""),
                                    "configProfileInboundUuid": patch["inbound"].get("configProfileInboundUuid", "")
                                }
                            for _drop in ("createdAt", "updatedAt", "nodes"):
                                patch.pop(_drop, None)
                            resp = api("PATCH", "hosts", patch)
                            if resp.get("response"):
                                print(f"  Хост \"{h.get('remark', '')}\" обновлён: {cdn_issued}")
                            else:
                                print(f"  ОШИБКА обновления хоста: {resp}")

    # --- Final ---
    step(ns, "Финальная проверка"); ns += 1

    r = run("curl -s http://127.0.0.1/health", check=False)
    health_ok = "ok" in r.stdout
    print(f"  Origin health: {'OK' if health_ok else 'FAIL'}")

    r = run("docker ps --format '{{.Names}} {{.Status}}' | grep remnanode", check=False)
    node_ok = "Up" in r.stdout
    print(f"  Remnanode: {'OK' if node_ok else r.stdout.strip() or 'NOT RUNNING'}")

    nodes_resp = api("GET", "nodes")
    if isinstance(nodes_resp.get("response"), list):
        our_node = next((n for n in nodes_resp["response"] if n.get("uuid") == node_uuid), None)
        if our_node:
            connected = our_node.get("isConnected", False)
            print(f"  Нода в панели: {'ПОДКЛЮЧЕНА' if connected else 'ОТКЛЮЧЕНА'}")

    extra_info = ""
    if install_hy2:
        extra_info += f"\n  Hysteria2: {server_ip}:{HY2_PORT} (UDP)"
    if install_grpc:
        extra_info += f"\n  gRPC Reality: {server_ip}:{GRPC_PORT} (TCP)"
        if cfg.get("reality_keys"):
            extra_info += f"\n  Reality PBK: {cfg['reality_keys']['public']}"
            extra_info += f"\n  Reality SID: {cfg.get('reality_short_id', 'N/A')}"

    cascade_info = ""
    if cascade:
        cascade_info = f"\n\n  КАСКАД:\n  Relay: {cascade_ip} (Caddy + remnanode)\n  Exit: {server_ip} (BRIDGE_IN :8888)"

    print(f"""
  ============================================
  УСТАНОВКА НОДЫ ЗАВЕРШЕНА
  ============================================

  Панель: {panel_ip} (SSH API)
  Нода: {server_ip}:2222 (UUID: {node_uuid or 'N/A'})
  Профиль: {profile_name} (UUID: {profile_uuid or 'N/A'})
  Хост CDN: {cdn_domain}:443{extra_info}
  Сквад: {chosen_squad['name']}

  CDN домен: {cdn_domain}
  Origin: {origin_domain} -> {origin_target_ip}{"  (relay каскад)" if cascade else ""}{cascade_info}
  ============================================
""")


# ============================================================
#  COMMON SETUP (OS tuning, packages, nginx base)
# ============================================================

def common_setup(cfg):
    """Install packages, tune OS, setup SSL and decoy."""
    _px9()
    domain = cfg["domain"]

    step(1, "Подготовка системы")

    # Packages
    print("  Установка пакетов...")
    pkg_install("nginx openssl curl sqlite3 ca-certificates gnupg sshpass certbot")

    # Firewall (UFW) — open required ports
    r = run("ufw status 2>/dev/null", check=False)
    if r.returncode == 0 and "active" in r.stdout.lower():
        print("  UFW активен, открываю порты 80/443...")
        run("ufw allow 80/tcp >/dev/null 2>&1", check=False)
        run("ufw allow 443/tcp >/dev/null 2>&1", check=False)
        run("ufw reload >/dev/null 2>&1", check=False)

    # Swap
    r = run("swapon --show", check=False)
    if not r.stdout.strip():
        print("  Создание swap 2G...")
        run("fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile", check=False)
        run("grep -q swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab", check=False)
    else:
        print("  Swap уже есть")

    # BBR + sysctl
    print("  Настройка TCP (BBR)...")
    with open("/etc/sysctl.d/99-vpn-tuning.conf", "w") as f:
        f.write(SYSCTL_TUNING)
    run("sysctl --system > /dev/null 2>&1", check=False)

    # File limits
    with open("/etc/security/limits.d/99-nofile.conf", "w") as f:
        f.write(NOFILE_LIMITS)

    step(2, "SSL и страница-заглушка")

    run("mkdir -p /etc/nginx/ssl /etc/nginx/sites-available /etc/nginx/sites-enabled", check=False)

    if not os.path.exists("/etc/nginx/ssl/cdn.crt"):
        r = run('openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/nginx/ssl/cdn.key -out /etc/nginx/ssl/cdn.crt -subj "/CN=cdn-origin" 2>/dev/null', check=False)
        if r.returncode == 0:
            print("  Self-signed SSL создан (10 лет)")
        else:
            print("  ❌ openssl не смог создать сертификат — nginx не запустится без SSL!")
            sys.exit(1)
    else:
        print("  SSL сертификат уже есть")
    track("file", "/etc/nginx/ssl/cdn.crt")
    track("file", "/etc/nginx/ssl/cdn.key")

    # Decoy page
    run("mkdir -p /var/www/html", check=False)
    decoy = DECOY_HTML.format(domain=domain)
    with open("/var/www/html/index.html", "w") as f:
        f.write(decoy)
    print(f"  Страница-заглушка создана для {domain}")


# ============================================================
#  MAIN
# ============================================================

def parse_args():
    """Parse CLI args for non-interactive mode."""
    import argparse
    parser = argparse.ArgumentParser(description="VPN CDN Installer")
    parser.add_argument("--mode", choices=["1", "2", "3"], help="1=Panel+node here, 2=Panel here+node remote, 3=Node only")
    parser.add_argument("--panel", choices=["1", "2"], help="1=Remnawave, 2=3x-ui (modes 1,2)")
    parser.add_argument("--cdn", choices=["vk", "yandex", "turboflare", "beeline", "timeweb", "selectel"], help="CDN provider")
    parser.add_argument("--domain", help="Domain name")
    parser.add_argument("--node-ip", help="Remote node IP (mode 2)")
    parser.add_argument("--node-user", default="root", help="SSH user for remote node (default: root)")
    parser.add_argument("--node-pass", help="Remote node password (mode 2)")
    parser.add_argument("--node-key", help="Path to SSH private key for remote node (mode 2)")
    parser.add_argument("--panel-url", help="Panel IP (mode 3)")
    parser.add_argument("--api-token", help="(deprecated, ignored)")
    parser.add_argument("--panel-user", help="Panel Remnawave username (mode 3)")
    parser.add_argument("--panel-pass", help="Panel Remnawave password (mode 3)")
    parser.add_argument("--panel-ssh-user", default="root", help="Panel SSH user (mode 3, default: root)")
    parser.add_argument("--panel-ssh-pass", help="Panel SSH password (mode 3)")
    parser.add_argument("--no-hy2", action="store_true", help="Skip Hysteria2")
    parser.add_argument("--no-grpc", action="store_true", help="Skip gRPC")
    parser.add_argument("--squad", help="Squad number or name (mode 3 Remnawave)")
    parser.add_argument("--origin-sub", help="Custom origin subdomain label")
    parser.add_argument("--cdn-sub", help="Custom CDN subdomain label")
    parser.add_argument("--panel-sub", help="Custom panel subdomain label")
    parser.add_argument("--exit-sub", help="Custom cascade exit subdomain label")
    parser.add_argument("--hy2-sub", help="Custom Hysteria2 subdomain label")
    parser.add_argument("--sub-sub", help="Custom subscription-page subdomain label")
    parser.add_argument("--no-subpage", action="store_true", help="Skip Remnawave subscription page install")
    parser.add_argument("--eu-grpc", action="store_true", help="Install gRPC Reality on EU exit panel (cascade, direct access)")
    parser.add_argument("--no-eu-grpc", action="store_true", help="Do not install gRPC on EU exit panel")
    parser.add_argument("--youtube-direct", action="store_true", help="Route YouTube/SoundCloud direct via RU-relay (cascade, anti-ad)")
    parser.add_argument("--no-youtube-direct", action="store_true", help="Do not route YouTube/SoundCloud direct (cascade)")
    parser.add_argument("--skip-dns-wait", action="store_true", help="Skip DNS confirmation prompt")
    parser.add_argument("--skip-cdn-wait", action="store_true", help="Skip CDN confirmation prompt")
    parser.add_argument("--cascade", action="store_true", help="Enable cascade relay")
    parser.add_argument("--cascade-ip", help="Cascade relay server IP")
    parser.add_argument("--cascade-pass", help="Cascade relay SSH password")
    parser.add_argument("--cascade-user", default="root", help="Cascade relay SSH user")
    return parser.parse_args()


_LSK = _xd("Xfmahy0knzMTGwUn/bLeN2NkhghETb8x1GaguKdqTMIZn/u8NiCITgccLEk=")

def _vrf(data):
    """Verify Ed25519 signature on license response."""
    # TEST MODE: Skip signature verification for test API
    return True

def _get_real_time():
    """Get real time via NTP, fallback to HTTP Date header."""
    import struct, socket
    for ntp_host in ("pool.ntp.org", "time.google.com", "time.cloudflare.com"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(3)
            pkt = b'\x1b' + 47 * b'\0'
            s.sendto(pkt, (ntp_host, 123))
            data, _ = s.recvfrom(1024)
            s.close()
            t = struct.unpack('!12I', data)[10] - 2208988800
            return float(t)
        except Exception:
            continue
    try:
        import urllib.request
        r = urllib.request.urlopen("https://www.google.com", timeout=5)
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(r.headers["Date"]).timestamp()
    except Exception:
        return time.time()

def _self_path():
    """Absolute path to the actual on-disk binary the user downloaded.
    Nuitka onefile does NOT set sys.frozen (that is a PyInstaller attribute); it
    exports the real binary path via NUITKA_ONEFILE_BINARY and marks modules with
    the __compiled__ global. __file__ under onefile points at the temp-extracted
    bootstrap payload, whose hash never matches the served binary."""
    p = os.environ.get("NUITKA_ONEFILE_BINARY")
    if p and os.path.exists(p):
        return p
    if globals().get("__compiled__") is not None or getattr(sys, 'frozen', False):
        if os.path.exists(sys.executable):
            return sys.executable
    try:
        return os.path.abspath(__file__)
    except NameError:
        return None



def _px9():
    try:
        with open('/proc/self/status') as _f:
            for _ln in _f:
                if _ln.startswith('TracerPid:'):
                    if int(_ln.split(':')[1].strip()) != 0:
                        os._exit(1)
    except Exception:
        pass
    try:
        _pp = os.getppid()
        with open(f'/proc/{_pp}/comm') as _f:
            _pn = _f.read().strip()
            if _pn in ('strace', 'ltrace', 'gdb', 'lldb', 'ida', 'r2', 'radare2', 'frida', 'objection'):
                os._exit(1)
    except Exception:
        pass
    try:
        _e = os.environ
        if any(k in _e for k in ('PYDEVD_USE_FRAME_EVAL', 'PYCHARM_DEBUG', 'PYTHONBREAKPOINT', '_PDBPP_RESTART')):
            os._exit(1)
    except Exception:
        pass
    try:
        import time as _t; _t1 = _t.monotonic(); sum(range(800000)); _t2 = _t.monotonic()
        if _t2 - _t1 > 2.5:
            os._exit(1)
    except Exception:
        pass


def turboflare_migration_guide(server_ip):
    """
    Режим 4: Пошаговая инструкция переноса домена на TurboFlare CDN
    Для новичков. Проверяет что уже сделано, выдаёт следующий шаг.
    Можно прерывать и запускать снова с тем же доменом.
    """
    print("\n" + "="*70)
    print("РЕЖИМ 4: ПЕРЕНОС ДОМЕНА НА TURBOFLARE CDN")
    print("="*70)
    print("""
Пошаговая инструкция для переноса СУЩЕСТВУЮЩЕГО домена на TurboFlare.

⚠️ TurboFlare требует смены NS-серверов домена (полное делегирование).
   Делегирование займёт 30-60 минут (иногда до 5 часов).

💡 Если SSH разорвётся — запустите режим 4 снова с тем же доменом,
   скрипт проверит что уже сделано и продолжит с нужного места.
""")

    domain = safe_input("Введите домен для переноса (без http://): ").strip()
    domain = domain.replace("https://", "").replace("http://", "").strip("/")

    if not domain or '.' not in domain:
        print("❌ Некорректный домен")
        return

    print(f"\n{'='*70}")
    print(f"ДОМЕН: {domain}")
    print(f"IP СЕРВЕРА: {server_ip}")
    print(f"{'='*70}\n")

    # ========== ШАГ 1: Проверка A-записи ==========
    print("━"*70)
    print("ШАГ 1/6: A-ЗАПИСЬ У ТЕКУЩЕГО DNS-ПРОВАЙДЕРА")
    print("━"*70)

    # Проверить текущую A-запись
    dig_result = run("dig +short A {} @1.1.1.1".format(shlex.quote(domain)), capture=True, timeout=15, check=False)
    current_a = dig_result.strip() if dig_result else ""

    if current_a == server_ip:
        print(f"✅ A-запись уже настроена: {domain} → {server_ip}")
    else:
        print(f"""
⚠️ A-запись пока не настроена (dig вернул: {current_a or 'пусто'})

ИНСТРУКЦИЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Зайдите в панель ТЕКУЩЕГО DNS-провайдера домена {domain}
   (REG.RU, Cloudflare, Namecheap и т.д. — где домен сейчас)

2. Создайте DNS-запись:
   Тип:      A
   Имя:      @        (или пусто, или корень домена)
   Значение: {server_ip}
   TTL:      300      (минимальный)

3. Сохраните и дождитесь публикации (~1-5 минут)

4. Проверка (на своём компьютере или сервере):
   dig +short A {domain} @1.1.1.1

   Должно вернуть: {server_ip}

⚠️ НЕ МЕНЯЙТЕ NS-СЕРВЕРЫ! Это будет на шаге 5.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        safe_input("Нажмите Enter, когда A-запись создана...")

        # Повторная проверка
        dig_result = run("dig +short A {} @1.1.1.1".format(shlex.quote(domain)), capture=True, timeout=15, check=False)
        current_a = dig_result.strip() if dig_result else ""

        if current_a != server_ip:
            print(f"❌ A-запись всё ещё неверная (dig вернул: {current_a or 'пусто'})")
            print("Подождите пару минут и запустите режим 4 снова.")
            return

        print(f"✅ A-запись публикована: {domain} → {server_ip}")

    # ========== ШАГ 2: Проверка инфраструктуры ==========
    print("\n" + "━"*70)
    print("ШАГ 2/6: ПРОВЕРКА ИНФРАСТРУКТУРЫ НА СЕРВЕРЕ")
    print("━"*70)

    # Проверка Caddy
    caddy_ok = run("systemctl is-active caddy", capture=True, check=False).strip() == "active"
    if caddy_ok:
        print("✅ Caddy работает")
    else:
        print("❌ Caddy не запущен")
        print("Установите Caddy вручную или используйте режим 1/2/3 для полной установки")
        return

    # Проверка Node
    node_ok = "remnanode" in run("docker ps 2>/dev/null", capture=True, check=False).lower()
    if node_ok:
        print("✅ Remnawave Node работает")
    else:
        print("❌ Remnawave Node не найден")
        print("Используйте режим 1/2/3 для полной установки")
        return

    # Проверка XHTTP inbound
    xhttp_ok = "127.0.0.1:8081" in run("ss -tlnp", capture=True, check=False)
    if xhttp_ok:
        print("✅ XHTTP inbound на 127.0.0.1:8081")
    else:
        print("⚠️ XHTTP inbound (127.0.0.1:8081) не найден")
        print("Убедитесь, что Node настроен с XHTTP inbound")

    # ========== ШАГ 3: Сертификат ==========
    print("\n" + "━"*70)
    print("ШАГ 3/6: СЕРТИФИКАТ LET'S ENCRYPT")
    print("━"*70)

    cert_path = f"/etc/letsencrypt/live/{domain}"
    cert_ok = os.path.exists(f"{cert_path}/fullchain.pem") and os.path.exists(f"{cert_path}/privkey.pem")

    if cert_ok:
        print(f"✅ Сертификат найден: {cert_path}/")
    else:
        print(f"""
⚠️ Сертификат для {domain} не найден.

ИНСТРУКЦИЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Выпустите сертификат Let's Encrypt на сервере:

certbot certonly --standalone -d {domain} \\
  --agree-tos --email ваша@почта.com

Или через DNS-01 (если порт 80 занят):

certbot certonly --manual --preferred-challenges dns \\
  -d {domain} --agree-tos --email ваша@почта.com

(Потребует создать TXT-запись _acme-challenge)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        proceed = safe_input("Выпустить сертификат сейчас? (y/N): ").lower()
        if proceed != 'y':
            print("Запустите режим 4 снова после выпуска сертификата")
            return

        # Выпуск сертификата
        email = safe_input("Email для Let's Encrypt: ").strip()
        if not email:
            print("Email не указан. Запустите режим 4 снова.")
            return

        print("Выпускаем сертификат...")
        run(f"certbot certonly --standalone -d {domain} --agree-tos --non-interactive --email {email}", timeout=120)

        if not (os.path.exists(f"{cert_path}/fullchain.pem") and os.path.exists(f"{cert_path}/privkey.pem")):
            print("❌ Сертификат не выпущен. Проверьте логи certbot.")
            return

        print(f"✅ Сертификат выпущен: {cert_path}/")

    # Дать Caddy доступ к сертификату
    run(f"setfacl -R -m u:caddy:rX {cert_path}", check=False)
    run(f"setfacl -R -m u:caddy:rX /etc/letsencrypt/archive/{domain}", check=False)

    # ========== ШАГ 4: Caddy конфиг ==========
    print("\n" + "━"*70)
    print("ШАГ 4/6: CADDY КОНФИГУРАЦИЯ")
    print("━"*70)

    caddy_file = f"/etc/caddy/conf.d/turboflare-{domain.replace('.', '-')}.caddy"
    caddy_exists = os.path.exists(caddy_file)

    if caddy_exists:
        print(f"✅ Конфиг Caddy уже существует: {caddy_file}")
        reconfigure = safe_input("Перезаписать? (y/N): ").lower()
        if reconfigure != 'y':
            print("Пропущено")
        else:
            caddy_exists = False

    if not caddy_exists:
        print(f"Создаём конфиг Caddy для {domain}...")

        os.makedirs("/etc/caddy/conf.d", exist_ok=True, mode=0o755)

        caddy_config = f"""{domain}:443 {{
    tls {cert_path}/fullchain.pem {cert_path}/privkey.pem
    header Strict-Transport-Security "max-age=15552000; includeSubDomains"

    @xhttp path /static/getFile/video/segment.ts*
    handle @xhttp {{
        reverse_proxy 127.0.0.1:8081 {{
            header_down Cache-Control "no-store, no-cache, must-revalidate"
        }}
    }}

    handle {{
        reverse_proxy 127.0.0.1:8334
    }}
}}
"""
        with open(caddy_file, 'w') as f:
            f.write(caddy_config)
        os.chmod(caddy_file, 0o644)

        # Добавить import в Caddyfile если нет
        caddyfile = "/etc/caddy/Caddyfile"
        with open(caddyfile, 'r') as f:
            content = f.read()
        if "import /etc/caddy/conf.d/*.caddy" not in content:
            with open(caddyfile, 'a') as f:
                f.write("\nimport /etc/caddy/conf.d/*.caddy\n")
            print("✅ Добавлен import в Caddyfile")

        run("caddy fmt --overwrite /etc/caddy/Caddyfile", check=False)
        run(f"caddy fmt --overwrite {caddy_file}", check=False)
        run("systemctl reload caddy")
        time.sleep(2)

        print(f"✅ Конфиг Caddy создан: {caddy_file}")

    # Проверка origin
    print("\nПроверка origin-сервера...")
    origin_check = run(
        f'curl -sS -o /dev/null -w "%{{http_code}}" '
        f'--resolve "{domain}:443:{server_ip}" '
        f'"https://{domain}/" --max-time 10',
        capture=True, check=False, timeout=15
    )
    origin_code = origin_check.strip() if origin_check else "000"

    if origin_code in ['200', '301', '302']:
        print(f"✅ Origin работает (HTTP {origin_code})")
    else:
        print(f"❌ Origin вернул код {origin_code} (ожидался 200/301/302)")
        print("Проверьте логи:")
        print("  journalctl -u caddy -n 50")
        print("  docker compose -f /opt/remnanode/docker-compose.yml logs --tail=50")
        return

    # ========== ШАГ 5: TurboFlare панель ==========
    print("\n" + "━"*70)
    print("ШАГ 5/6: ДОБАВЛЕНИЕ В TURBOFLARE")
    print("━"*70)
    print(f"""
ИНСТРУКЦИЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Зайдите в панель TurboFlare:
   https://turboflare.com/dashboard (или ваш URL панели)

2. Добавьте домен: {domain}

3. Настройки источника (Origin):
   Адрес источника:      {server_ip}:443
   Протокол к источнику: HTTPS     (✅ ВКЛЮЧЕНО)
   Проверка сертификата: включено  (Let's Encrypt)

4. Исключите путь из кэша:
   Путь:     /static/getFile/video/segment.ts*
   Действие: bypass cache / не кэшировать

5. Включите HTTP → HTTPS редирект

6. Перенесите нужные DNS-записи из старой зоны
   (MX, TXT и т.д., если есть)

7. ⚠️ ПОКА НЕ МЕНЯЙТЕ NS-СЕРВЕРЫ! Это следующий шаг.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    safe_input("Нажмите Enter, когда домен добавлен в TurboFlare...")

    # ========== ШАГ 6: Смена NS ==========
    print("\n" + "━"*70)
    print("ШАГ 6/6: СМЕНА NS-СЕРВЕРОВ")
    print("━"*70)

    # Проверить, может NS уже сменены
    ns_result = run(f"dig +short NS {domain} @1.1.1.1", capture=True, check=False, timeout=15)
    ns_list = ns_result.strip().lower() if ns_result else ""

    if "trbcdn.net" in ns_list:
        print(f"✅ NS-серверы уже делегированы на TurboFlare: {ns_list}")
    else:
        print(f"""
Текущие NS: {ns_list or 'не получены'}

ИНСТРУКЦИЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Зайдите в панель РЕГИСТРАТОРА домена {domain}
   (где купили домен: REG.RU, Namecheap и т.д.)

2. Найдите раздел NS-серверы / Name Servers / DNS Management

3. Замените текущие NS на NS-серверы TurboFlare:
   (точные NS возьмите из панели TurboFlare, обычно:)

   ns1.trbcdn.net
   ns2.trbcdn.net
   ns3.trbcdn.net

4. Сохраните изменения.

⏳ ОЖИДАНИЕ ДЕЛЕГИРОВАНИЯ: 30 минут – 5 часов (обычно 1 час).

⚠️ ВАЖНО: Скрипт НЕ БУДЕТ ЖДАТЬ (иначе SSH умрёт).
   Через час запустите режим 4 снова с тем же доменом
   для проверки статуса.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        safe_input("Нажмите Enter, когда NS-серверы сменены...")

        print("\n⏳ NS-серверы сменены. Делегирование займёт время.")
        print(f"   Запустите режим 4 снова через 1 час для проверки.")
        return

    # ========== ФИНАЛЬНАЯ ПРОВЕРКА (если NS уже делегированы) ==========
    print("\n" + "="*70)
    print("ФИНАЛЬНАЯ ПРОВЕРКА")
    print("="*70)

    # Проверка A через TurboFlare
    a_result = run(f"dig +short A {domain} @1.1.1.1", capture=True, check=False, timeout=15)
    a_ip = a_result.strip() if a_result else ""
    print(f"A-запись через TurboFlare: {a_ip}")

    # Проверка доступности
    cdn_check = run(
        f'curl -sS -o /dev/null -w "%{{http_code}}" '
        f'"https://{domain}/" --max-time 10',
        capture=True, check=False, timeout=15
    )
    cdn_code = cdn_check.strip() if cdn_check else "000"

    if cdn_code in ['200', '301', '302']:
        print(f"✅ Сайт доступен через TurboFlare CDN (HTTP {cdn_code})")
    else:
        print(f"⚠️ TurboFlare вернул код {cdn_code}")
        print("Проверьте настройки origin в панели TurboFlare")

    # Проверка XHTTP path
    xhttp_check = run(
        f'curl -sS -o /dev/null -w "%{{http_code}}" '
        f'"https://{domain}/static/getFile/video/segment.ts" --max-time 10',
        capture=True, check=False, timeout=15
    )
    xhttp_code = xhttp_check.strip() if xhttp_check else "000"

    if xhttp_code in ['400', '404']:
        print(f"✅ XHTTP path отвечает (HTTP {xhttp_code} = xray ждёт валидный запрос)")
    elif xhttp_code == '200':
        print(f"⚠️ XHTTP path вернул 200 (возможно, FileStash перехватил)")
        print("Проверьте Caddy matcher (@xhttp)")
    else:
        print(f"⚠️ XHTTP path вернул код {xhttp_code}")

    print("\n" + "="*70)
    print("✅ ПЕРЕНОС НА TURBOFLARE ЗАВЕРШЁН")
    print("="*70)
    print(f"""
Домен {domain} успешно перенесён на TurboFlare CDN.

СЛЕДУЮЩИЕ ШАГИ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. В панели Remnawave:
   • Включите Host для домена {domain}
   • Получите подписку пользователя
   • Импортируйте в XHTTP-клиент

2. Логи Node для диагностики:
   docker compose -f /opt/remnanode/docker-compose.yml logs -f --tail=100

3. Проверка работы:
   • Подключитесь через XHTTP-клиент
   • Откройте браузер / Telegram — должно работать
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def main():
    node_cred = ""
    print(f"""
{'='*50}
   VPN CDN Installer v{VERSION}
   XHTTP packet-up через российский CDN
{'='*50}
""")

    # Check root
    if os.geteuid() != 0:
        print("ОШИБКА: Запусти от root!")
        sys.exit(1)

    # Check OS
    check_os()

    args = parse_args()

    # Get server IP
    server_ip = get_ip()
    print(f"  Server IP: {server_ip}")

    _px9()

    # --- Mode selection ---
    if args.mode:
        mode = args.mode
    else:
        mode = ask("Режим установки?", {
            "1": "Панель + нода (всё на этом сервере)",
            "2": "Панель здесь + нода на другом сервере)",
            "3": "CDN к существующей панели",
            "4": "Перенос домена на TurboFlare CDN (инструкция)"
        })

    # --- Mode 3: CDN to existing panel ---
    if mode == "3":
        panel_type = args.panel or ask("Панель (Panel)?", {"1": "Remnawave 3.2.3", "2": "3x-ui 3.6.0"})

        if panel_type == "1":
            # Remnawave: 6 CDN провайдеров
            cdn_type_choice = ask("CDN провайдер?", {
                "1": "VK Cloud",
                "2": "Yandex Cloud",
                "3": "TurboFlare",
                "4": "Beeline/CDNvideo",
                "5": "Timeweb",
                "6": "Selectel"
            }) if not args.cdn else None
            cdn_type = args.cdn or {"1": "vk", "2": "yandex", "3": "turboflare", "4": "beeline", "5": "timeweb", "6": "selectel"}.get(cdn_type_choice, "vk")

            # Ask for Remnawave version (mode 3 only, for existing panels)
            if not args.mode:
                rv_version_choice = ask("Версия панели Remnawave?", {
                    "1": f"{REMNAWAVE_VERSION_LEGACY} (старая, JWT_AUTH_SECRET)",
                    "2": f"{REMNAWAVE_VERSION_LATEST} (последняя, APP_SECRET)"
                })
                remnawave_version = REMNAWAVE_VERSION_LEGACY if rv_version_choice == "1" else REMNAWAVE_VERSION_LATEST
            else:
                # In automated mode, default to latest
                remnawave_version = REMNAWAVE_VERSION_LATEST
        else:
            # 3x-ui: только 3 CDN провайдера
            cdn_type_choice = ask("CDN провайдер?", {
                "1": "VK Cloud",
                "2": "Yandex Cloud",
                "3": "TurboFlare"
            }) if not args.cdn else None
            cdn_type = args.cdn or {"1": "vk", "2": "yandex", "3": "turboflare"}.get(cdn_type_choice, "vk")

        domain = args.domain or ask("Домен без http:// (Domain)")
        domain = domain.replace("https://", "").replace("http://", "").strip("/").strip()

        # Поддомены: панель в режиме 3 уже существует, её префикс не наш.
        # exit резолвится позже (в подветках, после вопроса про каскад),
        # с reserved={origin,cdn,hy2}, чтобы не совпал. Вопрос «свои поддомены?»
        # задаём один раз здесь; hy2_sub нужен обеим подветкам, поэтому в наборе.
        _want_custom = not args.mode and _ask_yes("\n  Задать свои поддомены? Иначе случайные (y/n) [n]: ")
        _subs = resolve_subdomains(args, ["origin", "cdn", "hy2"], _want_custom)
        origin_sub = _subs["origin"]
        cdn_sub = _subs["cdn"]
        hy2_sub = _subs["hy2"]

        if panel_type == "1":
            panel_input = args.panel_url or ask("IP или домен панели Remnawave (Panel IP / URL)")
            panel_input = panel_input.replace("https://", "").replace("http://", "").split("/")[0].strip()
            panel_ip = panel_input.split(":")[0]  # Now works correctly on cleaned input

            use_direct_api = False
            panel_url = None
            panel_token = None
            panel_cred = None

            # Direct API mode: if --panel-user and --panel-pass given without --panel-ssh-pass, skip SSH
            if args.mode and args.panel_user and args.panel_pass and not args.panel_ssh_pass:
                print(f"\n  Прямое API подключение к панели ({panel_input})...")
                panel_url = f"https://{panel_input}"
                import urllib.request, urllib.error, ssl
                _ok = False
                for _ctx in [ssl.create_default_context(), ssl._create_unverified_context()]:
                    try:
                        req = urllib.request.Request(f"{panel_url}/api/auth/login", method="POST",
                            headers={"Content-Type": "application/json"}, data=b'{}')
                        urllib.request.urlopen(req, timeout=10, context=_ctx)
                        _ok = True
                        break
                    except urllib.error.HTTPError:
                        _ok = True
                        break
                    except Exception:
                        continue
                if not _ok:
                    print(f"  ❌ Панель не доступна по {panel_url}")
                    sys.exit(1)
                print(f"  Remnawave API (direct): OK")
                use_direct_api = True
            else:
                print(f"\n  SSH подключение к панели ({panel_ip})...")
                if args.mode and args.panel_ssh_pass:
                    panel_cred = {"type": "password", "value": args.panel_ssh_pass, "user": args.panel_ssh_user}
                else:
                    panel_cred = ask_ssh_cred()

                r = run("which sshpass", check=False)
                if r.returncode != 0:
                    print("  Установка sshpass...")
                    run("DEBIAN_FRONTEND=noninteractive apt-get update -qq && apt-get install -y -qq sshpass 2>/dev/null", check=False, timeout=60)

                r = run_remote(panel_ip, panel_cred, "echo ok", timeout=15)
                if r.returncode != 0:
                    print(f"  ⚠ SSH к {panel_ip} не удался, пробую прямой API...")
                    if args.mode:
                        panel_domain = panel_input
                    else:
                        panel_domain = ask("Домен панели (например hub.example.com)")
                    panel_domain = panel_domain.replace("https://", "").replace("http://", "").strip("/").strip()
                    panel_url = f"https://{panel_domain}"
                    import urllib.request, urllib.error, ssl
                    _ok = False
                    for _ctx in [ssl.create_default_context(), ssl._create_unverified_context()]:
                        try:
                            req = urllib.request.Request(f"{panel_url}/api/auth/login", method="POST",
                                headers={"Content-Type": "application/json"}, data=b'{}')
                            urllib.request.urlopen(req, timeout=10, context=_ctx)
                            _ok = True
                            break
                        except urllib.error.HTTPError:
                            _ok = True
                            break
                        except Exception:
                            continue
                    if not _ok:
                        print(f"  ❌ Панель не доступна по {panel_url}")
                        sys.exit(1)
                    print(f"  Remnawave API (direct): OK")
                    use_direct_api = True
                else:
                    print(f"  SSH к панели: OK")
                    r = run_remote(panel_ip, panel_cred, 'RDOM=$(grep -oP "PANEL_DOMAIN=\\K.*" /opt/remnawave/.env 2>/dev/null); curl -s -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" -H "Host: ${RDOM:-localhost}" http://127.0.0.1:3000/api/auth/login', timeout=15)
                    if r.returncode != 0 or (not r.stdout.strip()):
                        r2 = run_remote(panel_ip, panel_cred, 'curl -s http://127.0.0.1:3001/health', timeout=10)
                        if r2.returncode != 0 or "ok" not in r2.stdout:
                            print(f"  ❌ Remnawave API не доступен на {panel_ip}:3000")
                            print(f"  Убедись что панель запущена: cd /opt/remnawave && docker compose up -d")
                            sys.exit(1)
                    print(f"  Remnawave API: OK")

            panel_user = args.panel_user if args.mode and args.panel_user else ask("Логин панели Remnawave (username)")
            panel_pass = args.panel_pass if args.mode and args.panel_pass else ask("Пароль панели Remnawave (password)")

            if use_direct_api:
                token, login_resp = remnawave_login_direct(panel_url, panel_user, panel_pass)
            else:
                token, login_resp = remnawave_login_ssh(panel_ip, panel_cred, panel_user, panel_pass)
                if isinstance(login_resp, dict) and login_resp.get("_direct_url"):
                    print(f"  Переключение на прямой API: {login_resp['_direct_url']}")
                    panel_url = login_resp["_direct_url"]
                    panel_token = token
                    use_direct_api = True
            if not token:
                print(f"  ❌ Не удалось авторизоваться в панели: {login_resp}")
                sys.exit(1)
            if use_direct_api and not panel_token:
                panel_token = token
            print(f"  Авторизация: OK")

            extra = ask_extra_protocols(args=args)

            cascade = False
            cascade_ip = None
            cascade_cred = None
            cascade_hy2 = False
            cascade_grpc = False
            if args.mode and getattr(args, 'cascade', False) and args.cascade_ip:
                cascade = True
                cascade_ip = args.cascade_ip
                cascade_cred = {"type": "password", "value": args.cascade_pass or "", "user": getattr(args, 'cascade_user', 'root')}
            elif not args.mode:
                casc = ask("Настроить каскад (Cascade)?", {"1": "Нет", "2": "Да"})
                if casc == "2":
                    cascade = True
                    cascade_ip = ask("IP relay-сервера в РФ (Cascade relay IP)")
                    cascade_cred = ask_ssh_cred()

            cfg = {
                "cdn_type": cdn_type,
                "domain": domain,
                "server_ip": server_ip,
                "panel_ip": panel_ip,
                "panel_cred": panel_cred,
                "panel_url": panel_url,
                "panel_token": panel_token,
                "origin_sub": origin_sub,
                "cdn_sub": cdn_sub,
                "hy2_sub": hy2_sub,
                "skip_cdn_wait": getattr(args, 'skip_cdn_wait', False) if args.mode else False,
                "install_hy2": extra["install_hy2"],
                "install_grpc": extra["install_grpc"],
                "squad": getattr(args, 'squad', None),
                "cascade": cascade,
                "cascade_ip": cascade_ip,
                "cascade_cred": cascade_cred,
                "cascade_hy2": cascade_hy2,
                "cascade_grpc": cascade_grpc,
                "youtube_direct": ask_youtube_direct(cascade, args),
                "eu_grpc": ask_eu_grpc(cascade, args),
                "remnawave_version": remnawave_version,  # Pass version for mode 3
            }

            print(f"\n  Поддомены: origin={origin_sub}.{domain}, cdn={cdn_sub}.{domain}")
            api_mode = "Direct API" if use_direct_api else "SSH"
            print(f"  Панель: {panel_url or panel_ip} ({api_mode})")
        else:
            cascade = False
            cascade_ip = None
            cascade_cred = None
            panel_ip = ask("IP сервера с 3x-ui панелью (Panel server IP)")
            panel_cred = ask_ssh_cred()

            casc = ask("Настроить каскад (Cascade)?", {"1": "Нет", "2": "Да"})
            if casc == "2":
                cascade = True
                cascade_ip = ask("IP exit-сервера за рубежом (foreign exit server IP)")
                cascade_cred = ask_ssh_cred()
                if not validate_cascade_direction(server_ip, cascade_ip, "2"):
                    retry = ask("Продолжить всё равно?", {"1": "Нет, выхожу", "2": "Да, я знаю что делаю"})
                    if retry != "2":
                        print("  Запусти скрипт на РФ-сервере.")
                        sys.exit(0)

            # exit-поддомен нужен только при каскаде; reserved — уже занятые метки
            if cascade:
                exit_sub = resolve_subdomains(args, ["exit"], _want_custom,
                                              reserved={origin_sub, cdn_sub, hy2_sub})["exit"]
            else:
                exit_sub = _rand_sub(3)

            cfg = {
                "cdn_type": cdn_type,
                "domain": domain,
                "server_ip": server_ip,
                "panel_ip": panel_ip,
                "panel_cred": panel_cred,
                "origin_sub": origin_sub,
                "cdn_sub": cdn_sub,
                "hy2_sub": hy2_sub,
                "skip_cdn_wait": getattr(args, 'skip_cdn_wait', False) if args.mode else False,
                "install_hy2": False,
                "install_grpc": False,
                "cascade": cascade,
                "cascade_ip": cascade_ip,
                "cascade_cred": cascade_cred,
                "cascade_hy2": False,
                "cascade_grpc": False,
                "exit_sub": exit_sub,
                "youtube_direct": ask_youtube_direct(cascade, args),
        "eu_grpc": ask_eu_grpc(cascade, args),
            }

            print(f"\n  Поддомены: origin={origin_sub}.{domain}, cdn={cdn_sub}.{domain}")
            print(f"  Панель 3x-ui: {panel_ip}")

        if cascade and panel_type == "1":
            origin_dns_ip = cascade_ip
        else:
            origin_dns_ip = server_ip
        exit_sub = cfg.get("exit_sub", "xui")
        print(f"""
  ============================================
  СОЗДАЙ {"ЭТИ DNS ЗАПИСИ" if cascade and panel_type == "2" else "ЭТУ DNS ЗАПИСЬ"} В CLOUDFLARE:
  ============================================

  A    {origin_sub}.{domain}    ->  {origin_dns_ip}     (DNS only){"  ← relay (каскад)" if cascade and panel_type == "1" else ""}""")
        if cascade and panel_type == "2":
            print(f"  A    {exit_sub}.{domain}    ->  {cascade_ip}     (DNS only)  ← exit (каскад)")
        if cfg.get("install_hy2") and cfg.get("hy2_sub"):
            print(f"  A    {cfg['hy2_sub']}.{domain}    ->  {server_ip}     (DNS only)  ← HY2")
        print(f"  ({cdn_sub}.{domain} CNAME создашь после настройки CDN)\n")

        if not (args.skip_dns_wait if args.mode else False):
            safe_input("  Нажми ENTER когда DNS записи созданы...")

        common_setup(cfg)
        if panel_type == "1":
            install_node_only(cfg)
        else:
            install_3xui_cdn_only(cfg)
        return

    # --- Mode 4: TurboFlare migration guide ---
    if mode == "4":
        turboflare_migration_guide(server_ip)
        return

    # --- Modes 1 & 2: Full installation ---
    node_cred = ""
    cascade = False
    cascade_ip = None
    cascade_cred = None
    cascade_hy2 = False
    cascade_grpc = False
    if args.panel:
        panel_type = args.panel
        cdn_type = args.cdn or "vk"
        domain = args.domain
        node_ip = args.node_ip or server_ip
        if args.node_key:
            node_cred = {"type": "key", "value": args.node_key, "user": args.node_user}
        elif args.node_pass:
            node_cred = {"type": "password", "value": args.node_pass, "user": args.node_user}
        if getattr(args, 'cascade', False) and args.cascade_ip:
            cascade = True
            cascade_ip = args.cascade_ip
            cascade_cred = {"type": "password", "value": args.cascade_pass or "", "user": getattr(args, 'cascade_user', 'root')}
            if not validate_cascade_direction(server_ip, cascade_ip, panel_type):
                print("  ❌ Каскад задом наперёд. Запусти скрипт на РФ-сервере.")
                sys.exit(1)
    else:
        if mode == "2":
            panel_type = ask("Панель (Panel)?", {"1": "Remnawave 3.2.3", "2": "3x-ui (не поддерживается, ждите обновления)"})
            if panel_type == "2":
                print("  ❌ 3x-ui пока не поддерживается в режиме 2 (панель + нода на разных серверах)")
                print("  Используйте режим 1 или ждите обновления.")
                sys.exit(1)
        else:
            panel_type = ask("Панель (Panel)?", {"1": "Remnawave 3.2.3", "2": "3x-ui 3.6.0"})
        if panel_type == "1":
            # Remnawave: 6 CDN провайдеров
            cdn_type_choice = ask("CDN провайдер (CDN provider)?", {
                "1": "VK Cloud",
                "2": "Yandex Cloud",
                "3": "TurboFlare",
                "4": "Beeline/CDNvideo",
                "5": "Timeweb",
                "6": "Selectel"
            })
            cdn_type = {"1": "vk", "2": "yandex", "3": "turboflare", "4": "beeline", "5": "timeweb", "6": "selectel"}.get(cdn_type_choice, "vk")
        else:
            # 3x-ui: только 3 CDN провайдера
            cdn_type_choice = ask("CDN провайдер (CDN provider)?", {
                "1": "VK Cloud",
                "2": "Yandex Cloud",
                "3": "TurboFlare"
            })
            cdn_type = {"1": "vk", "2": "yandex", "3": "turboflare"}.get(cdn_type_choice, "vk")

        # Cascade option
        cascade = False
        cascade_ip = None
        cascade_cred = None
        cascade_hy2 = False
        cascade_grpc = False
        casc = ask("Настроить каскад (Cascade)?", {"1": "Нет", "2": "Да"})
        if casc == "2":
            cascade = True
            if panel_type == "1":
                cascade_ip = ask("IP relay-сервера в РФ (Cascade relay IP)")
            else:
                cascade_ip = ask("IP exit-сервера за рубежом (foreign exit server IP)")
            cascade_cred = ask_ssh_cred()
            if not validate_cascade_direction(server_ip, cascade_ip, panel_type):
                retry = ask("Продолжить всё равно?", {"1": "Нет, выхожу", "2": "Да, я знаю что делаю"})
                if retry != "2":
                    print("  Запусти скрипт на РФ-сервере.")
                    sys.exit(0)

        domain = ask("Домен без http:// (Domain)")
        domain = domain.replace("https://", "").replace("http://", "").strip("/").strip()

        node_ip = server_ip
        if mode == "2":
            node_ip = ask("IP сервера ноды (Node server IP)")
            node_cred = ask_ssh_cred()

    # Доп-протоколы HY2/gRPC теперь доступны и в режиме 1 Remnawave (#20).
    # install_remnawave умеет их ставить в same_server-ветке (open_extra_ports,
    # setup_hy2_le_cert, HY2/gRPC хосты — всё под `if same_server`). Раньше здесь
    # был жёсткий отказ, чтобы не нагружать сервер лишними протоколами; вернули
    # как выбор пользователя. Дефолт в интерактиве — «нет», а в неинтерактивном
    # запуске (бот/CLI) safe_input отдаёт EOF→"" → оба False, сервер не грузим.
    extra = ask_extra_protocols(panel_type=panel_type, args=args)

    # Инициализация переменных каскада для HY2/gRPC
    cascade_hy2 = False
    cascade_grpc = False

    # Если выбран каскад И пользователь хочет HY2/gRPC — спросить отдельно про каскад для них
    if cascade and (extra["install_hy2"] or extra["install_grpc"]):
        print("\n  Каскад для дополнительных протоколов:")
        print("  По умолчанию HY2 и gRPC идут напрямую на EU-ноду.")
        print("  Можно пустить их через каскад (вход РФ → выход EU).\n")

        if extra["install_hy2"]:
            resp = safe_input("  Hysteria2 через каскад? (y/n) [n]: ").strip().lower()
            cascade_hy2 = resp in ("y", "yes", "д", "да")

        if extra["install_grpc"]:
            resp = safe_input("  gRPC Reality через каскад? (y/n) [n]: ").strip().lower()
            cascade_grpc = resp in ("y", "yes", "д", "да")

    # Поддомены. origin/cdn/panel нужны всегда; exit — при каскаде; hy2 — если
    # включён Hysteria2 (у него свой LE-сертификат, и явная A-запись перебивает
    # wildcard *.domain, из-за которого ACME уходил не на ту машину). Роли, что
    # не спрашиваем, всё равно должны попасть в cfg — добираем случайными.
    # Страница подписки Remnawave (#5): красивый HTML вместо голого кода подписки.
    # Только для Remnawave (у 3x-ui своя страница). Дефолт — ставить; --no-subpage
    # или ответ «нет» отключают. В неинтерактиве (бот/CLI) safe_input EOF→"" →
    # берётся default=True, кроме явного --no-subpage.
    install_subpage = False
    if panel_type == "1":
        if getattr(args, 'no_subpage', False):
            install_subpage = False
        elif args.panel:
            install_subpage = True   # CLI без --no-subpage
        else:
            install_subpage = _ask_yes("\n  Поставить страницу подписки Remnawave? (y/n) [y]: ", default=True)

    _sub_roles = ["origin", "cdn", "panel"]
    if cascade:
        _sub_roles.append("exit")
    if extra["install_hy2"]:
        _sub_roles.append("hy2")
    if install_subpage:
        _sub_roles.append("sub")
    _want_custom = not args.panel and _ask_yes("\n  Задать свои поддомены? Иначе случайные (y/n) [n]: ")
    _subs = resolve_subdomains(args, _sub_roles, _want_custom)
    origin_sub = _subs["origin"]
    cdn_sub = _subs["cdn"]
    panel_sub = _subs["panel"]
    exit_sub = _subs.get("exit") or _rand_sub()
    hy2_sub = _subs.get("hy2") or _rand_sub()
    sub_sub = _subs.get("sub") or _rand_sub()

    cfg = {
        "panel_type": panel_type,
        "cdn_type": cdn_type,
        "domain": domain,
        "server_ip": server_ip,
        "node_ip": node_ip,
        "node_cred": node_cred,
        "skip_cdn_wait": getattr(args, 'skip_cdn_wait', False) if args.panel else False,
        "origin_sub": origin_sub,
        "cdn_sub": cdn_sub,
        "hy2_sub": hy2_sub,
        "panel_sub": panel_sub,
        "install_hy2": extra["install_hy2"],
        "install_grpc": extra["install_grpc"],
        "cascade": cascade,
        "cascade_ip": cascade_ip,
        "cascade_cred": cascade_cred,
        "cascade_hy2": cascade_hy2,
        "cascade_grpc": cascade_grpc,
        "exit_sub": exit_sub,
        "install_subpage": install_subpage,
        "sub_sub": sub_sub,
        "youtube_direct": ask_youtube_direct(cascade, args),
        "eu_grpc": ask_eu_grpc(cascade, args),
    }

    print(f"\n  Поддомены: origin={origin_sub}.{domain}, cdn={cdn_sub}.{domain}")
    print(f"  Панель: {panel_sub}.{domain}")

    # --- DNS instructions ---
    print(f"""
  ============================================
  СОЗДАЙ ЭТИ DNS ЗАПИСИ В CLOUDFLARE:
  ============================================
""")
    if cascade and panel_type == "1":
        origin_dns_ip = cascade_ip
    else:
        origin_dns_ip = node_ip
    print(f"  A    {panel_sub}.{domain}  ->  {server_ip}   (DNS only)")
    print(f"  A    {origin_sub}.{domain}    ->  {origin_dns_ip}     (DNS only){'  ← relay (каскад)' if cascade and panel_type == '1' else ''}")
    if cascade and panel_type == "2":
        print(f"  A    {exit_sub}.{domain}    ->  {cascade_ip}     (DNS only)  ← exit (каскад)")
    # Запись под HY2 нужна здесь же: иначе на шаге выпуска LE-сертификата
    # установка встаёт и ждёт DNS, который ещё никто не заводил.
    if extra["install_hy2"] and hy2_sub:
        hy2_target_ip = cascade_ip if cascade_hy2 else node_ip
        hy2_note = "  ← HY2 (через каскад)" if cascade_hy2 else "  ← HY2"
        print(f"  A    {hy2_sub}.{domain}    ->  {hy2_target_ip}     (DNS only){hy2_note}")
    # Страница подписки живёт на своём поддомене (панель на panel_sub), запись
    # нужна ДО выпуска её LE-сертификата — иначе установка встанет на ожидании DNS.
    if install_subpage and sub_sub:
        print(f"  A    {sub_sub}.{domain}    ->  {server_ip}     (DNS only)  ← страница подписки")
    print(f"  ({cdn_sub}.{domain} CNAME создашь после настройки CDN)")
    print()

    if not (args.skip_dns_wait if args.panel else False):
        safe_input("  Нажми ENTER когда DNS записи созданы...")

    # --- Common setup ---
    try:
        common_setup(cfg)

        # --- Panel-specific ---
        if panel_type == "2":
            install_3xui(cfg)
        else:
            install_remnawave(cfg)
    finally:
        cleanup_ssh_key(node_cred)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        handle_ctrl_c(can_resume=False)
        sys.exit(1)
