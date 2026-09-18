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

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

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
        print(f"Discord Alert Sent! Status Code: {res.status_code}")
    except Exception as e:
        print(f"Discord Alert Error: {e}")

def run_monitor():
    print("Vinted Monitor Started with Active Logging...")
    try:
        scraper.get("https://www.vinted.fr")
    except Exception:
        pass

    while True:
        try:
            response = scraper.get(VINTED_URL, timeout=15)
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
                        
                        # Match target brands
                        if any(b in brand_clean or b in title_clean for b in TARGET_BRANDS):
                            print(f"[MATCH FOUND] {brand_title} - {title} (€{item.get('price')})")
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
                            # Log scanned and rejected items
                            print(f"[IGNORED] {brand_title} | {title[:30]}")
                            
                        seen_item_ids.add(item_id)
            elif response.status_code in [403, 404, 429]:
                print(f"Vinted blocked IP ({response.status_code}), re-authenticating...")
                time.sleep(10)
                scraper.get("https://www.vinted.fr")
        except Exception as e:
            print(f"Connection error: {e}")

        time.sleep(20)

if __name__ == "__main__":
    run_monitor()
