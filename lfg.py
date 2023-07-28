import os
import discord
from discord.ext import commands
import dotenv
from loabot_db import LBDB
import random
from time import sleep

import logging


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formater = logging.Formatter('%(name)s:%(levelname)s: %(msg)s')
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False

#----------------------------------------------------------------------------------------------------------------------------#
raids = {}
#raids = {"Argos":"Argos Abyss Raid, max 8 players", "Valtan":"valtan Legion Raid, max 8 players", "Vykas":"Vykas Legion Raid, max 8 players", "Kakul-Saydon":"Kakul Legion Raid, max 4 players", "Brelshaza Normal":"Brelshaza Legion Raid, max 8 players"}
#modes = {"Argos":["Normal Mode, 1370"], "Valtan":["Normal Mode, 1415", "Hard Mode, 1445"], "Vykas":["Normal Mode, 1430", "Hard Mode, 1460"], "Kakul-Saydon":["Training mode, 1385","Normal Mode, 1475"], "Brelshaza Normal":["Training mode, 1430","Gate 1&2, 1490", "Gate 3&4, 1500", "Gate 5&6, 1520"]}

class LegionRaidCreation(discord.ui.View):

    def __init__(self,db, raids, embed):
        super().__init__(timeout=None)
        self.db = db
        self.raids = raids
        self.modes = {}
        self.selectedRaid = {}
        self.add_item(RaidSelect(self))
        self.embed = embed
        self.thread = None


    def set_modes(self, select, value):
        modes = value.get('modes')
        for mode in modes:
            select.append_option(discord.SelectOption(label=mode))


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
       

    @discord.ui.button(
        label="Create Raid",
        style=discord.ButtonStyle.green,
        row=4,
        custom_id='create',
        disabled=True
    )
    async def button_callback(self, button, interaction):
        embed = interaction.message.embeds[0]
        chanell = interaction.guild.get_channel(interaction.channel.id)
        #self.thread = await chanell.create_thread(name=f"{embed.title}", type=discord.ChannelType.public_thread)
        thread = await chanell.create_thread(name=f"{embed.title}", type=discord.ChannelType.public_thread)
        thread_id = thread.id


        edict = embed.to_dict()
        fields = edict.get('fields')
        print(edict.get('title'), fields[0].get('value'), fields[1].get('value'), fields[2].get('value'))#.get('name'))


        riad_id = self.db.store_group(edict.get('title'), fields[1].get('value'), fields[2].get('value'), thread_id, fields[0].get('value'))
        #edict['title'] = f'{edict.get("title")} '
        logger.info(f"Created Raid: {edict.get('title')}")
        embed.add_field(name='Anzahl DPS: ', value=0)
        embed.add_field(name='Anzahl SUPP: ', value=0)
        embed.add_field(name=chr(173), value=chr(173))
        embed.add_field(name='DPS', value=chr(173))
        embed.add_field(name='SUPP', value=chr(173))
        embed.add_field(name='ID', value=riad_id)
        await chanell.send('A Wild Raid spawns, come and join', embed=embed ,view=JoinRaid(self.db))
        await interaction.response.defer()
        await interaction.delete_original_response()

#TODO joinen funktioniert, leaven hingegn hat manchmal anomalien und löscht falschen benutzer
# have to supbcalss selects for better usability and get acces to user interacting 
# that might help: https://stackoverflow.com/questions/75575015/discord-py-multiple-select-menu-interactions-get-mixed-up
class JoinRaid(discord.ui.View):

    def __init__(self, db):
        super().__init__(timeout=None)
        
        self.dps = 0
        self.supp = 0
        self.selectedChar = ''
        self.dpsvalue = []
        self.suppvalue= []
        self.disabled = True
        self.db = db
        self.user_chars = [] #TODO: clear list after join [x]
        self.parentview = self
        self.thread = None
        self.embed = None
        self.group_id = None

    @discord.ui.button(
        label='join Raid',
        style=discord.ButtonStyle.green,
        custom_id= 'join_button'
    )

    async def join_callback(self, button, interaction):
        user = interaction.user.name
        result = self.db.select_chars(user)
        self.embed = interaction.message.embeds[0]
        edict = self.embed.to_dict()
        fields = edict.get('fields')
        self.group_id = fields[5].get('value') #groupd tabel id
        thread_id = None
        thread = None
        temp_char_list = [{k: item[k] for k in item.keys()} for item in result]
        for d in temp_char_list:
            self.user_chars.append(d.get('char_name'))

        panel = discord.Embed(
            title='Please choose your Character and as which Role you want to join the raid.',
            color=discord.Colour.blue(),
        )

        #self.add_item(CharSelect(self.user_chars))
        chanell = interaction.guild.get_channel(interaction.channel.id)
        allThreads = chanell.threads
        for t in allThreads:
            if t.name == self.embed.title:
                thread_id = t.id
        thread = chanell.get_thread(thread_id)
        message = interaction.message.id
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(ephemeral=True, view=JoinDialogue(self, self.group_id, thread, message), embed=panel)

  
    @discord.ui.button(
        label='leave',
        style=discord.ButtonStyle.red,
        custom_id='leave_thread'
    )


    async def leave_callback(self, button, interaction):
        thread_id = None
        thread = None
        embed = interaction.message.embeds[0]
        count = len(self.suppvalue) + len(self.dpsvalue)

        chanell = interaction.guild.get_channel(interaction.channel.id)
        allThreads = chanell.threads
        for t in allThreads:
            if t.name == embed.title:
                thread_id = t.id

        thread = chanell.get_thread(thread_id)
        threadMeembers = await thread.fetch_members()

        if count <= 1:
            await interaction.response.send_message('you can not leave, try to delete the group instead', ephemeral=True)
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
        embed = interaction.message.embeds[0]
        author = embed.author.name
        embed_dict = embed.to_dict()

        fields = embed_dict.get('fields')

        thread_id = None
        thread = None

        chanell = interaction.guild.get_channel(interaction.channel.id)
        allThreads = chanell.threads
        for t in allThreads:
            if t.name == embed.title:
                thread_id = t.id

        thread = chanell.get_thread(thread_id)

        if str(interaction.user) == author:
            self.db.delete_raids(fields[8].get('value'))
            await thread.delete()
            await interaction.response.defer()
            await interaction.message.delete()

#--------------------- Subclassed view elements -----------------------------------#

class JoinDialogue(discord.ui.View):
    def __init__(self, orgview, group_id, thread, message):
        self.orgview = orgview
        self.user_chars = self.orgview.user_chars
        self.id = group_id
        self.thread = thread
        self.message = message
        super().__init__(
            timeout=120, 
            disable_on_timeout=True
            )
        self.add_item(CharSelect(self.user_chars))

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
        self.view.add_item(JoinButton(selectedChar))          
        await interaction.response.edit_message(view=self.view)

class RaidSelect(discord.ui.Select):
    def __init__(self, parentview) -> None:
        self.parentview = parentview
        def set_options():
            list = []
            #print('legin creation ',self.parentview.raids['Valtan'])
            for key, value in self.parentview.raids.items():
                list.append(discord.SelectOption(label=key, description=value.get('type')))
            return list

        super().__init__(custom_id='raid_selection', placeholder='Choose a Raid', min_values=1, max_values=1, options=set_options(), disabled=False)
    
    async def callback(self, interaction: discord.Interaction):
        self.parentview.embed.add_field(name=f'Raid: ', value=self.values[0], inline=True)
        self.placeholder = self.values[0]
        self.parentview.selectedRaid = self.parentview.raids[self.values[0]]
        self.disabled = True
        self.parentview.add_item(RaidModeSelect(parentview=self.parentview, mode=self.parentview.raids[self.values[0]]))
        await interaction.response.edit_message(view=self.parentview, embed=self.parentview.embed)

class RaidModeSelect(discord.ui.Select):
    def __init__(self, parentview, mode) -> None:
        self.parentview = parentview
        self.mode = mode
        def set_options():
            list = []
            list.append(discord.SelectOption(label='Static', description='For groups with no spcifig raid type (e.g static groups)'))
            for m in self.mode.get('modes'):
                list.append(discord.SelectOption(label=m))
            return list
        
        super().__init__(custom_id='raid_mode', placeholder='Choose the mode of the raid', min_values=1, max_values=1, options=set_options(), disabled=False)
    
    async def callback(self, interaction: discord.Interaction):
        self.parentview.embed.add_field(name=f'Raid Mode: ', value=self.values[0], inline=True)
        self.placeholder = self.values[0]
        createButton  = self.parentview.get_item('create')
        createButton.disabled = False
        self.disabled = True
        await interaction.response.edit_message(view=self.parentview, embed=self.parentview.embed)



class JoinButton(discord.ui.Button):
    def __init__(self, selection):
        self.char = selection

        super().__init__(
            style=discord.ButtonStyle.green, 
            label='DPS', 
            disabled=False, 
            custom_id='join_dps', 
        )
    
    async def callback(self, interaction: discord.Interaction):
        threadMeembers = await self.view.thread.fetch_members()
        char_select = self.view.get_item('character_selection')
        #TODO: access view.orgview and get group id
        if any(m.id == interaction.user.id for m in threadMeembers):
            await interaction.response.send_message('you are already in this group', ephemeral=True)
        else:
            self.view.orgview.dpsvalue.append(f'{self.char} - {interaction.user.name}\n')
            #char_select.placeholder = 'Choose a Character'
            n = ''.join(self.view.orgview.dpsvalue)
            self.view.orgview.embed.set_field_at(3,name='Anzahl DPS:', value=self.view.orgview.dps)
            self.view.orgview.embed.set_field_at(6, name='DPS', value=f"""{n}""")
            #testdict = self.embed.to_dict()
            #print('test dict: ', testdict)
            self.view.orgview.user_chars.clear() #clear list
            await self.view.thread.add_user(interaction.user)
            #self.view.remove_item(char_select)
            #self.view.remove_item(self)
            #await self.view.orgview.message.edit(embed=self.view.orgview.embed, view=self.view.orgview)
            #await self.view.message.edit(embed=self.view.orgview.embed, view=self.view.orgview)
            logger.debug(f'VIEW - {self.view.message}')
            await interaction.response.defer()
            await interaction.delete_original_response()









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
            await interaction.response.send_message('you can not leave, try to delete the group instead', ephemeral=True)
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

class TestView(discord.ui.View):
    def __init__(self,db):
        #self.bot = bot
        self.db = db
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label='Testing',
        style=discord.ButtonStyle.red,
        custom_id='tester'
    )
        
    async def button_callback(self, button, interaction):

        title = random.randint(1,100)
        panel = discord.Embed(
            title=title,
            color=discord.Colour.blue(),
        )
        panel.set_author(name=interaction.user)

        #chanell = self.bot.get_channel(interaction.channel_id)
        chanell = interaction.guild.get_channel(interaction.channel.id)
        msg = await chanell.send('A Test spawns, come and join', embed=panel ,view=TestFollow())
        self.db.add_message(msg.id, chanell.id)
        await interaction.response.send_message("started", delete_after=10)

class TestFollow(discord.ui.View):
    def __init__(self):
        #self.embed = embed
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label='Testing follow',
        style=discord.ButtonStyle.blurple,
        custom_id='tester1'
    )

    async def button_callback(self, button, interaction):
        msg = await interaction.response.send_message(f'Hello {interaction.user}, this is a follow test for {interaction.message.embeds[0].title}')



#----------------------------------------------------------------------------------------------------------------------------#

def set_Raids(db):
        result = db.get_raids()
        raiddicts = [{k: item[k] for k in item.keys()} for item in result]
        for r in raiddicts:
            modes = r.get('modes')
            modearray = modes.split(',')
            rdata = {'type':r.get('type'), 'modes':modearray, 'player':r.get('member')}
            raids[r.get('name')] = rdata
        print('raids dict', raids)
        logger.info('Raids are set')

async def persistent_setup(db, bot):
    result = db.get_messages()
    m_ids = [{k: item[k] for k in item.keys()} for item in result]
    logger.debug(f'Message IDs: {m_ids}')
    
    for id in m_ids:
        m_id = id.get('m_id')
        c_id = id.get('c_id')
        chanell = bot.get_channel(c_id)
        msg = await chanell.fetch_message(m_id)
        #logger.debug(f'Dict mid:   {m_id}')
        #msg = bot.get_message(m_id)
        logger.debug(f'Retrived msg object: {msg}')
        #bot.add_view(view=TestFollow(msg.embeds[0]))#, message_id=msg.id)
    logger.info('Add all persistent views')


def run():

    dotenv.load_dotenv()
    token = str(os.getenv("TOKEN"))
    intents = discord.Intents.all()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    db = LBDB()
    
    #bot.get_message(id)
    
    @bot.event
    async def on_ready():
        logger.info(f"We have logged in as {bot.user}")
        db.setup()
        set_Raids(db)
        bot.add_view(TestView(db))
        bot.add_view(TestFollow())
        bot.add_view(JoinRaid(db))
        #await persistent_setup(db, bot)
        logger.info('Setup in general done')

    
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

        await ctx.respond("A wild Raid spawns, come and join", embed=panel, view=LegionRaidCreation(db, raids, panel), ephemeral=True)
    
    @bot.slash_command(name="db_adduser", description="adds the user to the DB")
    async def db_adduser(ctx):    
        str_res = db.add_user(ctx.author.name)
        await ctx.respond(str_res, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="db_showtable", description="shows alll rows of given table")
    async def db_showtable(ctx, table: discord.Option(str, 'name of the table', required=True)):
        rows = db.show(table)
        dicts = [{k: item[k] for k in item.keys()} for item in rows]
        print(dicts)
        await ctx.respond(f'your table view {dicts}', delete_after=30)
    
    @bot.slash_command(name="db_addchars", description="adds a given char of the user to the DB")
    async def db_addchars(ctx, char: discord.Option(str, 'Charname', required=True), cl: discord.Option(str, 'Charclass', required=True), ilvl: discord.Option(int, 'item level', required=True)):
        result = db.add_chars(char, cl, ctx.author.name, ilvl)
        await ctx.respond(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="db_getchars", description="shows all chars of the user")
    async def db_getchars(ctx, user: discord.Option(str, 'User', required=False)):
        panel = discord.Embed(
            title='Char overview',
            color=discord.Colour.blue(),
        )
        names = []
        classes = []
        ilvl =[]

        if user:
            result = db.get_chars(ctx.author.name)
            chardicts = [{k: item[k] for k in item.keys()} for item in result]
            for c in chardicts:
                names.append(c.get('char_name'))
                classes.append(c.get('class'))
                ilvl.append(c.get('ilvl'))
                
        else:    
            result = db.get_chars(ctx.author.name)
            chardicts = [{k: item[k] for k in item.keys()} for item in result]
            for c in chardicts:
                names.append(c.get('char_name'))
                classes.append(c.get('class'))
                ilvl.append(c.get('ilvl'))

        e_names = "\n".join(str(name) for name in names)
        e_class = "\n".join(str(c) for c in classes)
        e_ilvl = "\n".join(str(lvl) for lvl in ilvl)

        panel.add_field(name='Name', value=e_names)
        panel.add_field(name='Class', value=e_class)
        panel.add_field(name='ilvl', value=e_ilvl)
        await ctx.respond(f'Characters - {ctx.author.name}', embed=panel, ephemeral=False)

    @bot.slash_command(name="db_addraid", description="Adds a new Raid to lfg selection")
    async def db_addraid(ctx, name: discord.Option(str, 'Raidname', required=True), modes: discord.Option(str, 'Modes', required=True), member: discord.Option(int, 'Playercount', required=True), raidtype: discord.Option(str, 'rtype', required=True)):
        #m = json.dumps(modes)
        #print(m)
        db.add_raids(name,modes,member,raidtype)
        await ctx.respond(f'added the new Raid {name}', ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="db_testraid")
    async def db_testraid(ctx):
        rr = {}
        result = db.get_raids()
        raiddicts = [{k: item[k] for k in item.keys()} for item in result]
        for r in raiddicts:
            modes = r.get('modes')
            modearray = modes.split(',')
            rdata = {'type':r.get('type'), 'modes':modearray, 'player':r.get('member')}
            raids[r.get('name')] = rdata
        #print(rr)
        await ctx.respond(f'loaded all raids ', ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="testing")
    async def testing(ctx):
        await ctx.respond('lets go', view=TestView(db))

    @bot.slash_command(name="clear")
    async def clear_messages(ctx, amount:discord.Option(int, 'amount', required=False)):
        if amount:
            #await ctx.channel.purge(limit=amount, bulk=False)
            #await ctx.respond(f'deleted {amount} messages',ephemeral=True, delete_after=10)
            for i in range(0, amount):
                await ctx.channel.purge(limit=5, bulk=False)
                await ctx.respond(f'deleted 4 messages', ephemeral=True, delete_after=10)
                sleep(10)
                
        else:
            await ctx.channel.purge(limit=5, bulk=False)
            await ctx.respond(f'deleted 4 messages', ephemeral=True, delete_after=10)
    
    @bot.slash_command(name="sql")
    async def run_command(ctx, command:discord.Option(str, 'command', required=True)):
        res = db.raw_SQL(command)
        await ctx.respond(res, ephemeral=True, delete_after=20)
            

    
   

    
    bot.run(token)

if __name__=="__main__":
    run()