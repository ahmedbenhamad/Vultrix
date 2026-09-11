# Vulnerable target — end-to-end validation for Strix + Metasploit

A small, purpose-built **distccd** container (CVE-2004-2687) so you can prove the
whole chain works: **Strix (agent) → exploit_research (RAG + Metasploit) → real
exploit → finding in the console.**

Built from `debian:bullseye-slim` + `distcc` — no giant image pulls, boots in
seconds, and maps to a deterministic Metasploit module.

> ⚠ **Lab only.** Intentionally insecure. Run on an isolated host/private network.

## 1. Build & launch

```bash
cd web/vulnerable-target
docker compose up -d --build
```

Verify it's up (distccd 3.3.5 listening on `0.0.0.0:3632`, accepting jobs from any host):

```bash
docker logs strix-vuln-target        # -> "listening on 0.0.0.0:3632", "allowing up to N active jobs"
```

## 2. The vulnerability

| Port | Service       | Metasploit module                 | CVE           | Result            |
|------|---------------|-----------------------------------|---------------|-------------------|
| 3632 | distccd 3.3.5 | `exploit/unix/misc/distcc_exec`   | CVE-2004-2687 | remote command exec |

`distccd` here runs with `--allow 0.0.0.0/0`, so it accepts compile jobs from any
host and executes the supplied "compiler" — unauthenticated RCE. Validate manually:

```
msf6 > use exploit/unix/misc/distcc_exec
msf6 > set RHOSTS <host-ip>
msf6 > set RPORT 3632
msf6 > run                    # -> command execution / session
```

## 3. Point a Strix assessment at it

- **Target:** `host.docker.internal` — the Strix sandbox is created with
  `extra_hosts host.docker.internal:host-gateway`, so it reaches the host, and the
  daemon is published on host port **3632**.
- In the console: **Assessments → New**, target = `host.docker.internal`, mode = **deep**.
- During exploitation, `exploit_research` should identify distcc (CVE-2004-2687)
  and hand off to the `distcc_exec` Metasploit module.

## 4. Prerequisite — a capable LLM

The agents drive the tools via the model in `web/backend/.env` (`STRIX_LLM`). A
weak/free model may reason but fail to complete exploitation; a stronger model
(e.g. a paid Claude/GPT on your OpenRouter key) drives the agents far more
reliably. With the live-console fix, progress (agents/tools/tokens/findings)
streams in real time regardless.

## 5. Tear down

```bash
docker compose down          # stop + remove
```
