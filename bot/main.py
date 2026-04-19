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
    def __init__(self, name: str, plz: str, discord_id: str):
        super().__init__(timeout=60)
        self.name = name
        self.plz = plz
        self.discord_id = discord_id
        self.message = None

    @discord.ui.button(label="Einverstanden", style=discord.ButtonStyle.success, emoji="✅")
    async def bestaetigen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True

        coords = geocode.get_coords(self.plz)
        if coords is None:
            await interaction.edit_original_response(
                content=f"Die Postleitzahl **{self.plz}** wurde leider nicht gefunden. Bitte versuch es erneut.",
                view=self,
            )
            return

        lat, lng = coords

        try:
            storage.add_user(repo, self.discord_id, self.name, self.plz, lat, lng)
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
    print(f"Bot läuft als {client.user}")


@tree.command(name="eintragen", description="Trage dich mit Name und Postleitzahl in die Karte ein.")
@app_commands.describe(
    name="Dein Name (wird auf der Karte angezeigt)",
    plz="Deine Postleitzahl (5 Ziffern)",
)
async def eintragen(interaction: discord.Interaction, name: str, plz: str):
    if not (plz.isdigit() and len(plz) == 5):
        await interaction.response.send_message(
            "Die Postleitzahl muss genau 5 Ziffern haben (z.B. `10115`).",
            ephemeral=True,
        )
        return

    view = EintragungView(name, plz, str(interaction.user.id))
    await interaction.response.send_message(DATENSCHUTZ_HINWEIS, view=view, ephemeral=True)
    view.message = await interaction.original_response()


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


@tree.command(name="admin_loeschen", description="[Admin] Entfernt den Karteneintrag eines anderen Nutzers.")
@app_commands.describe(nutzer="Der Nutzer, dessen Eintrag entfernt werden soll.")
@app_commands.checks.has_permissions(administrator=True)
async def admin_loeschen(interaction: discord.Interaction, nutzer: discord.Member):
    await interaction.response.defer(ephemeral=True)

    try:
        removed = storage.remove_user(repo, str(nutzer.id))
    except GithubException:
        await interaction.followup.send(
            "Es gab einen Fehler beim Löschen. Bitte versuch es in einem Moment erneut.",
            ephemeral=True,
        )
        return

    if removed:
        await interaction.followup.send(
            f"Der Eintrag von **{nutzer.display_name}** wurde von der Karte entfernt.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            f"**{nutzer.display_name}** war nicht auf der Karte eingetragen.",
            ephemeral=True,
        )


@admin_loeschen.error
async def admin_loeschen_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "Du hast keine Berechtigung für diesen Befehl.",
            ephemeral=True,
        )


@tree.command(name="karte", description="Zeigt den Link zur Community-Karte.")
async def karte(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Hier ist die Community-Karte: {MAP_URL}",
        ephemeral=True,
    )


client.run(DISCORD_TOKEN)
