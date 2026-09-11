import os
import sys
import subprocess
from pathlib import Path
from src.utils import ensure_qdrant_running

# ANSI Colors for terminal formatting
C = "\033[96m"
G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
RESET = "\033[0m"

BASE_DIR = Path(__file__).resolve().parent

def clear_screen():
    # Clear terminal based on OS
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print(f"{C}")
    print(" █▀▀█ █▀▀ █▀▀▄ ▀▀█▀▀ █▀▀ █▀▀ ▀▀█▀▀   █▀▀█ █▀▀█ █▀▀▀ ")
    print(" █░░█ █▀▀ █░░█ ░░█░░ █▀▀ ▀▀█ ░░█░░   █▄▄▀ █▄▄█ █░▀█ ")
    print(" █▀▀▀ ▀▀▀ ▀░░▀ ░░▀░░ ▀▀▀ ▀▀▀ ░░▀░░   ▀░▀▀ ▀░░▀ ▀▀▀▀ ")
    print(f"{Y}         Omnivorous AI Knowledge Base Manager{RESET}\n")

def run_command(cmd_list):
    print(f"\n{G}[*] Running: {' '.join(cmd_list)}{RESET}\n")
    try:
        subprocess.run(cmd_list, check=True)
    except subprocess.CalledProcessError:
        print(f"\n{R}[!] Process encountered an error or was interrupted.{RESET}")
    except KeyboardInterrupt:
        print(f"\n{Y}[!] Interrupted by user.{RESET}")
    input(f"\n{C}Press Enter to return to menu...{RESET}")

def change_model():
    print_header()
    env_path = BASE_DIR / ".env"
    
    # Check if .env exists, fallback to .env.example
    if not env_path.exists():
        if (BASE_DIR / ".env.example").exists():
            print(f"{Y}[*] .env file not found. Creating one from .env.example...{RESET}")
            content = (BASE_DIR / ".env.example").read_text()
            env_path.write_text(content)
        else:
            print(f"{R}[!] No .env or .env.example found! Your configuration is broken.{RESET}")
            input("Press Enter to return...")
            return

    print(f"{C}--- Change AI Model Configuration ---{RESET}")
    print("1) Ollama (Local AI - No API keys)")
    print("2) OpenRouter (Cloud AI - Requires API key)")
    print("0) Cancel")
    
    choice = input(f"\n{Y}Select Provider > {RESET}")
    if choice == '1':
        provider = "ollama"
        model = input(f"Enter Ollama model name (e.g., {C}llama3{RESET}, {C}mistral{RESET}): ")
    elif choice == '2':
        provider = "openrouter"
        model = input(f"Enter OpenRouter model name (e.g., {C}anthropic/claude-3-opus{RESET}): ")
    else:
        return
        
    if not model.strip():
        print(f"{R}[!] Model name cannot be empty.{RESET}")
        input("Press Enter to return...")
        return

    # Update .env purely via string slicing to retain comments
    lines = env_path.read_text().splitlines()
    new_lines = []
    
    prov_found = False
    mod_found = False
    
    for line in lines:
        if line.startswith("LLM_PROVIDER="):
            new_lines.append(f"LLM_PROVIDER={provider}")
            prov_found = True
        elif line.startswith("LLM_MODEL="):
            new_lines.append(f"LLM_MODEL={model}")
            mod_found = True
        else:
            new_lines.append(line)
            
    if not prov_found:
        new_lines.append(f"LLM_PROVIDER={provider}")
    if not mod_found:
        new_lines.append(f"LLM_MODEL={model}")
        
    env_path.write_text("\n".join(new_lines) + "\n")
    print(f"\n{G}[+] Successfully updated {env_path.name}!{RESET}")
    print(f"    - Provider: {Y}{provider}{RESET}")
    print(f"    - Model:    {Y}{model}{RESET}")
    input(f"\n{C}Press Enter to return to menu...{RESET}")

def main():
    # Automate Qdrant lifecycle on startup
    ensure_qdrant_running()
    
    while True:
        print_header()
        print("Please choose an action:")
        print(f" {G}1){RESET} 🧠 Query the RAG      {C}(Ask a Pentesting Question){RESET}")
        print(f" {G}2){RESET} 🔍 Fast-Path Retrieve {C}(Quick knowledge check - no LLM){RESET}")
        print(f" {G}3){RESET} 🚀 Launch API Server  {C}(Start background server for Strix){RESET}")
        print(f" {G}4){RESET} 🕸️ Scrape links       {C}(Gather data from web links){RESET}")
        print(f" {G}5){RESET} 🧹 Clean Data         {C}(Prepare data & remove junks){RESET}")
        print(f" {G}6){RESET} 📚 Feed the RAG       {C}(Ingest the data/ folder){RESET}")
        print(f" {G}7){RESET} ⚙️ Change AI Model    {C}(Switch between Ollama/OpenRouter){RESET}")
        print(f" {G}8){RESET} 🐳 Qdrant Status      {C}(Check/Start Vector Database){RESET}")
        print(f" {R}0){RESET} Exit\n")

        choice = input(f"{Y}Your choice > {RESET}")

        if choice == '1':
            q = input(f"\n{C}Enter your pentesting question:{RESET}\n> ")
            if q.strip():
                run_command([sys.executable, "main.py", "--query", q])
        elif choice == '2':
            q = input(f"\n{C}Enter search terms for retrieval:{RESET}\n> ")
            if q.strip():
                # We use curl here because /retrieve is only an API endpoint, not a CLI flag in main.py
                print(f"\n{Y}Performing fast-path retrieval for: {q}{RESET}")
                run_command(["curl", "-X", "POST", "http://localhost:8000/retrieve", "-H", "Content-Type: application/json", "-d", f'{{"query": "{q}"}}'])
        elif choice == '3':
            print(f"\n{Y}Starting API server on port 8000... Press Ctrl+C to stop it.{RESET}")
            run_command([sys.executable, "main.py", "--serve"])
        elif choice == '4':
            print(f"\n{Y}Note:{RESET} By default, this searches the whole data/ folder.")
            run_command([sys.executable, "scripts/scrape_awesome_links.py"])
        elif choice == '5':
            run_command([sys.executable, "scripts/clean_data.py"])
        elif choice == '6':
            run_command([sys.executable, "main.py", "--ingest"])
        elif choice == '7':
            change_model()
        elif choice == '8':
            print(f"\n{Y}[*] Checking Qdrant status...{RESET}")
            ensure_qdrant_running(force=True)
            input(f"\n{C}Press Enter to return to menu...{RESET}")
        elif choice == '0':
            clear_screen()
            print(f"\n{G}Script Runner exited. Happy Hacking!{RESET}\n")
            break
        else:
            print(f"\n{R}[!] Invalid choice.{RESET}")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print(f"\n{G}Script Runner exited. Happy Hacking!{RESET}\n")
