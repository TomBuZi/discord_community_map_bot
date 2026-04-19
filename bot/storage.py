import json
import github

DATA_PATH = "data/users.json"


def get_users(repo) -> list[dict]:
    """Liest die aktuelle Nutzerliste aus dem GitHub-Repo."""
    try:
        content_file = repo.get_contents(DATA_PATH)
        return json.loads(content_file.decoded_content.decode("utf-8"))
    except github.GithubException:
        return []


def save_users(repo, users: list[dict]) -> None:
    """Schreibt die Nutzerliste zurück ins GitHub-Repo."""
    content = json.dumps(users, indent=2, ensure_ascii=False)
    content_file = repo.get_contents(DATA_PATH)
    repo.update_file(
        path=DATA_PATH,
        message="Bot: Nutzerdaten aktualisiert",
        content=content,
        sha=content_file.sha,
    )


def add_user(repo, discord_id: str, name: str, plz: str, land: str, lat: float, lng: float) -> None:
    """
    Fügt einen Nutzer hinzu oder aktualisiert seinen bestehenden Eintrag.
    Jeder Discord-Nutzer kann nur einen Eintrag haben.
    """
    users = get_users(repo)
    users = [u for u in users if u["discord_id"] != discord_id]
    users.append({
        "discord_id": discord_id,
        "name": name,
        "plz": plz,
        "land": land,
        "lat": lat,
        "lng": lng,
    })
    save_users(repo, users)


def add_admin_entry(repo, name: str, plz: str, land: str, lat: float, lng: float,
                    strasse: str = None, hausnummer: str = None, url: str = None,
                    url_text: str = None, beschreibung: str = None) -> None:
    """Fügt einen Admin-Eintrag hinzu. Überschreibt einen bestehenden Eintrag mit gleichem Namen."""
    users = get_users(repo)
    users = [u for u in users if not (u.get("type") == "admin" and u["name"].lower() == name.lower())]
    entry = {"type": "admin", "name": name, "plz": plz, "land": land, "lat": lat, "lng": lng}
    if strasse:
        entry["strasse"] = strasse
    if hausnummer:
        entry["hausnummer"] = hausnummer
    if url:
        entry["url"] = url
    if url_text:
        entry["url_text"] = url_text
    if beschreibung:
        entry["beschreibung"] = beschreibung
    users.append(entry)
    save_users(repo, users)


def remove_admin_entry(repo, name: str) -> bool:
    """Entfernt einen Admin-Eintrag per Name (Groß-/Kleinschreibung egal)."""
    users = get_users(repo)
    filtered = [u for u in users if not (u.get("type") == "admin" and u["name"].lower() == name.lower())]
    if len(filtered) == len(users):
        return False
    save_users(repo, filtered)
    return True


def remove_user(repo, discord_id: str) -> bool:
    """
    Entfernt den Eintrag eines Nutzers.
    Gibt True zurück wenn ein Eintrag gelöscht wurde, sonst False.
    """
    users = get_users(repo)
    filtered = [u for u in users if u["discord_id"] != discord_id]
    if len(filtered) == len(users):
        return False
    save_users(repo, filtered)
    return True
