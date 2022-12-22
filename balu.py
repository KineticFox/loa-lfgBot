import os
import discord
import dotenv

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))

raids = {"Argos": 8, "Valtan": 8, "Vykas": 8, "Kakul-Saydon": 4, "Brelshaza": 8}
chartypes = {"Bardin": "Supporter", "Zauberin": "DD", "Arcanistin": "DD", "Beschwörerin": "DD", "Paladin": "Supporter"}

bot = discord.Bot()


class Raidview(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.int_spieler = 2

    @discord.ui.button(label="Bin dabei!", custom_id="burton-join")
    
    async def join(self, button, interaction):
        embed = interaction.message.embeds[0]
        embed.add_field(name=f'Spieler {self.int_spieler}', value=interaction.user, inline=True)
        test = embed.to_dict()
        print(f'Embed:\n{test}')
        self.int_spieler += 1
        await interaction.response.send_message(content='Es wird geraidet! Bist du dabei?', embed=embed, view=self)


@bot.command()
async def lfg(ctx: discord.ApplicationContext,
              raid: discord.Option(str, "Wähle den Raid aus.", choices=raids),
              deine_klasse: discord.Option(str, "Welche Klasse?", choices=chartypes),
              datum_uhrzeit: discord.Option(str, "wann?", required=True),
              ):
    int_spieler = 1
    embed = discord.Embed(
        title=raid,
        color=discord.Colour.blue(),
    )
    embed.add_field(name="Datum/Uhrzeit", value=datum_uhrzeit)
    embed.add_field(name=f'Spieler {int_spieler}', value=f'{ctx.author} / {deine_klasse}', inline=True)
    int_spieler += 1
    embed.set_author(name=ctx.author)
    

    await ctx.respond('Es wird geraidet! Bist du dabei?', embed=embed, view=Raidview())


#bot.run('OTMzNzU3ODI5NDM5OTU5MDUw.YemLvg.drJUy37X_b55zRqPHUgoUMzTkmo')
bot.run(token)