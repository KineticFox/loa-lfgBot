import asyncio
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

raids = {"Argos":"Argos Abyss Raid, max 8 players", "Valtan":"valtan Legion Raid, max 8 players", "Vykas":"Vykas Legion Raid, max 8 players", "Kakul-Saydon":"Kakul Legion Raid, max 4 players", "Brelshaza Normal":"Brelshaza Legion Raid, max 8 players"}
modes = {"Argos":["Normal Mode, 1370"], "Valtan":["Normal Mode, 1415", "Hard Mode, 1445"], "Vykas":["Normal Mode, 1430", "Hard Mode, 1460"], "Kakul-Saydon":["Training mode, 1385","Normal Mode, 1475"], "Brelshaza Normal":["Training mode, 1430","Gate 1&2, 1490", "Gate 3&4, 1500", "Gate 5&6, 1520"]}
chars = ['Artillerist', 'Gunslinger', 'Summoner', 'Berserk', 'Destroyer', 'Paladin', 'Bard', 'Lancemaster', 'Gunlancer', 'Scouter', 'Sorceress']

class LegionRaidCreation(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    def options():
        list = []
        for raid in raids:
            list.append(discord.SelectOption(label=raid, description=raids[raid]))
        return list

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red,
        row=4,
        custom_id='cancel',
        disabled=False
    )
    async def buttonCancel_callback(self, button, interaction):
        await interaction.message.delete()
        

     
    @discord.ui.select(
        placeholder = "Choose a Raid!", 
        min_values = 1, 
        max_values = 1,
        custom_id='raid', 
        options = options()
    )    
    async def selectRaid_callback(self, select, interaction):
        embed = interaction.message.embeds[0]
        embed.add_field(name=f'Raid: ', value=select.values[0], inline=True)
        select.placeholder = select.values[0]
        select.disabled = True
        mode = self.get_item('mode')
        mode.disabled = False
        if select.values[0] == "Argos":
            o1 = modes["Argos"]
            mode.append_option(discord.SelectOption(label=o1[0]))
        elif select.values[0] == "Valtan":
            o1 = modes["Valtan"]
            mode.append_option(discord.SelectOption(label=o1[0]))
            mode.append_option(discord.SelectOption(label=o1[1]))
        elif select.values[0] == "Vykas":
            o1 = modes["Vykas"]
            mode.append_option(discord.SelectOption(label=o1[0]))
            mode.append_option(discord.SelectOption(label=o1[1]))
        elif select.values[0] == "Kakul-Saydon":
            o1 = modes["Kakul-Saydon"]
            mode.append_option(discord.SelectOption(label=o1[0]))
            mode.append_option(discord.SelectOption(label=o1[1]))
        elif select.values[0] == "Brelshaza Normal":
            o1 = modes["Brelshaza Normal"]
            mode.append_option(discord.SelectOption(label=o1[0]))
            mode.append_option(discord.SelectOption(label=o1[1]))
            mode.append_option(discord.SelectOption(label=o1[2]))
            mode.append_option(discord.SelectOption(label=o1[3]))
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder = "Choose a Mode!", 
        min_values = 1, 
        max_values = 1,
        disabled=True,
        custom_id='mode', 
        options = [
            discord.SelectOption(
                label="None",
                description="no selection made"
            ), 
        ]
    )    
    async def selectMode_callback(self, select, interaction):
        embed = interaction.message.embeds[0]
        embed.add_field(name=f'Raid Mode: ', value=select.values[0], inline=True)
        select.placeholder = select.values[0]
        createButton  = self.get_item('create')
        createButton.disabled = False
        select.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        

    @discord.ui.button(
        label="Create Raid",
        style=discord.ButtonStyle.green,
        row=4,
        custom_id='create',
        disabled=True
    )
    async def button_callback(self, button, interaction):
        embed = interaction.message.embeds[0]
        chanell = bot.get_channel(interaction.channel_id)
        #print(interaction.user.id)
        raidThread = await chanell.create_thread(name=f"{embed.title}", type=discord.ChannelType.public_thread)
        #await raidThread.add_user(interaction.user)
        await interaction.channel.send('A Wild Raid spawns, come and join', embed=embed ,view=JoinRaid(embed, chanell, raidThread))

        await interaction.response.defer()
        await interaction.delete_original_response()


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
        self.embed.add_field(name=chr(173), value=chr(173))
        self.embed.add_field(name='DPS', value=chr(173))
        self.embed.add_field(name='SUPP', value=chr(173))
        self.selectedChar = ''
        self.dpsvalue = []
        self.suppvalue= []
        self.disabled = True
            

    def chars():
        list = []
        for char in chars:
            list.append(discord.SelectOption(label=char))
        return list

    @discord.ui.select(
        placeholder = "Choose a Character", 
        min_values = 1, 
        max_values = 1,
        custom_id='character', 
        options = chars()
    )

    async def char_callback(self, select, interaction):
       self.selectedChar = select.values[0]
       #select.disabled = True
       select.placeholder = select.values[0]
       dps_button = self.get_item('join_dps')
       supp_button = self.get_item('join_supp')
       dps_button.disabled = False
       supp_button.disabled = False
       await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label='DPS',
        style=discord.ButtonStyle.green,
        custom_id='join_dps',
        disabled=True
    )

    async def dps_callback(self, button, interaction):
        #print(interaction.user)
        self.dps += 1
        
        threadMeembers = await self.thread.fetch_members()
        for m in threadMeembers:
            if interaction.user.id == m.id:
                await interaction.response.send_message('you are already in this group', ephemeral=True)
            else:
                self.dpsvalue.append(f'{self.selectedChar} - {interaction.user}\n')
                n = ''.join(self.dpsvalue)
                self.embed.set_field_at(3,name='DPS:', value=self.dps)
                self.embed.set_field_at(6, name='DPS', value=f"""{n}""")
                await self.thread.add_user(interaction.user)
                await interaction.response.edit_message(embed=self.embed, view=self)


    @discord.ui.button(
        label='SUPP',
        style=discord.ButtonStyle.blurple,
        custom_id='join_supp',
        disabled=True
    )
    async def supp_callback(self, button, interaction):
        self.supp += 1
        threadMeembers = await self.thread.fetch_members()
        for m in threadMeembers:
            if interaction.user.id == m.id:
                await interaction.response.send_message('you are already in this group', ephemeral=True)
            else:
                self.suppvalue.append(f'{self.selectedChar} - {interaction.user}\n')
                n = ''.join(self.suppvalue)
                self.embed.set_field_at(4,name='SUPP:', value=self.supp)
                self.embed.set_field_at(7, name='SUPP', value=f"""{n}""")
                await self.thread.add_user(interaction.user)
                await interaction.response.edit_message(embed=self.embed, view=self)
    
    @discord.ui.button(
        label='leave',
        style=discord.ButtonStyle.red,
        custom_id='leave_thread'
    )

    async def leave_callback(self, button, interaction):
        threadMeembers = await self.thread.fetch_members()
        for m in threadMeembers:
            if interaction.user.id == m.id:
                for dps in self.dpsvalue:
                    if str(interaction.user) in dps:
                        self.dps -=1
                        self.dpsvalue.remove(dps)
                        n = ''.join(self.dpsvalue)
                        self.embed.set_field_at(3,name='DPS:', value=self.dps)
                        self.embed.set_field_at(6, name='DPS', value=f"""{n}""")
                    else:
                        print(f'nope not in {dps}')
                
                for supp in self.suppvalue:
                    if str(interaction.user) in supp:
                        self.supp -=1
                        self.suppvalue.remove(supp)
                        n = ''.join(self.suppvalue)
                        self.embed.set_field_at(3,name='SUPP:', value=self.supp)
                        self.embed.set_field_at(7, name='SUPP', value=f"""{n}""")
                    else:
                        print(f'nope not in {supp}')

                await interaction.response.edit_message(embed=self.embed, view=self)
                await self.thread.remove_user(interaction.user)
                
                #self.embed
                #await interaction.response.edit_message(embed=self.embed, view=self)






@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.slash_command(name = "hi", description = "say hi")
async def hello(ctx):
    await ctx.respond(f"hello {ctx.user}")

@bot.slash_command(name="lfg", description="creates a raid")
async def create_raid(ctx, title: discord.Option(str, 'Choose a title'), date: discord.Option(str, 'When?', required=True)):
    time = date

    panel = discord.Embed(
        title=title,
        color=discord.Colour.blue(),
    )
    panel.add_field(name="Date/Time: ", value=time, inline=True)
    panel.set_author(name=ctx.author)

    await ctx.respond("A wild Raid spawns, come and join", embed=panel, view=LegionRaidCreation(), ephemeral=True)



bot.run(token)