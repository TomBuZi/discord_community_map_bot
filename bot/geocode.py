import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "discord-map-bot/1.0"}


def get_coords(plz: str) -> tuple[float, float] | None:
    """
    Gibt (lat, lng) für eine deutsche Postleitzahl zurück.
    Gibt None zurück wenn die PLZ nicht gefunden wird oder ein Fehler auftritt.
    """
    params = {
        "q": f"{plz},Germany",
        "format": "json",
        "limit": 1,
    }
    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        lat = float(results[0]["lat"])
        lng = float(results[0]["lon"])
        return lat, lng
    except (requests.RequestException, KeyError, ValueError):
        return None
