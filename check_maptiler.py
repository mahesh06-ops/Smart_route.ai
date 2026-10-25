from dotenv import dotenv_values
import urllib.request
import urllib.error

key = (dotenv_values(".env").get("MAPTILER_API_KEY") or "").strip()

if not key or key.startswith("YOUR_"):
    print("ERROR: MAPTILER_API_KEY missing from .env")
else:
    url = "https://api.maptiler.com/maps/hybrid/style.json?key=" + key
    request = urllib.request.Request(
        url,
        headers={"Origin": "http://127.0.0.1:8000"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print("HTTP status:", response.status)
            print("MapTiler style access: OK")
    except urllib.error.HTTPError as error:
        print("HTTP status:", error.code)
        print("MapTiler response:", error.read().decode("utf-8", errors="replace")[:500])
    except Exception as error:
        print("Connection error:", type(error).__name__, str(error))
