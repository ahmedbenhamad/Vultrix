import os
import re
import sys
import argparse
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCRAPED_DIR = DATA_DIR / "scraped_writeups"

def extract_links_from_md(file_path):
    """Extracts all http/https URLs from a markdown file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Regex to find standard Markdown links [text](http...)
    links = re.findall(r'\[.*?\]\((https?://[^\s\)]+)\)', content)
    # Also find raw URLs just in case
    raw_urls = re.findall(r'(https?://[^\s\>\)\]]+)', content)
    
    return list(set(links + raw_urls))

def scrape_url(url, output_path):
    """Fetches a URL, extracts readable main text, and saves it while ignoring noise."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove core layout and noisy tags
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                element.decompose()
                
            # Remove elements with class or ID names indicating comments, sidebars, or ads
            for noise in soup.find_all(class_=re.compile(r'(sidebar|comment|widget|menu|popup|ad-|social|related)', re.I)):
                noise.decompose()
            for noise in soup.find_all(id=re.compile(r'(sidebar|comment|widget|menu|popup|ad-|related)', re.I)):
                noise.decompose()
            
            # Prefer <article> or <main>. If neither exists, use an element with id="content", etc.
            main_content = soup.find('article') or soup.find('main') or soup.find(id=re.compile(r'(content|main|post)', re.I))
            if not main_content:
                main_content = soup.body if soup.body else soup
            
            # Extract plain text
            text = main_content.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text) # Consolidate blank lines
            
            # Ensure it has enough textual content to be worth saving
            if len(text) > 200:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"Source URL: {url}\n\n{text}")
                return True
    except Exception as e:
        print(f"Failed to scrape {url}: {str(e)[:50]}")
    return False

def main():
    parser = argparse.ArgumentParser(description="Scraper for awesome lists and bug bounty writeups.")
    parser.add_argument("target", nargs="?", default=str(DATA_DIR), 
                        help="A directory containing markdown files, a specific .md file, or a direct URL to scrape. Defaults to data/")
    args = parser.parse_args()

    if not SCRAPED_DIR.exists():
        SCRAPED_DIR.mkdir(parents=True)

    all_links = set()
    target_str = args.target

    if target_str.startswith("http://") or target_str.startswith("https://"):
        print(f"Target is a single URL: {target_str}")
        all_links.add(target_str)
    else:
        target_path = Path(target_str)
        if target_path.is_file() and target_path.suffix.lower() == '.md':
            print(f"Extracting links from file: {target_path}")
            all_links.update(extract_links_from_md(target_path))
        elif target_path.is_dir():
            print(f"Searching for Markdown files in {target_path} to extract links...")
            md_files = list(target_path.glob("**/*.md"))
            for md_file in md_files:
                all_links.update(extract_links_from_md(md_file))
        else:
            print(f"Error: Target '{target_str}' is not a valid markdown file, directory, or URL.")
            sys.exit(1)
            
    if not all_links:
        print("No valid links found to process.")
        return
        
    print(f"Found {len(all_links)} total links to process!")
    
    success_count = 0
    for i, url in enumerate(list(all_links)):
        # Skip obvious non-article links
        if any(x in url for x in ['.png', '.jpg', '.zip', '.pdf', 'twitter.com', 'youtube.com']):
            continue
            
        print(f"[{i+1}/{len(all_links)}] Scraping {url}...")
        
        domain = urlparse(url).netloc.replace("www.", "")
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', url.split('/')[-1])
        if not safe_name:
            safe_name = "index"
            
        filename = f"{domain}_{safe_name}.txt"
        output_path = SCRAPED_DIR / filename
        
        if output_path.exists():
            continue # Already scraped
            
        if scrape_url(url, output_path):
            success_count += 1
            
    print(f"\nDone! Successfully scraped text from {success_count} external links.")
    print(f"Run your 'python3 src/ingest.py' script now to index them!")

if __name__ == "__main__":
    main()
