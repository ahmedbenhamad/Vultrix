#!/usr/bin/env python3
"""Emulates the vsftpd 2.3.4 backdoor (CVE-2011-2523) for authorized lab use.

Behavior faithful to what the Metasploit module ``exploit/unix/ftp/
vsftpd_234_backdoor`` probes for:

1. FTP control on :21 replies with ``220 (vsFTPd 2.3.4)``.
2. When a client sends ``USER <name>:)`` (any user containing ``:)``), the
   server silently spawns a root shell bound to :6200 and hangs the FTP
   session — the classic smiley trigger.
3. :6200 accepts one TCP client, hands them a ``/bin/sh``, and exits.

⚠ Lab only. Never expose to a real network.
"""
import os
import socket
import subprocess  # nosec B404 - intentional lab-only shell binding
import threading


def _shell_listener(port: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))  # nosec B104
    srv.listen(1)
    conn, _ = srv.accept()
    srv.close()
    # Hand the socket to /bin/sh — exactly what the real backdoor did.
    for fd in (0, 1, 2):
        os.dup2(conn.fileno(), fd)
    subprocess.call(["/bin/sh"])  # nosec B603 B607


_backdoor_fired = threading.Lock()


def _trigger_backdoor() -> None:
    # First smiley wins; subsequent hits are ignored so the port stays bound.
    if _backdoor_fired.acquire(blocking=False):
        threading.Thread(target=_shell_listener, args=(6200,), daemon=False).start()


def _handle_ftp(conn: socket.socket) -> None:
    try:
        conn.sendall(b"220 (vsFTPd 2.3.4)\r\n")
        f = conn.makefile("rwb")
        while True:
            line = f.readline()
            if not line:
                break
            cmd = line.decode("latin-1", errors="replace").rstrip("\r\n")
            up = cmd.upper()
            if up.startswith("USER "):
                username = cmd[5:]
                if ":)" in username:
                    _trigger_backdoor()
                    # Real backdoor hangs here — no reply, no close.
                    while conn.recv(4096):
                        pass
                    return
                conn.sendall(b"331 Please specify the password.\r\n")
            elif up.startswith("PASS "):
                conn.sendall(b"530 Login incorrect.\r\n")
            elif up.startswith("QUIT"):
                conn.sendall(b"221 Goodbye.\r\n")
                return
            else:
                conn.sendall(b"500 Unknown command.\r\n")
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 21))  # nosec B104
    srv.listen(8)
    print("[vsftpd-2.3.4-backdoor] listening on :21 (:6200 opens on smiley trigger)")
    while True:
        conn, addr = srv.accept()
        print(f"[vsftpd-2.3.4-backdoor] connection from {addr[0]}:{addr[1]}")
        threading.Thread(target=_handle_ftp, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
