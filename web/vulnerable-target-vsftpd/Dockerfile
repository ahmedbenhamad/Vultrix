# ─────────────────────────────────────────────────────────────────────────────
# Purpose-built vulnerable target: vsftpd 2.3.4 smiley-face backdoor
# (CVE-2011-2523).
#
# Metasploit validates it deterministically:
#     msf > use exploit/unix/ftp/vsftpd_234_backdoor
#     msf > set RHOSTS <host>;  set RPORT 21;  run     # -> root shell on :6200
#
# We emulate the exact protocol behavior the Metasploit module probes for
# (banner "220 (vsFTPd 2.3.4)" + `USER anything:)` triggers a shell bind on
# :6200) rather than shipping the real backdoored binary — smaller image,
# faster boot, and no need to pull period-correct build tools.
#
# ⚠ Lab only — this is intentionally insecure. Do not expose to a real network.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# /bin/sh is present in the base image; that's what the backdoor hands out.
COPY vsftpd_234_backdoor.py /opt/vsftpd_234_backdoor.py

EXPOSE 21 6200

CMD ["python3", "-u", "/opt/vsftpd_234_backdoor.py"]
