import concurrent.futures
import json
import re
import time
import sys
import cloudscraper

PLAYLIST_URL = "https://game.playindia.fun/Jtv/RiYlIZ/Playlist.m3u"
OUTPUT_FILE = "final_playlist.m3u"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch_playlist_content():
    print("Playlist download ho rahi hai (Cloudscraper bypass te Header nal)...")
    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": USER_AGENT
    }
    try:
        response = scraper.get(PLAYLIST_URL, headers=headers, timeout=20)
        # Check je Cloudflare challenge page taan nahi aa gaya
        if "<html" in response.text.lower() and "challenge" in response.text.lower():
            print("Error: Cloudflare block kar riha hai!")
            return None
        return response.text
    except Exception as e:
        print(f"Error: Playlist download nahi ho saki! {e}")
        return None

def fetch_keys(license_url, retries=3):
    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://game.playindia.fun/",
    }
    
    for attempt in range(retries):
        try:
            response = scraper.get(license_url, headers=headers, timeout=15)
            data = response.json()
            if data:
                return license_url, json.dumps(data)
            else:
                return license_url, None
        except Exception as e:
            if attempt == retries - 1:
                return license_url, None
            time.sleep(1)
            
    return license_url, None

def process_playlist():
    content = fetch_playlist_content()
    if not content:
        sys.exit(1)

    # Cookies / Pipe format nu clean query parameter vich badlo
    content = re.sub(r'(%7Ccookie=|\|cookie=)(__hdnea__=[^&\s]+)(?:&User-Agent=[^\s]+)?', r'?\2', content)

    pattern = r"(#KODIPROP:inputstream.adaptive.license_key=)(https://[^\s]+)"
    matches = list(re.finditer(pattern, content))
    print(f"Total {len(matches)} channels mile ne. Safe speed (8 threads) te keys fetch ho rahiyan ne...")

    new_content = content

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {
            executor.submit(fetch_keys, match.group(2)): match.group(2)
            for match in matches
        }

        completed = 0
        for future in concurrent.futures.as_completed(future_to_url):
            license_url, keys_json = future.result()
            completed += 1
            if keys_json:
                prefix = "#KODIPROP:inputstream.adaptive.license_key="
                new_content = new_content.replace(prefix + license_url, prefix + keys_json)
            
            if completed % 10 == 0 or completed == len(matches):
                print(f"Progress: {completed}/{len(matches)} processed")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nKaam complete! Nayi playlist '{OUTPUT_FILE}' vich save ho gayi hai.")

if __name__ == "__main__":
    process_playlist()
