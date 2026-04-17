# Community Map Bot

Ein Discord-Bot, mit dem sich Server-Mitglieder mit Name und Postleitzahl auf einer gemeinsamen Karte eintragen können.

## Was der Bot kann

| Command | Sichtbar für | Funktion |
|---|---|---|
| `/eintragen name:<name> plz:<plz>` | Nur dich | Eintragen oder Eintrag aktualisieren |
| `/loeschen` | Nur dich | Eigenen Eintrag entfernen |
| `/karte` | Alle im Channel | Link zur Karte posten |

---

## Einrichtung

### Schritt 1 — GitHub-Repository anlegen

1. Geh auf [github.com](https://github.com) und melde dich an.
2. Klick oben rechts auf **+** → **New repository**.
3. Name: `discord_map_bot` — **Public** auswählen (nötig für GitHub Pages) → **Create repository**.
4. Lade alle Dateien aus diesem Projekt in das Repo hoch.
   - Entweder per **Drag & Drop** im Browser-Interface
   - Oder per Git-Kommandozeile:
     ```bash
     git init
     git add .
     git commit -m "Erster Commit"
     git remote add origin https://github.com/DEINUSERNAME/discord_map_bot.git
     git push -u origin main
     ```

---

### Schritt 2 — Discord-Bot erstellen

1. Geh auf [discord.com/developers/applications](https://discord.com/developers/applications).
2. Klick auf **New Application** → gib dem Bot einen Namen (z.B. „Karten Bot") → **Create**.
3. Klick links auf **Bot**.
4. Klick auf **Reset Token** → bestätige → **kopiere den Token** und speichere ihn sicher. Du siehst ihn nur einmal.
5. Klick links auf **OAuth2** → **URL Generator**.
6. Unter **Scopes** wähle: `bot` und `applications.commands`.
7. Unter **Bot Permissions** wähle: `Send Messages`.
8. Kopiere die generierte URL ganz unten, öffne sie im Browser und lade den Bot zu deinem Server ein.

---

### Schritt 3 — GitHub Personal Access Token erstellen

Der Bot braucht diesen Token, um die Kartendaten in deinem Repo zu speichern.

1. Geh auf GitHub → klick oben rechts auf dein Profilbild → **Settings**.
2. Ganz unten links: **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
3. Klick auf **Generate new token (classic)**.
4. Gib ihm einen Namen (z.B. „discord-bot") und setze die Ablaufzeit nach Wunsch.
5. Unter **Select scopes** setze einen Haken bei **repo** (der erste, übergeordnete Eintrag).
6. Klick auf **Generate token** → **kopiere den Token**. Auch dieser wird nur einmal angezeigt.

---

### Schritt 4 — GitHub Pages aktivieren (die Karten-Webseite)

1. Geh in dein GitHub-Repo → **Settings** → links im Menü **Pages**.
2. Unter **Source**: Branch `main` auswählen, Ordner `/docs` → **Save**.
3. Warte 1–2 Minuten. GitHub zeigt dir dann deine Karten-URL an:
   `https://DEINUSERNAME.github.io/discord_map_bot`
4. Öffne `docs/index.html` in deinem Repo und passe die Zeile mit `DATA_URL` an — ersetze `DEINUSERNAME` und `DEINREPO` mit deinen echten Werten. Speichere die Änderung.

---

### Schritt 5 — Bot auf Discloud deployen

[Discloud](https://discloud.com) ist ein kostenloser Hosting-Dienst speziell für Discord-Bots.

#### 5a — Account erstellen & Discord verbinden

1. Geh auf [discloud.com](https://discloud.com) → **Login with Discord**.
2. Autorisiere Discloud für deinen Discord-Account.

#### 5b — Projekt als ZIP hochladen

1. Packe **alle Dateien dieses Projekts** (inkl. `discloud.config`, `bot/`, `data/`) in eine ZIP-Datei.
   - Wichtig: Die `discloud.config` muss direkt im **Wurzelverzeichnis** der ZIP liegen, nicht in einem Unterordner.
2. Geh im Discloud-Dashboard auf **Add App** → **Upload ZIP**.
3. Lade die ZIP-Datei hoch.

#### 5c — Umgebungsvariablen setzen

Nach dem Upload erscheint deine App im Dashboard. Klick darauf und geh zu **Environment** (oder „Env Vars"):

| Variable | Wert |
|---|---|
| `DISCORD_TOKEN` | Dein Discord-Bot-Token (aus Schritt 2) |
| `GITHUB_TOKEN` | Dein GitHub-Token (aus Schritt 3) |
| `GITHUB_REPO` | `DEINUSERNAME/discord_map_bot` |
| `MAP_URL` | `https://DEINUSERNAME.github.io/discord_map_bot` |

Speichere die Variablen. Discloud startet den Bot automatisch neu.

#### 5d — Status prüfen

Im Dashboard siehst du, ob der Bot läuft (grüner Punkt). Im Log-Tab kannst du die Ausgabe sehen — dort sollte erscheinen:
```
Bot läuft als DeinBotName#1234
```

---

## Hinweise

- **Slash-Commands:** Nach dem ersten Start kann es bis zu **1 Stunde** dauern, bis `/eintragen`, `/loeschen` und `/karte` in Discord erscheinen. Das ist normal — Discord verteilt neue Commands global.
- **Karten-Aktualisierung:** Nach einem neuen Eintrag kann die Karte bis zu **5 Minuten** veraltet sein (GitHub CDN-Cache). Ein Ctrl+Shift+R im Browser erzwingt die neueste Version.
- **PLZ-Format:** Nur deutsche 5-stellige Postleitzahlen werden unterstützt.
- **Umzug:** Wer `/eintragen` erneut aufruft, überschreibt seinen alten Eintrag automatisch — kein Duplikat entsteht.

---

## Projektstruktur

```
discord_map_bot/
├── bot/
│   ├── main.py           ← Bot-Einstiegspunkt, alle Slash-Commands
│   ├── geocode.py        ← Postleitzahl → Koordinaten (OpenStreetMap)
│   ├── storage.py        ← Daten in GitHub lesen und schreiben
│   └── requirements.txt  ← Python-Abhängigkeiten
├── data/
│   └── users.json        ← Kartendaten (wird vom Bot automatisch aktualisiert)
├── docs/
│   └── index.html        ← Karten-Webseite (GitHub Pages)
├── discloud.config        ← Discloud-Konfiguration
├── .env.example           ← Vorlage für Umgebungsvariablen
├── .gitignore
└── README.md
```
