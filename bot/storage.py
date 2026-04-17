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


def add_user(repo, discord_id: str, name: str, plz: str, lat: float, lng: float) -> None:
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
        "lat": lat,
        "lng": lng,
    })
    save_users(repo, users)


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
