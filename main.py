import time
import cloudscraper
from datetime import datetime

# 1. Your Discord Webhook Link
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1550604418112823318/-GczalwvRKujHA_6JwGSBba-3f3ceejYIUz-jQv9h4Z5NNgDLI7BG4iwqVROEYtbmCw-"

# 2. Vinted Search Endpoint
VINTED_URL = "https://www.vinted.fr/api/v2/catalog/items?search_text=nike%20ralph%20lauren&price_to=50&currency=EUR"

# Initialize cloudscraper to auto-bypass Cloudflare
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

seen_item_ids = set()

def send_discord_alert(title, price, brand, size, item_id, photo_url):
    """Sends the formatted rich embed directly to Discord."""
    item_url = f"https://www.vinted.fr/items/{item_id}"
    
    payload = {
        "username": "Vinted Deal Monitor",
        "avatar_url": "https://www.vinted.fr/favicon.ico",
        "embeds": [
            {
                "title": f"🔥 {title or 'New Listing Found!'}",
                "url": item_url,
                "color": 0x00A8A8,
                "description": f"**Price:** `€{price}`\n\n[👉 Tap here to view item on Vinted]({item_url})",
                "fields": [
                    {"name": "🏷️ Brand", "value": f"`{brand}`" if brand else "`N/A`", "inline": True},
                    {"name": "📏 Size", "value": f"`{size}`" if size else "`N/A`", "inline": True},
                    {"name": "💶 Currency", "value": "`EUR (€)`", "inline": True}
                ],
                "image": {"url": photo_url} if photo_url else {},
                "footer": {
                    "text": "Vinted Monitor • Ireland Alerts",
                    "icon_url": "https://www.vinted.fr/favicon.ico"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    try:
        scraper.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Discord Alert Error: {e}")

def run_monitor():
    print("Vinted Cloudscraper Active: Monitoring Nike & Ralph Lauren under €50...")

    # Warm up session and acquire Cloudflare clearance tokens
    try:
        scraper.get("https://www.vinted.fr")
        print("Cloudflare verification passed!")
    except Exception as e:
        print(f"Initial setup warning: {e}")

    while True:
        try:
            response = scraper.get(VINTED_URL, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                for item in items:
                    item_id = item.get("id")
                    if item_id not in seen_item_ids:
                        if len(seen_item_ids) > 0:
                            print(f"New deal found: {item.get('title')}")
                            
                            photos = item.get("photos", [])
                            photo_url = photos[0].get("url", "") if photos else ""
                            
                            send_discord_alert(
                                item.get("title"),
                                item.get("price"),
                                item.get("brand_title"),
                                item.get("size_title"),
                                item_id,
                                photo_url
                            )
                        seen_item_ids.add(item_id)

            elif response.status_code in [403, 404, 429]:
                print(f"Response {response.status_code}. Re-authenticating session...")
                time.sleep(10)
                scraper.get("https://www.vinted.fr")
            else:
                print(f"Status Code: {response.status_code}")

        except Exception as e:
            print(f"Connection paused: {e}")

        # Check interval
        time.sleep(20)

if __name__ == "__main__":
    run_monitor()
