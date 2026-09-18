import os
import time
import threading
import cloudscraper
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 1. HEALTH CHECK SERVER FOR RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Vinted Monitor Active")

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_check, daemon=True).start()

# --- 2. CONFIGURATION ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1550604418112823318/-GczalwvRKujHA_6JwGSBba-3f3ceejYIUz-jQv9h4Z5NNgDLI7BG4iwqVROEYtbmCw-"
VINTED_URL = "https://www.vinted.fr/api/v2/catalog/items?price_to=50&currency=EUR&order=newest_first"

TARGET_BRANDS = [
    "ralph lauren", "polo ralph lauren",
    "louis vuitton",
    "nike",
    "burberry",
    "adidas"
]

def create_fresh_scraper():
    """Generates a browser session with realistic headers."""
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.vinted.fr/catalog",
        "Origin": "https://www.vinted.fr"
    })
    try:
        # Visit main page first to get session cookies
        scraper.get("https://www.vinted.fr", timeout=10)
    except Exception as e:
        print(f"Cookie fetch warning: {e}", flush=True)
    return scraper

seen_item_ids = set()

def send_discord_alert(title, price, brand, size, item_id, photo_url):
    item_url = f"https://www.vinted.fr/items/{item_id}"
    payload = {
        "username": "Vinted Deal Monitor",
        "avatar_url": "https://www.vinted.fr/favicon.ico",
        "embeds": [
            {
                "title": f"🔥 {title or 'New Listing Found!'}",
                "url": item_url,
                "color": 0x00A8A8,
                "description": f"**Price:** `€{price}`\n\n[👉 View Item on Vinted]({item_url})",
                "fields": [
                    {"name": "🏷️ Brand", "value": f"`{brand}`" if brand else "`N/A`", "inline": True},
                    {"name": "📏 Size", "value": f"`{size}`" if size else "`N/A`", "inline": True},
                    {"name": "💶 Currency", "value": "`EUR (€)`", "inline": True}
                ],
                "image": {"url": photo_url} if photo_url else {},
                "footer": {
                    "text": "Vinted Monitor • All Categories",
                    "icon_url": "https://www.vinted.fr/favicon.ico"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    try:
        res = scraper.post(DISCORD_WEBHOOK_URL, json=payload)
        print(f"Discord Alert Sent! Status Code: {res.status_code}", flush=True)
    except Exception as e:
        print(f"Discord Alert Error: {e}", flush=True)

def run_monitor():
    global scraper
    print("Vinted Monitor Initializing...", flush=True)
    scraper = create_fresh_scraper()

    while True:
        try:
            response = scraper.get(VINTED_URL, timeout=15)
            print(f"Vinted Fetch Status: {response.status_code}", flush=True)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                for item in items:
                    item_id = item.get("id")
                    if item_id not in seen_item_ids:
                        brand_title = item.get("brand_title") or "Unknown Brand"
                        title = item.get("title") or "No Title"
                        
                        brand_clean = brand_title.lower()
                        title_clean = title.lower()
                        
                        if any(b in brand_clean or b in title_clean for b in TARGET_BRANDS):
                            print(f"[MATCH FOUND] {brand_title} - {title} (€{item.get('price')})", flush=True)
                            photos = item.get("photos", [])
                            photo_url = photos[0].get("url", "") if photos else ""
                            send_discord_alert(
                                title,
                                item.get("price"),
                                brand_title,
                                item.get("size_title"),
                                item_id,
                                photo_url
                            )
                        else:
                            print(f"[IGNORED] {brand_title} | {title[:30]}", flush=True)
                            
                        seen_item_ids.add(item_id)

            elif response.status_code in [403, 429]:
                print(f"Block detected ({response.status_code}). Rebuilding session...", flush=True)
                time.sleep(15)
                scraper = create_fresh_scraper()

        except Exception as e:
            print(f"Connection error: {e}", flush=True)

        # Increased delay slightly to 30s to avoid triggering Cloudflare rate limits
        time.sleep(30)

if __name__ == "__main__":
    run_monitor()
