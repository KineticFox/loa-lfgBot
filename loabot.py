import os
import discord
import dotenv

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))

bot = discord.Bot()


class LegionRaid(discord.ui.Select):
    
    def __init__(self, raidtype):
        super().__init__(
            #select_type,
            #custom_id=custom_id, 
            placeholder='Choose Raid', 
            min_values=1, 
            max_values=1, 
            options= [
                discord.SelectOption(
                    label="Clown",
                    description="Legion raid Kaykol",
                ),
                discord.SelectOption(
                    label="Vykas",
                    description="Legion raid Vykas",
                ),
                discord.SelectOption(
                    label="Brel",
                    description="Legion raid Brelshaza",
                )
            ], 
        )
        self.raidtype = raidtype  

    
    async def callback(self, interaction:discord.Interaction):
        self.raidtype = self.values[0]
        await interaction.response.send_message(f"Du willst also {self.raidtype} erstellen")



    #async def on_timeout(self):
    #    for child in self.children:
    #        child.disabled = True
    #    await self.message.edit(content="Took to long", view=self)

class CreateRaid(discord.ui.Button):

    def __init__(self, raidtype):
        super().__init__(
            style=discord.enums.ButtonStyle.green, 
            label="Los", 
            custom_id="interaction:DefaultButton"
        )
        self.raidtype = raidtype
        

    async def callback(self, interaction:discord.Interaction):
        #message = await interaction.response.send_message("Verwalte den Raid")
        #await message.create_thread(name="Legionraid")
        await interaction.response.send_message(f'du hast geklickt und willst {self.raidtype} raiden')

class LegionRaidCreation(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

     
    @discord.ui.select(
        placeholder = "Choose a Raid!", 
        min_values = 1, 
        max_values = 1,
        custom_id='raid', 
        options = [ 
            discord.SelectOption(
                label="Kakul-Saydon",
                description="Kakul-Saydon Raid "
            ),
            discord.SelectOption(
                label="Brelshaza",
                description="Brelshaza raid"
            ),
            discord.SelectOption(
                label="Vykas",
                description="Vykas Raid"
            )
        ]
    )    
    async def selectRaid_callback(self, select, interaction):
        #await interaction.response.send_message(f"Awesome! I like {select.values[0]} too!")
        embed = interaction.message.embeds[0]
        embed.add_field(name=f'Raid: ', value=select.values[0])
        select.placeholder = select.values[0]
        mode = self.get_item('mode')
        mode.disabled = False
        await interaction.response.send_message(f'du hast {select.values[0]} gewählt', embed=embed, view=self)

    @discord.ui.select(
        placeholder = "Choose a Mode!", 
        min_values = 1, 
        max_values = 1,
        disabled=True,
        custom_id='mode', 
        options = [ 
            discord.SelectOption(
                label="Normal Mode (GS 1430)",
                description="Kakul-Saydon Raid "
            ),
            discord.SelectOption(
                label="Hard Mode (GS 1460)",
                description="Brelshaza raid"
            ),
        ]
    )    
    async def selectMode_callback(self, select, interaction):
        #await interaction.response.send_message(f"Awesome! I like {select.values[0]} too!")
        embed = interaction.message.embeds[0]
        embed.add_field(name=f'Raid Mode: ', value=select.values[0])
        createButton  = self.get_item('create')
        createButton.disabled = False
        await interaction.response.send_message(f'du hast {select.values[0]} gewählt', embed=embed, view=self)
        

    @discord.ui.button(
        label="Create Raid",
        style=discord.ButtonStyle.green,
        row=4,
        custom_id='create',
        disabled=True
    )
    async def button_callback(self, button, interaction):
        await interaction.response.send_message('du hast den raid erstellt')


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.slash_command(name = "hi", description = "say hi")
async def hello(ctx):
    await ctx.respond("hello")

@bot.slash_command(name="lfg", description="creates a raid")
async def create_raid(ctx, title: discord.Option(str, 'Choose a title'), date: discord.Option(str, 'When?', required=True)):
    time = date
    #title = title

    panel = discord.Embed(
        title=title,
        color=discord.Colour.blue(),
    )
    panel.add_field(name="Date/Time", value=time, inline=True)
    panel.set_author(name=ctx.author)

    await ctx.respond("A wild Raid spawns, come and join", embed=panel, view=LegionRaidCreation())



bot.run(token)