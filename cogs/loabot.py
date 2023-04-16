import asyncio
import os
import discord
import dotenv
from discord.ext import commands
from discord.commands import SlashCommand
from loabot_db import LBDB


#bot = discord.Bot()



    #async def on_timeout(self):
    #    for child in self.children:
    #        child.disabled = True
    #    await self.message.edit(content="Took to long", view=self)

raids = {"Argos":"Argos Abyss Raid, max 8 players", "Valtan":"valtan Legion Raid, max 8 players", "Vykas":"Vykas Legion Raid, max 8 players", "Kakul-Saydon":"Kakul Legion Raid, max 4 players", "Brelshaza Normal":"Brelshaza Legion Raid, max 8 players"}
modes = {"Argos":["Normal Mode, 1370"], "Valtan":["Normal Mode, 1415", "Hard Mode, 1445"], "Vykas":["Normal Mode, 1430", "Hard Mode, 1460"], "Kakul-Saydon":["Training mode, 1385","Normal Mode, 1475"], "Brelshaza Normal":["Training mode, 1430","Gate 1&2, 1490", "Gate 3&4, 1500", "Gate 5&6, 1520"]}
chars = ['Artillerist', 'Gunslinger', 'Summoner', 'Berserk', 'Destroyer', 'Paladin', 'Bard', 'Lancemaster', 'Gunlancer', 'Scouter', 'Sorceress']

class LegionRaidCreation(discord.ui.View):

    def __init__(self, bot, db):
        super().__init__(timeout=None)
        self.bot = bot
        self.db = db

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
        #await interaction.message.delete()
        await interaction.response.defer()
        await interaction.delete_original_response()
        

     
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
        chanell = self.bot.get_channel(interaction.channel_id)
        #print(interaction.user.id)
        raidThread = await chanell.create_thread(name=f"{embed.title}", type=discord.ChannelType.public_thread)
        #await raidThread.add_user(interaction.user)
        #await interaction.channel.send('A Wild Raid spawns, come and join', embed=embed ,view=JoinRaid(embed, chanell, raidThread))
        await chanell.send('A Wild Raid spawns, come and join', embed=embed ,view=JoinRaid(embed, chanell, raidThread, self.db))

        await interaction.response.defer()
        await interaction.delete_original_response()

#--------------------- Subclassed view elements -----------------------------------#

class CharSelect(discord.ui.Select):
    def __init__(self, optionlist) -> None:
        self.olist = optionlist
        def set_options():
            list=[]
            for char in optionlist:
                list.append(discord.SelectOption(label=char))
            return list
    
        super().__init__(custom_id='character_selection', placeholder='Choose your Character', min_values=1, max_values=1, options=set_options(), disabled=False)

    async def callback(self, interaction: discord.Interaction):
        selectedChar = self.values[0]
        self.placeholder = self.values[0]
        self.view.add_item(DPSButton(selectedChar))           

        await interaction.response.edit_message(view=self.view)



class DPSButton(discord.ui.Button):
    def __init__(self, selection):
        self.char = selection

        super().__init__(
            style=discord.ButtonStyle.green, 
            label='DPS', 
            disabled=False, 
            custom_id='join_dps', 
        )
    
    async def callback(self, interaction: discord.Interaction):
        threadMeembers = await self.view.orgview.thread.fetch_members()
        char_select = self.view.get_item('character_selection')

        if any(m.id == interaction.user.id for m in threadMeembers):
            await interaction.response.send_message('you are already in this group', ephemeral=True)
        else:
            self.view.orgview.dpsvalue.append(f'{self.char} - {interaction.user.name}\n')
            #char_select.placeholder = 'Choose a Character'
            n = ''.join(self.view.orgview.dpsvalue)
            self.view.orgview.embed.set_field_at(3,name='Anzahl DPS:', value=self.view.orgview.dps)
            self.view.orgview.embed.set_field_at(6, name='DPS', value=f"""{n}""")
            #button.disabled = True
            #supp_button.disabled = True
            #testdict = self.embed.to_dict()
            #print('test dict: ', testdict)
            await self.view.orgview.thread.add_user(interaction.user)
            #self.view.remove_item(char_select)
            #self.view.remove_item(self)
            await self.view.orgview.message.edit(embed=self.view.orgview.embed, view=self.view.orgview)
            await interaction.response.defer()
            await interaction.delete_original_response()

class SUPPButton(discord.ui.Button):
    def __init__(self, selection):
        self.char = selection
        super().__init__(
            style=discord.ButtonStyle.blurple, 
            label = 'SUPP', 
            disabled=False, 
            custom_id='join_supp'
            #,  row
            )
    
    async def callback(self, interaction: discord.Interaction):
        self.view.supp += 1
        threadMeembers = await self.view.orgview.thread.fetch_members()
        char_select = self.view.get_item('character_selection')

        if any(m.id == interaction.user.id for m in threadMeembers):
            await interaction.response.send_message('you are already in this group', ephemeral=True)
        else:
            self.view.orgview.suppvalue.append(f'{self.char} - {interaction.user.name}\n')
            n = ''.join(self.view.orgview.suppvalue)
            self.view.orgview.embed.set_field_at(4,name='Anzahl SUPP:', value=self.view.orgview.supp)
            self.view.orgview.embed.set_field_at(7, name='SUPP', value=f"""{n}""")
            await self.view.orgview.thread.add_user(interaction.user)
            await self.view.orgview.message.edit(embed=self.view.orgview.embed, view=self.view.orgview)
            await interaction.response.defer()
            await interaction.delete_original_response()


class JoinDialogue(discord.ui.View):
    def __init__(self, orgview):
        self.orgview = orgview
        super().__init__(
            timeout=120, 
            disable_on_timeout=True
            )
        self.add_item(CharSelect(self.orgview.user_chars))
    
    @discord.ui.button(
        label='test',
        style=discord.ButtonStyle.green
    )
    async def bcallback(self, button, interaction):
        print(self.orgview.user_chars)

        await interaction.response.edit_message(view=self)
    


#TODO joinen funktioniert, leaven hingegn hat manchmal anomalien und löscht falschen benutzer
# have to supbcalss selects for better usability and get acces to user interacting 
# that might help: https://stackoverflow.com/questions/75575015/discord-py-multiple-select-menu-interactions-get-mixed-up
class JoinRaid(discord.ui.View):

    def __init__(self, embed, channelID, thread, db):
        super().__init__(timeout=None)
        
        self.embed = embed
        self.channelID = channelID
        self.thread = thread
        self.dps = 0
        self.supp = 0
        self.embed.add_field(name='Anzahl DPS: ', value=self.dps)
        self.embed.add_field(name='Anzahl SUPP: ', value=self.dps)
        self.embed.add_field(name=chr(173), value=chr(173))
        self.embed.add_field(name='DPS', value=chr(173))
        self.embed.add_field(name='SUPP', value=chr(173))
        self.selectedChar = ''
        self.dpsvalue = []
        self.suppvalue= []
        self.disabled = True
        self.db = db
        self.user_chars = []

    @discord.ui.button(
        label='join Raid',
        style=discord.ButtonStyle.green,

    )

    async def join_callback(self, button, interaction):
        user = interaction.user.name
        self.user_chars = self.db.select_chars(user)
        #charselect = self.get_item('character')
        #charselect.disabled = False

        panel = discord.Embed(
            title='Please choose ur Character and as which Role you want to join the raid.',
            color=discord.Colour.blue(),
        )


        #self.add_item(CharSelect(self.user_chars))
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(ephemeral=True, view=JoinDialogue(self), embed=panel)


#------------- leave section, embed aktuallisierung macht probleme
#
#{
#    'author': {'name': 'MrXilef#8048'}, 
#    'fields': [
#        {'name': 'Date/Time:', 'value': 'now', 'inline': True}, 
#        {'name': 'Raid:', 'value': 'Brelshaza Normal', 'inline': True}, 
#        {'name': 'Raid Mode:', 'value': 'Gate 1&2, 1490', 'inline': True}, 
#        {'name': 'DPS:', 'value': '1', 'inline': True}, 
#        {'name': 'SUPP: ', 'value': '0', 'inline': True}, 
#        {'name': '\xad', 'value': '\xad', 'inline': True}, 
#        {'name': 'DPS', 'value': 'Destroyer - MrXilef#8048\n', 'inline': True}, 
#        {'name': 'SUPP', 'value': '\xad', 'inline': True}
#    ], 
#    'color': 3447003, 'type': 'rich', 'title': 'test'
#}


  
    @discord.ui.button(
        label='leave',
        style=discord.ButtonStyle.red,
        custom_id='leave_thread'
    )


    async def leave_callback(self, button, interaction):
        threadMeembers = await self.thread.fetch_members()
        count = len(self.suppvalue) + len(self.dpsvalue)
        if count <= 1:
            await interaction.response.send_message('you can not leave, try to delete the group', ephemeral=True)
        else:

            if any(m.id == interaction.user.id for m in threadMeembers):                
                    for dps in self.dpsvalue:
                        if str(interaction.user) in dps:
                            self.dps -=1
                            self.dpsvalue.remove(dps)
                            if len(self.dpsvalue) < 1:
                                self.embed.set_field_at(6, name='DPS', value=chr(173))
                            else:
                                n = ''.join(self.dpsvalue)
                                self.embed.set_field_at(3,name='DPS:', value=self.dps)
                                self.embed.set_field_at(6, name='DPS', value=f"""{n}""")
                            break
                    
                    
                    for supp in self.suppvalue:
                        if str(interaction.user) in supp:
                            self.supp -=1
                            self.suppvalue.remove(supp)
                            if len(self.suppvalue) < 1:
                                self.embed.set_field_at(6, name='SUPP', value=chr(173))
                            else:
                                n = ''.join(self.suppvalue)
                                self.embed.set_field_at(4,name='SUPP:', value=self.supp)
                                self.embed.set_field_at(7, name='SUPP', value=f"""{n}""")
                            break


            await interaction.response.edit_message(embed=self.embed, view=self)
            await self.thread.remove_user(interaction.user)
                    
    @discord.ui.button(
        label='delete',
        style=discord.ButtonStyle.red,
        custom_id='delete_thread'
    )

    async def delete_callback(self, button, interaction):
        author = self.embed.author.name

        if str(interaction.user) == author:
            await self.thread.delete()
            await interaction.response.defer()
            await interaction.message.delete()

#TODO: improve editing of the embed
# --> work with embed.to_dict / embed.from_dict



class loaLFGBot(commands.Cog):

    def __init__(self,bot, db):
        self.bot = bot
        self.db = db

    @commands.slash_command(name = "hi", description = "say hi")
    async def hello(self, ctx):
        await ctx.respond(f"hello {ctx.user}")

    @discord.slash_command(name="lfg", description="creates a raid")
    async def create_raid(self,ctx, title: discord.Option(str, 'Choose a title'), date: discord.Option(str, 'When?', required=True)):
        time = date

        panel = discord.Embed(
            title=title,
            color=discord.Colour.blue(),
        )
        panel.add_field(name="Date/Time: ", value=time, inline=True)
        panel.set_author(name=ctx.author)

        await ctx.respond("A wild Raid spawns, come and join", embed=panel, view=LegionRaidCreation(self.bot, self.db), ephemeral=True)
    
    @discord.slash_command(name="db_adduser", description="adds the user to the DB")
    async def db_adduser(self, ctx):
        print(ctx.author.id)     
        self.db.add_user(ctx.author.name)
    
    @discord.slash_command(name="db_showtable", description="shows alll rows of given table")
    async def db_showtable(self, ctx, table: discord.Option(str, 'name of the table', required=True)):
        print(self.db.show(table))
    
    @discord.slash_command(name="db_addchars", description="adds a given char of the user to the DB")
    async def db_addchars(self, ctx, char: discord.Option(str, 'Charname', required=True), cl: discord.Option(str, 'Charclass', required=True)):
        self.db.add_chars(char, cl, ctx.author.name)
        await ctx.respond('added your char to the DB', ephemeral=True, delete_after=20)
    
    @discord.slash_command(name="db_getchars", description="shows all chars of the user")
    async def db_getchars(self, ctx):
        res = self.db.get_chars(ctx.author.name)
        await ctx.respond(f'Your chars: {res}', ephemeral=True)
    
    

def setup(bot):
    db = LBDB()
    db.setup()
    bot.add_cog(loaLFGBot(bot, db))


#bot.run(token)