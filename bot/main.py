import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from github import Github, GithubException

import geocode
import storage

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
MAP_URL = os.getenv("MAP_URL")

gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)

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
    def __init__(self, name: str, plz: str, lat: float, lng: float, discord_id: str):
        super().__init__(timeout=60)
        self.name = name
        self.plz = plz
        self.lat = lat
        self.lng = lng
        self.discord_id = discord_id

    @discord.ui.button(label="Einverstanden", style=discord.ButtonStyle.success, emoji="✅")
    async def bestaetigen(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all_items()
        try:
            storage.add_user(repo, self.discord_id, self.name, self.plz, self.lat, self.lng)
        except GithubException:
            await interaction.response.edit_message(
                content="Es gab einen Fehler beim Speichern. Bitte versuch es in einem Moment erneut.",
                view=self,
            )
            return

        await interaction.response.edit_message(
            content=f"✅ Du wurdest eingetragen! **{self.name}** aus PLZ **{self.plz}** ist jetzt auf der Karte.\nDie Karte: {MAP_URL}",
            view=self,
        )

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.danger, emoji="❌")
    async def abbrechen(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all_items()
        await interaction.response.edit_message(
            content="Kein Problem — du wurdest nicht eingetragen.",
            view=self,
        )

    async def on_timeout(self):
        self.disable_all_items()


@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot läuft als {client.user}")


@tree.command(name="eintragen", description="Trage dich mit Name und Postleitzahl in die Karte ein.")
@app_commands.describe(
    name="Dein Name (wird auf der Karte angezeigt)",
    plz="Deine Postleitzahl (5 Ziffern)",
)
async def eintragen(interaction: discord.Interaction, name: str, plz: str):
    await interaction.response.defer(ephemeral=True)

    if not (plz.isdigit() and len(plz) == 5):
        await interaction.followup.send(
            "Die Postleitzahl muss genau 5 Ziffern haben (z.B. `10115`).",
            ephemeral=True,
        )
        return

    coords = geocode.get_coords(plz)
    if coords is None:
        await interaction.followup.send(
            f"Die Postleitzahl **{plz}** wurde leider nicht gefunden. "
            "Bitte überprüfe sie und versuch es erneut.",
            ephemeral=True,
        )
        return

    lat, lng = coords
    view = EintragungView(name, plz, lat, lng, str(interaction.user.id))
    await interaction.followup.send(DATENSCHUTZ_HINWEIS, view=view, ephemeral=True)


@tree.command(name="loeschen", description="Entferne deinen Eintrag von der Karte.")
async def loeschen(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    try:
        removed = storage.remove_user(repo, str(interaction.user.id))
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


@tree.command(name="karte", description="Zeigt den Link zur Community-Karte.")
async def karte(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Hier ist die Community-Karte: {MAP_URL}"
    )


client.run(DISCORD_TOKEN)
