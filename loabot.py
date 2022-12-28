import os
import discord
import dotenv

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))

bot = discord.Bot()



    #async def on_timeout(self):
    #    for child in self.children:
    #        child.disabled = True
    #    await self.message.edit(content="Took to long", view=self)

raids = {"Argos":"Argos Abyss Raid", "Valtan":"valtan Legion Raid", "Vykas":"Vykas LEgion Raid", "Kakul-Saydon":"Kakul Legion Raid", "Brelshaza":"Brelshaza Legion Raid"}


class LegionRaidCreation(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    def options():
        list = []
        for raid in raids:
            list.append(discord.SelectOption(label=raid, description=raids[raid]))
        return list

     
    @discord.ui.select(
        placeholder = "Choose a Raid!", 
        min_values = 1, 
        max_values = 1,
        custom_id='raid', 
        options = options()#[ 
            #discord.SelectOption(
            #    label="Kakul-Saydon",
            #    description="Kakul-Saydon Raid "
            #),
            #discord.SelectOption(
            #    label="Brelshaza",
            #    description="Brelshaza raid"
            #),
            #discord.SelectOption(
            #    label="Vykas",
            #    description="Vykas Raid"
            #)

        #]
    )    
    async def selectRaid_callback(self, select, interaction):
        #await interaction.response.send_message(f"Awesome! I like {select.values[0]} too!")
        embed = interaction.message.embeds[0]
        embed.add_field(name=f'Raid: ', value=select.values[0])
        select.placeholder = select.values[0]
        mode = self.get_item('mode')
        mode.disabled = False
        #await interaction.response.send_message(f'du hast {select.values[0]} gewählt', embed=embed, view=self)
        await interaction.response.edit_message(embed=embed, view=self)

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
        select.placeholder = select.values[0]
        createButton  = self.get_item('create')
        createButton.disabled = False
        await interaction.response.edit_message(embed=embed, view=self)
        

    @discord.ui.button(
        label="Create Raid",
        style=discord.ButtonStyle.green,
        row=4,
        custom_id='create',
        disabled=True
    )
    async def button_callback(self, button, interaction):
        #await interaction.response.send_message('du hast den raid erstellt')
        embed = interaction.message.embeds[0]
        chanell = bot.get_channel(interaction.channel_id)
        chanellUser = bot.get_user()
        chanellUser.get_channel()

        print(interaction.user.id)
        #message = await interaction.response.send_message("Raid erstellt")
        raidThread = await chanell.create_thread(name=f"{embed.title}", type=discord.ChannelType.public_thread)
        await interaction.response.send_message('Join the Raid.', embed=embed ,view=JoinRaid(embed, chanell, raidThread))
        #await raidThread.add_user(bot.guild  get_user(interaction.user.id))
        #await raidThread.join()

class JoinRaid(discord.ui.View):

    def __init__(self, embed, channelID, thread):
        super().__init__(timeout=None)
        self.embed = embed
        self.channelID = channelID
        self.thread = thread
        self.dps = 0
        self.supp = 0
        self.embed.add_field(name='DPS: ', value=self.dps)
        self.embed.add_field(name='SUPP: ', value=self.dps)

    @discord.ui.button(
        label='DPS',
        style=discord.ButtonStyle.green,
        custom_id='join_dps'
    )

    async def dps_callback(self, button, interaction):
        print(interaction.user)
        self.dps += 1
        self.embed.add_field(name=f'DPS', value=interaction.user, inline=True)
        await self.thread.join()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(
        label='SUPP',
        style=discord.ButtonStyle.blurple,
        custom_id='join_supp'
    )
    async def supp_callback(self, button, interaction):
        self.supp += 1
        self.embed.add_field(name=f'SUPP', value=interaction.user, inline=True)
        await self.thread.join()
        await interaction.response.edit_message(embed=self.embed, view=self)


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
    panel.add_field(name="Date/Time: ", value=time, inline=True)
    panel.set_author(name=ctx.author)

    await ctx.respond("A wild Raid spawns, come and join", embed=panel, view=LegionRaidCreation())



bot.run(token)