from http.server import BaseHTTPRequestHandler, HTTPServer
import json, urllib.request, os, sys
from urllib.parse import urlparse, parse_qs

SDIO_KEY = os.environ.get("SPORTS_DATA_API_KEY") or os.environ.get("SPORTSDATAIO_API_KEY", "")
SDIO_BASE = "https://api.sportsdata.io/v3"

SPORT_MAP = {
    "MLB": "mlb",
    "NBA": "nba",
    "NFL": "nfl",
    "WNBA": "wnba",
    "NHL": "nhl"
}

def fetch_sdio(path, params=""):
    url = f"{SDIO_BASE}/{path}?{params}" if params else f"{SDIO_BASE}/{path}"
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": SDIO_KEY})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"error": str(e), "body": e.read().decode()[:500]}
    except Exception as e:
        return 500, {"error": str(e)}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        sport = qs.get("sport", ["MLB"])[0].upper()
        date = qs.get("date", [""])[0]
        sdio_sport = SPORT_MAP.get(sport, sport.lower())

        if path == "/health":
            self.send_json(200, {"ok": True, "service": "sdio-lines", "key_set": bool(SDIO_KEY)})
            return

        if path == "/games":
            params = f"date={date}" if date else ""
            code, data = fetch_sdio(f"{sdio_sport}/scores/json/Games", params)
            self.send_json(code if code == 200 else 200, {
                "sport": sport,
                "source": "SportsDataIO",
                "count": len(data) if isinstance(data, list) else 0,
                "games": data if isinstance(data, list) else [],
                "status_code": code
            })
            return

        if path == "/odds":
            params = f"date={date}" if date else ""
            code, data = fetch_sdio(f"{sdio_sport}/odds/json/GameOdds", params)
            self.send_json(code if code == 200 else 200, {
                "sport": sport,
                "source": "SportsDataIO",
                "count": len(data) if isinstance(data, list) else 0,
                "odds": data if isinstance(data, list) else [],
                "status_code": code
            })
            return

        self.send_json(404, {"error": "not found", "path": path, "routes": ["/health", "/games", "/odds"]})

    def send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8520))
    print(f"[sdio-lines] starting on :{port}", flush=True)
    print(f"[sdio-lines] key set: {bool(SDIO_KEY)}", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
