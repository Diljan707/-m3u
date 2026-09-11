import concurrent.futures
import json
import re
import urllib.request
import time
import sys

# Direct URL input instead of local file
PLAYLIST_URL = "https://game.playindia.fun/Jtv/RiYlIZ/Playlist.m3u"
OUTPUT_FILE = "final_playlist.m3u"
USER_AGENT = "Denver1769"

def fetch_playlist_content():
    print("Playlist download ho rahi hai...")
    req = urllib.request.Request(
        PLAYLIST_URL,
        headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        print(f"Error: Playlist download nahi ho saki! {e}")
        return None

def fetch_keys(license_url, retries=3):
    req = urllib.request.Request(
        license_url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://game.playindia.fun/",
        },
    )
    
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                raw_data = response.read().decode()
                data = json.loads(raw_data)
                
                if "base64" in data and "keys" in data["base64"]:
                    kodi_key_format = {"keys": data["base64"]["keys"]}
                    return license_url, json.dumps(kodi_key_format)
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
        sys.exit(1)  # GitHub Actions nu fail status den layi je download na hove

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
            
            # GitHub logs vich \r di jagah har 10 items baad print hovega taaki logs saaf rehn
            if completed % 10 == 0 or completed == len(matches):
                print(f"Progress: {completed}/{len(matches)} processed")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nKaam complete! Nayi playlist '{OUTPUT_FILE}' vich save ho gayi hai.")

if __name__ == "__main__":
    process_playlist()
