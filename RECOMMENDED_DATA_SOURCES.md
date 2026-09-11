# Recommended RAG Data Sources

This document contains a curated list of high-quality, open-source repositories perfectly suited for enriching your Pentest RAG system. 

To ingest any of these, simply copy the `git clone` command, run it inside your `data/` directory, and then execute `python3 src/ingest.py`.

---

## 1. Pentesting Techniques & Playbooks
These repositories contain markdown files full of specific commands, methodologies, and bypasses. They are the **best** assets you can feed your RAG.

* **PayloadAllTheThings**
  * *Description*: The holy grail for web application security. Contains thousands of payload examples and bypass techniques.
  * *Command*: `git clone https://github.com/swisskyrepo/PayloadsAllTheThings.git`
* **HackTricks**
  * *Description*: Enormous cybersecurity encyclopedia covering privilege escalation, AD attacks, and port-specific hacking.
  * *Command*: `git clone https://github.com/carlospolop/hacktricks.git`
* **HighOn.Coffee Cheat Sheets**
  * *Description*: Detailed cheat sheets for tools like Nmap, reverse shells, etc.
  * *Command*: `git clone https://github.com/HighOnCoffee/highon.coffee.git`

## 2. Active Directory & Advanced Red Teaming
* **Atomic Red Team**
  * *Description*: Thousands of `.md` files detailing exact terminal/PowerShell commands to test or execute specific MITRE ATT&CK techniques.
  * *Command*: `git clone https://github.com/redcanaryco/atomic-red-team.git`
* **Red Teaming Tactics and Techniques (ired.team)**
  * *Description*: Extensive notes on malware development, code injection, and AD exploitation.
  * *Command*: `git clone https://github.com/mantvydasb/RedTeaming-Tactics-and-Techniques.git`
* **LOLBAS (Living Off The Land Binaries)**
  * *Description*: Details on how to use built-in Windows binaries to bypass defenses.
  * *Command*: `git clone https://github.com/LOLBAS-Project/LOLBAS.git`

## 3. Cloud Hacking (AWS, Azure, GCP, K8s)
* **HackTricks Cloud**
  * *Description*: The cloud-specific version of HackTricks.
  * *Command*: `git clone https://github.com/carlospolop/hacktricks-cloud.git`

## 4. Huge Collections of CTF & Bug Bounty Writeups
* **Daffainfo CTF Writeups**
  * *Description*: Over 500 CTF walkthroughs and scripts.
  * *Command*: `git clone https://github.com/daffainfo/ctf-writeup.git`
* **CTFs Repositories (0xdf)**
  * *Description*: The raw markdown files from 0xdf's legendary HackTheBox walkthrough blog.
  * *Command*: `git clone https://github.com/0xdf/0xdf.github.io.git`
* **Awesome Bugbounty Writeups**
  * *Description*: A massive curated list of bug bounty reports and methodologies.
  * *Command*: `git clone https://github.com/devanshbatham/Awesome-Bugbounty-Writeups.git`
* **EdOverflow's BugBounty-CheatSheet**
  * *Description*: Definitions of exact payloads and edge cases for specific web vulnerabilities.
  * *Command*: `git clone https://github.com/EdOverflow/bugbounty-cheatsheet.git`

## 5. Vulnerability Databases
* **Exploit Database (Exploit-DB)**
  * *Description*: Thousands of exploits in `.py`, `.c`, and `.txt` files with `.csv` database mapping.
  * *Command*: `git clone https://github.com/offensive-security/exploitdb.git`

## 6. Threat Intelligence & Academic Research
* **MITRE Cyber Threat Intelligence (CTI)**
  * *Description*: Massive repository of JSON-based threat intelligence mapping APTs, malware, and specific campaign strategies. Useful if you want the RAG to recognize the signatures of state-sponsored groups.
  * *Command*: `git clone https://github.com/mitre/cti.git`
* **VX Underground Malware Source & Research Papers**
  * *Description*: Deep-dive academic papers and reverse engineering studies regarding real-world malware. It's an immense library of PDFs.
  * *Command*: `git clone https://github.com/vxunderground/MalwareSourceCode.git`
* **APT Notes**
  * *Description*: Hundreds of publicly released cyber threat intelligence reports organized by year, mostly in PDF format.
  * *Command*: `git clone https://github.com/aptnotes/data.git`

## 7. Books, Defense, and Methodologies
* **OWASP Web Security Testing Guide (WSTG)**
  * *Description*: The definitive book and methodology guide for testing the security of web applications.
  * *Command*: `git clone https://github.com/OWASP/wstg.git`
* **OWASP Mobile Security Testing Guide (MASTG)**
  * *Description*: The definitive book and guide for testing mobile (iOS/Android) application security.
  * *Command*: `git clone https://github.com/OWASP/MASTG.git`
* **Awesome Pentest (Reference Links and Cheat Sheets)**
  * *Description*: A large curated list of books, tools, and methodologies. While many are links, the localized resources and summaries provide excellent contextual data.
  * *Command*: `git clone https://github.com/enaqx/awesome-pentest.git`

---

## ⚠️ CRITICAL WARNING FOR RAG INGESTION ⚠️
Do **NOT** ingest repositories that are essentially just wordlists or dictionary files (like `danielmiessler/SecLists`). 

If you use your universal ingest script on a directory containing a 14-million-line `.txt` file of rockyou passwords or XSS fuzzing strings:
1. It will take days to vectorize.
2. It will bloat your ChromaDB to gigabytes of junk.
3. It will completely pollute the AI's search results, making it spew random text passwords instead of answering your questions logically. 

**Rule of thumb**: Only feed the RAG files that contain English/French *explanations*, *concepts*, or *structured commands*. Do not feed it raw fuzzing wordlists!
