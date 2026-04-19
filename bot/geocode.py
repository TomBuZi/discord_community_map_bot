import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "discord-map-bot/1.0"}


def get_coords(plz: str, land: str = "Deutschland", strasse: str = None, hausnummer: str = None) -> tuple[float, float] | None:
    """
    Gibt (lat, lng) für eine Postleitzahl zurück.
    Mit Straße/Hausnummer wird eine präzisere Adresse abgefragt.
    Gibt None zurück wenn die Adresse nicht gefunden wird oder ein Fehler auftritt.
    """
    if strasse:
        adresse = f"{strasse} {hausnummer}".strip() if hausnummer else strasse
        q = f"{adresse}, {plz}, {land}"
    else:
        q = f"{plz}, {land}"
    params = {
        "q": q,
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
