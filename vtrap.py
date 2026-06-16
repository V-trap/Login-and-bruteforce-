#!/usr/bin/env python3
"""
VTRAP — Educational network login tester — for authorized use only.
Interface: service://host, -l/-L, -p/-P, -t threads, -f stop on success.

Supported services: ssh, ftp, http-basic, http-form

Install dependencies:
    pip install paramiko requests
"""

import argparse
import ftplib
import queue
import socket
import sys
import threading
import time
from datetime import datetime

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ── terminal colours ──────────────────────────────────────────────────────────

class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    YELLOW = '\033[93m'
    BLUE   = '\033[94m'
    CYAN   = '\033[96m'
    BOLD   = '\033[1m'
    RESET  = '\033[0m'


# ── shared state ──────────────────────────────────────────────────────────────

found       = []          # [(user, pass), ...]
attempts    = 0
stop_flag   = threading.Event()
lock        = threading.Lock()


# ── logging ───────────────────────────────────────────────────────────────────

def ts():
    return datetime.now().strftime("%H:%M:%S")

def log_success(msg): print(f"\n[{ts()}] {C.GREEN}[+]{C.RESET} {msg}")
def log_fail(msg):    print(f"[{ts()}] {C.RED}[-]{C.RESET} {msg}")
def log_info(msg):    print(f"[{ts()}] {C.BLUE}[*]{C.RESET} {msg}")
def log_warn(msg):    print(f"[{ts()}] {C.YELLOW}[!]{C.RESET} {msg}")


# ── protocol handlers ─────────────────────────────────────────────────────────

def try_ssh(host, port, user, passwd, timeout):
    if not PARAMIKO_AVAILABLE:
        sys.exit("paramiko not installed — run: pip install paramiko")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host, port=port,
            username=user, password=passwd,
            timeout=timeout,
            allow_agent=False, look_for_keys=False,
        )
        return True
    except paramiko.AuthenticationException:
        return False
    except (paramiko.SSHException, socket.error, EOFError):
        return None   # network error — caller will retry
    finally:
        try: client.close()
        except Exception: pass


def try_ftp(host, port, user, passwd, timeout):
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=timeout)
        ftp.login(user, passwd)
        ftp.quit()
        return True
    except ftplib.error_perm:
        return False
    except Exception:
        return None


def try_http_basic(host, port, user, passwd, path, ssl, timeout):
    if not REQUESTS_AVAILABLE:
        sys.exit("requests not installed — run: pip install requests")
    scheme = "https" if ssl else "http"
    url = f"{scheme}://{host}:{port}{path}"
    try:
        r = requests.get(url, auth=(user, passwd), timeout=timeout,
                         verify=False, allow_redirects=False)
        return r.status_code not in (401, 403)
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return False


def try_http_form(host, port, user, passwd, path, user_field, pass_field,
                  fail_string, ssl, timeout):
    if not REQUESTS_AVAILABLE:
        sys.exit("requests not installed — run: pip install requests")
    scheme = "https" if ssl else "http"
    url = f"{scheme}://{host}:{port}{path}"
    data = {user_field: user, pass_field: passwd}
    try:
        r = requests.post(url, data=data, timeout=timeout,
                          verify=False, allow_redirects=True)
        if fail_string:
            return fail_string not in r.text
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return False


# ── worker ────────────────────────────────────────────────────────────────────

def worker(cfg, q):
    global attempts

    while not stop_flag.is_set():
        try:
            user, passwd = q.get(timeout=1)
        except queue.Empty:
            break

        result = None
        for _ in range(3):                     # up to 3 retries on network error
            if stop_flag.is_set():
                break
            svc = cfg.service

            if svc == "ssh":
                result = try_ssh(cfg.host, cfg.port, user, passwd, cfg.timeout)
            elif svc == "ftp":
                result = try_ftp(cfg.host, cfg.port, user, passwd, cfg.timeout)
            elif svc == "http-basic":
                result = try_http_basic(cfg.host, cfg.port, user, passwd,
                                        cfg.path, cfg.ssl, cfg.timeout)
            elif svc == "http-form":
                result = try_http_form(cfg.host, cfg.port, user, passwd,
                                       cfg.path, cfg.user_field, cfg.pass_field,
                                       cfg.fail_string, cfg.ssl, cfg.timeout)

            if result is not None:
                break
            time.sleep(0.5)

        with lock:
            attempts += 1
            if result is True:
                found.append((user, passwd))
                log_success(f"VALID  {user}:{passwd}  @  {cfg.host}:{cfg.port}/{cfg.service}")
                if cfg.stop_on_success:
                    stop_flag.set()
            elif cfg.verbose:
                log_fail(f"{user}:{passwd}")

        q.task_done()


# ── helpers ───────────────────────────────────────────────────────────────────

DEFAULT_PORTS = {"ssh": 22, "ftp": 21, "http-basic": 80, "http-form": 80}
SUPPORTED     = list(DEFAULT_PORTS.keys())


def load(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        sys.exit(f"File not found: {path}")


def parse_target(raw):
    if "://" not in raw:
        sys.exit("Target must be  service://host[:port]  e.g. ssh://10.0.0.1")
    svc, host_part = raw.split("://", 1)
    svc = svc.lower()
    if svc not in SUPPORTED:
        sys.exit(f"Unknown service '{svc}'. Supported: {', '.join(SUPPORTED)}")
    if ":" in host_part:
        host, port = host_part.rsplit(":", 1)
        port = int(port)
    else:
        host = host_part
        port = DEFAULT_PORTS[svc]
    return svc, host, port


def banner():
    print(f"""
{C.CYAN}{C.BOLD}  ██╗   ██╗████████╗██████╗   █████╗ ██████╗ {C.RESET}
{C.CYAN}{C.BOLD}  ██║   ██║╚══██╔══╝██╔══██╗ ██╔══██╗██╔══██╗{C.RESET}
{C.CYAN}{C.BOLD}  ██║   ██║   ██║   ██████╔╝ ███████║██████╔╝{C.RESET}
{C.CYAN}{C.BOLD}  ╚██╗ ██╔╝   ██║   ██╔══██╗ ██╔══██║██╔═══╝ {C.RESET}
{C.CYAN}{C.BOLD}   ╚████╔╝    ██║   ██║  ██║ ██║  ██║██║     {C.RESET}
{C.CYAN}{C.BOLD}    ╚═══╝     ╚═╝   ╚═╝  ╚═╝ ╚═╝  ╚═╝╚═╝     {C.RESET}
{C.YELLOW}  Educational Network Login Tester{C.RESET}
{C.RED}  !! Only use on systems you own or have written permission to test !!{C.RESET}
""")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    banner()

    ap = argparse.ArgumentParser(
        description="VTRAP — Educational network login tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  SSH, single user, wordlist:
    python vtrap.py ssh://10.0.0.1  -l admin  -P rockyou.txt  -t 8

  FTP, user + pass wordlists:
    python vtrap.py ftp://10.0.0.1  -L users.txt  -P pass.txt

  HTTP Basic Auth:
    python vtrap.py http-basic://10.0.0.1  -l admin  -P pass.txt  --path /admin

  HTTP Login Form (stop on first hit, save results):
    python vtrap.py http-form://10.0.0.1  -l admin  -P pass.txt  \\
        --path /login  --user-field username  --pass-field password  \\
        --fail-string "Invalid credentials"  -f  -o results.txt
""",
    )

    ap.add_argument("target",
                    help="service://host[:port]  — ssh, ftp, http-basic, http-form")
    ap.add_argument("-l", dest="username",  help="Single username")
    ap.add_argument("-L", dest="userlist",  help="Username wordlist file")
    ap.add_argument("-p", dest="password",  help="Single password")
    ap.add_argument("-P", dest="passlist",  help="Password wordlist file")
    ap.add_argument("-t", dest="threads",   type=int, default=4,
                    help="Parallel threads (default: 4)")
    ap.add_argument("-s", dest="port_override", type=int,
                    help="Port override")
    ap.add_argument("--timeout", type=int, default=5,
                    help="Connection timeout in seconds (default: 5)")
    ap.add_argument("-f", dest="stop_on_success", action="store_true",
                    help="Stop after first valid credential found")
    ap.add_argument("-v", dest="verbose", action="store_true",
                    help="Show failed attempts")
    ap.add_argument("-o", dest="output",
                    help="Write found credentials to file")

    # HTTP-specific
    ap.add_argument("--path",       default="/",        help="URL path  (default: /)")
    ap.add_argument("--ssl",        action="store_true", help="Use HTTPS")
    ap.add_argument("--user-field", dest="user_field",  default="username",
                    help="Form field for username  (default: username)")
    ap.add_argument("--pass-field", dest="pass_field",  default="password",
                    help="Form field for password  (default: password)")
    ap.add_argument("--fail-string", dest="fail_string",
                    help="String in response that means login failed")

    cfg = ap.parse_args()

    # Parse target
    cfg.service, cfg.host, cfg.port = parse_target(cfg.target)
    if cfg.port_override:
        cfg.port = cfg.port_override

    # Build credential lists
    usernames = [cfg.username] if cfg.username else (
        load(cfg.userlist) if cfg.userlist else None)
    passwords = [cfg.password] if cfg.password else (
        load(cfg.passlist) if cfg.passlist else None)

    if not usernames:
        sys.exit("Provide -l <user> or -L <wordlist>")
    if not passwords:
        sys.exit("Provide -p <pass> or -P <wordlist>")

    # Fill queue
    q = queue.Queue()
    for u in usernames:
        for p in passwords:
            q.put((u, p))
    total = q.qsize()

    log_info(f"Target   : {cfg.service}://{cfg.host}:{cfg.port}")
    log_info(f"Users    : {len(usernames)}   Passwords: {len(passwords)}   "
             f"Combos: {total}")
    log_info(f"Threads  : {cfg.threads}   Timeout: {cfg.timeout}s")
    log_info("Starting...\n")

    t0 = time.time()
    threads = [
        threading.Thread(target=worker, args=(cfg, q), daemon=True)
        for _ in range(min(cfg.threads, total))
    ]
    for t in threads: t.start()

    try:
        while any(t.is_alive() for t in threads):
            with lock:
                done = total - q.qsize()
            elapsed = time.time() - t0
            rate    = done / elapsed if elapsed else 0
            eta     = q.qsize() / rate if rate else 0
            print(
                f"\r{C.CYAN}Progress:{C.RESET} {done}/{total}  "
                f"rate: {rate:.1f}/s  eta: {eta:.0f}s  "
                f"found: {C.GREEN}{len(found)}{C.RESET}   ",
                end="", flush=True,
            )
            time.sleep(0.4)
    except KeyboardInterrupt:
        log_warn("Interrupted — stopping threads...")
        stop_flag.set()

    for t in threads: t.join(timeout=2)

    elapsed = time.time() - t0
    print(f"\n\n{'─'*60}")
    log_info(f"Done in {elapsed:.1f}s | {attempts} attempts | {len(found)} found")

    if found:
        print(f"\n{C.GREEN}{C.BOLD}  ✓ Valid credentials:{C.RESET}")
        for u, p in found:
            print(f"    {C.GREEN}{u}:{p}{C.RESET}")
        if cfg.output:
            with open(cfg.output, "w") as f:
                for u, p in found:
                    f.write(f"{u}:{p}\n")
            log_info(f"Saved to {cfg.output}")
    else:
        log_warn("No valid credentials found.")


if __name__ == "__main__":
    main()
