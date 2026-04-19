import os
import math
import discord
from discord import app_commands
from dotenv import load_dotenv
from github import Github, GithubException

import geocode
import storage


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_DATA_REPO = os.getenv("GITHUB_DATA_REPO")
MAP_URL = os.getenv("MAP_URL")
ADMIN_GUILD_ID = int(os.getenv("ADMIN_GUILD_ID", "0"))


def nur_admin_server():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.guild_id == ADMIN_GUILD_ID
    return app_commands.check(predicate)

gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)
data_repo = gh.get_repo(GITHUB_DATA_REPO)

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

DATENSCHUTZ_HINWEIS = """🔒 **Datenschutzhinweis**

Durch die Eintragung werden folgende Daten **öffentlich** auf einer Karte angezeigt:
• Dein Anzeigename
• Deine Postleitzahl
• Dein Discord-Profil (als klickbarer Link)

Diese Daten sind für jeden einsehbar, der die Karte aufruft.

**Verantwortlich:** @tom_buzi (per Discord-DM erreichbar)
**Löschung:** jederzeit mit `/loeschen`
**Speicherdauer:** bis zur Löschung durch dich oder Auflösung des Servers

Bist du einverstanden?"""


class EintragungView(discord.ui.View):
    def __init__(self, name: str, plz: str, land: str, discord_id: str):
        super().__init__(timeout=60)
        self.name = name
        self.plz = plz
        self.land = land
        self.discord_id = discord_id
        self.message = None

    @discord.ui.button(label="Einverstanden", style=discord.ButtonStyle.success, emoji="✅")
    async def bestaetigen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True

        coords = geocode.get_coords(self.plz, self.land)
        if coords is None:
            await interaction.edit_original_response(
                content=f"Die Postleitzahl **{self.plz}** wurde leider nicht gefunden. Bitte versuch es erneut.",
                view=self,
            )
            return

        lat, lng = coords

        try:
            storage.add_user(data_repo, self.discord_id, self.name, self.plz, self.land, lat, lng)
        except GithubException:
            await interaction.edit_original_response(
                content="Es gab einen Fehler beim Speichern. Bitte versuch es in einem Moment erneut.",
                view=self,
            )
            return

        await interaction.edit_original_response(
            content=(
                f"✅ Du wurdest eingetragen! **{self.name}** aus PLZ **{self.plz}** ist jetzt auf der Karte.\n"
                f"Die Karte: {MAP_URL}\n\n"
                f"_Es kann bis zu 10 Minuten dauern, bis dein Eintrag auf der Karte sichtbar ist._\n"
                f"_Möchtest du deinen Eintrag später entfernen, nutze einfach `/loeschen`._"
            ),
            view=self,
        )

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.danger, emoji="❌")
    async def abbrechen(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="Kein Problem — du wurdest nicht eingetragen.",
            view=self,
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


@client.event
async def on_ready():
    await tree.sync()
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="die Community-Karte · /hilfe",
        )
    )
    print(f"Bot läuft als {client.user}")


@tree.command(name="eintragen", description="Trage dich mit Name und Postleitzahl in die Karte ein.")
@app_commands.describe(
    plz="Deine Postleitzahl",
    name="Dein Anzeigename auf der Karte (Standard: dein Discord-Username)",
    land="Dein Land (Standard: Deutschland)",
)
async def eintragen(interaction: discord.Interaction, plz: str, name: str = None, land: str = "Deutschland"):
    anzeigename = name if name else interaction.user.display_name

    if not plz.isdigit():
        await interaction.response.send_message(
            "Die Postleitzahl darf nur Ziffern enthalten.",
            ephemeral=True,
        )
        return

    view = EintragungView(anzeigename, plz, land, str(interaction.user.id))
    await interaction.response.send_message(DATENSCHUTZ_HINWEIS, view=view, ephemeral=True)
    view.message = await interaction.original_response()


@tree.command(name="loeschen", description="Entferne deinen Eintrag von der Karte.")
async def loeschen(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    try:
        removed = storage.remove_user(data_repo, str(interaction.user.id))
    except GithubException:
        await interaction.followup.send(
            "Es gab einen Fehler beim Löschen. Bitte versuch es in einem Moment erneut.",
            ephemeral=True,
        )
        return

    if removed:
        await interaction.followup.send("Dein Eintrag wurde von der Karte entfernt.", ephemeral=True)
    else:
        await interaction.followup.send("Du warst nicht auf der Karte eingetragen.", ephemeral=True)


async def user_eintraege_autocomplete(interaction: discord.Interaction, current: str):
    users = storage.get_users(data_repo)
    return [
        app_commands.Choice(name=f"{u['name']} ({u.get('plz', '?')})", value=u["discord_id"])
        for u in users
        if u.get("type") != "admin" and current.lower() in u["name"].lower()
    ][:25]


@tree.command(name="admin_user_loeschen", description="[Admin] Entfernt den Karteneintrag eines Nutzers.")
@app_commands.describe(nutzer="Nutzer aus der Karte auswählen")
@app_commands.autocomplete(nutzer=user_eintraege_autocomplete)
@app_commands.checks.has_permissions(administrator=True)
@nur_admin_server()
async def admin_user_loeschen(interaction: discord.Interaction, nutzer: str):
    await interaction.response.defer(ephemeral=True)

    try:
        removed = storage.remove_user(data_repo, nutzer)
    except GithubException:
        await interaction.followup.send(
            "Es gab einen Fehler beim Löschen. Bitte versuch es in einem Moment erneut.",
            ephemeral=True,
        )
        return

    if removed:
        await interaction.followup.send(
            "Der Eintrag wurde von der Karte entfernt.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            "Dieser Nutzer war nicht auf der Karte eingetragen.",
            ephemeral=True,
        )


@tree.command(name="admin_eintragen", description="[Admin] Trägt einen Ort oder eine Organisation in die Karte ein.")
@app_commands.describe(
    name="Anzeigename auf der Karte",
    plz="Postleitzahl",
    strasse="Straße (optional)",
    hausnummer="Hausnummer (optional)",
    land="Land (Standard: Deutschland)",
    url="Webadresse (optional)",
    url_text="Linktext für die Webadresse, z.B. 'Zur Website' (optional)",
    beschreibung="Kurzbeschreibung im Popup (optional)",
)
@app_commands.checks.has_permissions(administrator=True)
@nur_admin_server()
async def admin_eintragen(
    interaction: discord.Interaction,
    name: str,
    plz: str,
    strasse: str = None,
    hausnummer: str = None,
    land: str = "Deutschland",
    url: str = None,
    url_text: str = None,
    beschreibung: str = None,
):
    await interaction.response.defer(ephemeral=True)

    coords = geocode.get_coords(plz, land, strasse, hausnummer)
    if coords is None:
        await interaction.followup.send(
            f"Die Adresse **{plz}, {land}** wurde nicht gefunden. Bitte prüfe die Angaben.",
            ephemeral=True,
        )
        return

    lat, lng = coords
    try:
        storage.add_admin_entry(data_repo, name, plz, land, lat, lng, strasse, hausnummer, url, url_text, beschreibung)
    except GithubException:
        await interaction.followup.send(
            "Es gab einen Fehler beim Speichern. Bitte versuch es in einem Moment erneut.",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"✅ **{name}** wurde als Admin-Eintrag in die Karte eingetragen.\n"
        f"_Es kann bis zu 10 Minuten dauern, bis der Eintrag auf der Karte sichtbar ist._",
        ephemeral=True,
    )


@admin_eintragen.error
async def admin_eintragen_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        await interaction.response.send_message(
            "Du hast keine Berechtigung für diesen Befehl.",
            ephemeral=True,
        )


async def admin_eintraege_autocomplete(interaction: discord.Interaction, current: str):
    users = storage.get_users(data_repo)
    return [
        app_commands.Choice(name=u["name"], value=u["name"])
        for u in users
        if u.get("type") == "admin" and current.lower() in u["name"].lower()
    ][:25]


@tree.command(name="admin_eintrag_loeschen", description="[Admin] Entfernt einen Admin-Karteneintrag.")
@app_commands.describe(name="Name des Eintrags")
@app_commands.autocomplete(name=admin_eintraege_autocomplete)
@app_commands.checks.has_permissions(administrator=True)
@nur_admin_server()
async def admin_eintrag_loeschen(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)

    try:
        removed = storage.remove_admin_entry(data_repo, name)
    except GithubException:
        await interaction.followup.send(
            "Es gab einen Fehler beim Löschen. Bitte versuch es in einem Moment erneut.",
            ephemeral=True,
        )
        return

    if removed:
        await interaction.followup.send(
            f"Admin-Eintrag **{name}** wurde von der Karte entfernt.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            f"Kein Admin-Eintrag mit dem Namen **{name}** gefunden.",
            ephemeral=True,
        )


@admin_eintrag_loeschen.error
async def admin_eintrag_loeschen_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        await interaction.response.send_message(
            "Du hast keine Berechtigung für diesen Befehl.",
            ephemeral=True,
        )


@admin_user_loeschen.error
async def admin_user_loeschen_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        await interaction.response.send_message(
            "Du hast keine Berechtigung für diesen Befehl.",
            ephemeral=True,
        )


@tree.command(name="find", description="Zeigt alle Mitglieder im Umkreis von X Kilometern.")
@app_commands.describe(km="Suchradius in Kilometern")
async def find(interaction: discord.Interaction, km: int):
    await interaction.response.defer(ephemeral=True)

    users = storage.get_users(data_repo)
    own = next((u for u in users if u.get("discord_id") == str(interaction.user.id)), None)

    if own is None:
        await interaction.followup.send(
            "Du bist noch nicht auf der Karte eingetragen. Nutze `/eintragen`, um dich hinzuzufügen.",
            ephemeral=True,
        )
        return

    nearby = []
    for u in users:
        if u.get("discord_id") == str(interaction.user.id):
            continue
        dist = haversine_km(own["lat"], own["lng"], u["lat"], u["lng"])
        if dist <= km:
            nearby.append((dist, u))

    nearby.sort(key=lambda x: x[0])

    if not nearby:
        await interaction.followup.send(
            f"Keine Mitglieder im Umkreis von **{km} km** gefunden.",
            ephemeral=True,
        )
        return

    lines = [f"**Mitglieder im Umkreis von {km} km:**"]
    for dist, u in nearby:
        lines.append(f"• {u['name']} (<@{u['discord_id']}>) — {dist:.0f} km")

    await interaction.followup.send("\n".join(lines), ephemeral=True)


HILFE_TEXT = """🗺️ **Marvel Champions Community Map**

Trag dich auf unserer gemeinsamen Karte ein! Alle Mitglieder sind als Marker sichtbar.

**Befehle**
📍 `/eintragen` – Trägt dich mit Name und Postleitzahl ein. Erneutes Eintragen überschreibt den alten Eintrag.
🔍 `/find km:<zahl>` – Zeigt alle Mitglieder im Umkreis von X Kilometern, sortiert nach Entfernung.
🗑️ `/loeschen` – Entfernt deinen Eintrag von der Karte.
🌍 `/karte` – Zeigt dir den Link zur Karte.

**Hinweise**
- PLZ und Land werden zur Standortbestimmung genutzt (auch nicht-deutsche PLZ möglich)
- Auf der Karte ist dein Name sichtbar — klick auf den Marker für dein Discord-Profil
- Nach dem Eintragen kann es ein paar Minuten dauern bis du auf der Karte erscheinst
- `/find` zeigt Luftlinien-Distanzen und ist nur für dich sichtbar

🔒 **Datenschutz**
Die Teilnahme ist freiwillig. Gespeichert werden: dein Anzeigename, deine Postleitzahl und dein Discord-Profil (öffentlich einsehbar).
Löschung jederzeit mit `/loeschen`. Verantwortlich: @tom_buzi (per DM erreichbar)."""

HILFE_ADMIN = """

⚙️ **Admin-Befehle**
📌 `/admin_eintragen` – Trägt einen Ort oder eine Organisation ein (roter Marker).
🗑️ `/admin_eintrag_loeschen` – Entfernt einen Admin-Eintrag per Name.
❌ `/admin_user_loeschen` – Entfernt den Karteneintrag eines Nutzers (Dropdown-Auswahl)."""


@tree.command(name="hilfe", description="Zeigt alle Befehle und Hinweise zur Community-Karte.")
async def hilfe(interaction: discord.Interaction):
    ist_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
    text = HILFE_TEXT + (HILFE_ADMIN if ist_admin else "")
    await interaction.response.send_message(text, ephemeral=True)


@tree.command(name="karte", description="Zeigt den Link zur Community-Karte.")
async def karte(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Hier ist die Community-Karte: {MAP_URL}",
        ephemeral=True,
    )


client.run(DISCORD_TOKEN)
