# ─────────────────────────────────────────────────────────────────────────────
# Purpose-built vulnerable target: distccd with an open --allow (CVE-2004-2687).
#
# distcc's daemon, when it accepts jobs from arbitrary hosts, will execute the
# "compiler" command line it is handed → unauthenticated remote command
# execution. Metasploit validates it deterministically:
#     msf > use exploit/unix/misc/distcc_exec
#     msf > set RHOSTS <host>;  set RPORT 3632;  run     # -> command execution
#
# ⚠ Lab only — this is intentionally insecure. Do not expose to a real network.
# ─────────────────────────────────────────────────────────────────────────────
FROM debian:bullseye-slim

# distccd needs a real compiler on PATH to dispatch jobs to (that's what gets abused).
RUN apt-get update \
    && apt-get install -y --no-install-recommends distcc gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Run the daemon unprivileged.
RUN useradd -m -u 1001 distccuser
USER distccuser

EXPOSE 3632

# The vulnerable configuration: accept jobs from ANY host (--allow 0.0.0.0/0),
# listen on all interfaces, stay in the foreground for Docker.
CMD ["distccd", "--daemon", "--no-detach", \
     "--allow", "0.0.0.0/0", \
     "--listen", "0.0.0.0", \
     "--port", "3632", \
     "--log-stderr", "--log-level", "info"]
