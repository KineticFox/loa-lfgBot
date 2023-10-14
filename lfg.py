import os
import discord
from discord.components import SelectOption
from discord.enums import ChannelType, ComponentType
from discord.ext import commands
from discord.interactions import Interaction
import dotenv
from loabot_db import LBDB
import json
from time import sleep
import asyncio
import logging
import re


logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formater = logging.Formatter('%(name)s:%(levelname)s: %(msg)s')
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False

#----------------------------------------------------------------------------------------------------------------------------#
raids = {}

class LegionRaidCreation(discord.ui.View):

    def __init__(self,db, raids, embed):
        super().__init__(timeout=None)
        self.db = db
        self.raids = raids
        self.modes = {}
        self.selectedRaid = {}
        self.add_item(RaidType(self))
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
        
        self.db.close()
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

        edict = embed.to_dict()
        fields = edict.get('fields')

        fname = fields[1].get('value')
        fname_lower = fname.lower()

        type_result = self.db.get_raidtype(fname, 'TechKeller')
        type = type_result['type']

        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        #upload image
        if type == 'Guardian':
            result = self.db.get_image_url('default', 'TechKeller')
            url = result['url']
        else:
            result = self.db.get_image_url(fname_lower, 'TechKeller')
            url = result['url']
        
              

        embed.set_thumbnail(url=url)    
        embed.set_field_at(1, name='Raid: ', value=f'{fname} - {type} Raid')   

        logger.info(f"Created Raid: {edict.get('title')}")
        embed.add_field(name='Anzahl DPS: ', value=0)
        embed.add_field(name='Anzahl SUPP: ', value=0)
        embed.add_field(name=chr(173), value=chr(173))
        embed.add_field(name='DPS', value=chr(173))
        embed.add_field(name='SUPP', value=chr(173))
        
        m = await chanell.send('A Wild Raid spawns, come and join', embed=embed ,view=JoinRaid())
        thread = await m.create_thread(name=f"{embed.title}")#, type=discord.ChannelType.public_thread)
        thread_id = thread.id
        
        r_id = self.db.store_group(edict.get('title'), fields[1].get('value'), fields[2].get('value'), fields[0].get('value'), thread_id, guild_name)
        raid_id = r_id['LAST_INSERT_ID()']
        self.db.add_message(m.id, raid_id, guild_name)
        embed.add_field(name='ID', value=raid_id)

        await m.edit(embed=embed ,view=JoinRaid(self.db))
        self.db.close()
        logger.debug(f'stored raid group with ID {raid_id}')
        await interaction.response.defer()
        await interaction.delete_original_response()

class JoinRaid(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        
        self.dps = 0
        self.supp = 0
        self.selectedChar = ''
        self.dpsvalue = []
        self.suppvalue= []
        self.disabled = True
        #self.db = db
        #self.user_chars = [] #TODO: clear list after join [x]
        self.parentview = self
        self.embed = None
        self.group_id = None

    @discord.ui.button(
        label='join Raid',
        style=discord.ButtonStyle.green,
        custom_id= 'join_button'
    )

    async def join_callback(self, button, interaction):
        db = LBDB()
        db.use_db()

        user = interaction.user.name
        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())
        result = db.select_chars(user, guild_name)
        self.embed = interaction.message.embeds[0]
        edict = self.embed.to_dict()
        fields = edict.get('fields')
        group_id = fields[8].get('value') #groupd tabel id
        thread_id = None
        thread = None
        
        #check if user is already connected to this raid id --> raidmember table
        join_check = db.raidmember_check(group_id, interaction.user.name, guild_name)

        if result is None:
            db.close()
            await interaction.response.send_message('Please register your user and chars first!',  ephemeral=True)        
        elif len(result) == 0:
            db.close()
            await interaction.response.send_message('No registered chars found. Please register your chars first!',  ephemeral=True)
        elif join_check is not None:
            db.close()
            char = join_check['char_name']
            await interaction.response.send_message(f'You are already in this raid with {char}', ephemeral=True)
        else:
            panel = discord.Embed(
                title='Please choose your Character and as which Role you want to join the raid.',
                color=discord.Colour.blue(),
            )

            chanell = interaction.guild.get_channel(interaction.channel.id)
            allThreads = chanell.threads
            for t in allThreads:
                if t.name == self.embed.title:
                    thread_id = t.id
            thread = chanell.get_thread(thread_id)
            message = interaction.message.id
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(ephemeral=True, view=JoinDialogue(self, group_id, db,thread, message, user, guild_name), embed=panel)

  
    @discord.ui.button(
        label='leave',
        style=discord.ButtonStyle.red,
        custom_id='leave_thread'
    )


    async def leave_callback(self, button, interaction):
        db = LBDB()
        db.use_db()
        thread_id = None
        thread = None
        count = len(self.suppvalue) + len(self.dpsvalue)
        embed = interaction.message.embeds[0]
        chanell = interaction.guild.get_channel(interaction.channel.id)
        allThreads = chanell.threads
        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        for t in allThreads:
            if t.name == embed.title:
                thread_id = t.id

        thread = chanell.get_thread(thread_id)
        threadMeembers = await thread.fetch_members()

        #get group id
        embed_dict = embed.to_dict()
        fields = embed_dict.get('fields')
        group_id = fields[8].get('value')

        #get char of user
        char_result = db.raidmember_check(group_id, interaction.user.name, guild_name)
        

        #check if user is raid member      

        if char_result is None:
            db.close()
            await interaction.response.send_message('you can not leave, you are not member of the party', ephemeral=True)
        else:
            char = char_result['char_name']
            #get role of user
            role_result = db.get_charRole(char, guild_name)
            role = role_result['role']

            group_result = db.get_group(group_id, guild_name)
            mc = group_result['raid_mc']

            ilvl = db.get_char_ilvl(char, guild_name)
            char_ilvl = ilvl['ilvl']

            if role == 'DPS':
                mc -= 1
                dps_count = fields[3].get('value')
                d_count = int(dps_count) - 1
                db.update_group_mc(group_id, mc, guild_name)
                self.dpsvalue.clear()
                dps_string = fields[6].get('value')

                re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                new_dps_string = re.sub(re_pattern, '', dps_string, 1)
                embed.set_field_at(6, name='DPS', value=new_dps_string)
                embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                db.remove_groupmember(interaction.user.name, group_id, guild_name)

            else:
                mc -= 1
                supp_count = fields[4].get('value')
                s_count = int(supp_count) - 1
                db.update_group_mc(group_id, mc, guild_name)
                self.suppvalue.clear()
                supp_string = fields[7].get('value')
                re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                new_supp_string = re.sub(re_pattern, '', supp_string, 1)

                embed.set_field_at(7, name='SUPP', value=new_supp_string)
                embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)

                db.remove_groupmember(interaction.user.name, group_id, guild_name)

            db.close()
            await interaction.response.edit_message(embed=embed, view=self)
            await thread.remove_user(interaction.user)
                    
    @discord.ui.button(
        label='delete',
        style=discord.ButtonStyle.red,
        custom_id='delete_thread'
    )

    async def delete_callback(self, button, interaction):
        db = LBDB()
        db.use_db()
        embed = interaction.message.embeds[0]
        author = embed.author.name
        embed_dict = embed.to_dict()

        fields = embed_dict.get('fields')

        thread_id = None
        thread = None

        chanell = interaction.guild.get_channel(interaction.channel.id)
        allThreads = chanell.threads

        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        for t in allThreads:
            if t.name == embed.title:
                thread_id = t.id

        thread = chanell.get_thread(thread_id)

        if str(interaction.user) == author:
            db.delete_raids(fields[8].get('value'), guild_name)
            db.close()
            await thread.delete()
            await interaction.response.defer()
            await interaction.message.delete()
        else:
            db.close()
            await interaction.response.send_message('you can not delete the party because you are not the owner', ephemeral=True)

#--------------------- Subclassed view elements -----------------------------------#

class JoinDialogue(discord.ui.View):
    def __init__(self, orgview, db,group_id, thread, message, user_name, guild_name):
        self.orgview = orgview
        self.db = db
        self.user_chars = []
        self.g_id = group_id
        self.thread = thread
        self.message = message
        self.username = user_name
        self.guild_name = guild_name
        def setup_chars():
            result = self.db.select_chars(self.username, self.guild_name)  
            #temp_char_list = [{k: item[k] for k in item.keys()} for item in result]
            for d in result:
                self.user_chars.append(d.get('char_name'))


        setup_chars()
        super().__init__(
            timeout=40, 
            disable_on_timeout=True
            )
        
        self.add_item(CharSelect(self.user_chars, self.db))
    
    

class CharSelect(discord.ui.Select):
    def __init__(self, optionlist, db) -> None:
        self.olist = optionlist
        self.db = db
        def set_options():
            list=[]
            for char in optionlist:
                list.append(discord.SelectOption(label=char))
            return list
    
        super().__init__(custom_id='character_selection', placeholder='Choose your Character', min_values=1, max_values=1, options=set_options(), disabled=False)

    async def callback(self, interaction: discord.Interaction):
        selectedChar = self.values[0]
        self.placeholder = self.values[0]

        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        #get selected char from db for role
        role = self.db.get_charRole(selectedChar, guild_name)
        #get raid id, user id

        #check if user is already connected to this raid id --> raidmember table
        check = self.db.raidmember_check(self.view.g_id, interaction.user.name, guild_name)

        #disable select menu to prevent unintended char switching
        self.disabled = True

        if(check is None):
            self.db.add_groupmember(self.view.g_id, interaction.user.name, selectedChar, guild_name)

            #get mc from raid
            res = self.db.get_group(self.view.g_id, guild_name)
            mc = res['raid_mc']

            #get message id
            message = self.db.get_message(self.view.g_id, guild_name)
            m_id = message['m_id']

            #get char ilvl
            ilvl = self.db.get_char_ilvl(selectedChar, guild_name)
            char_ilvl = ilvl['ilvl']


            e_dict = self.view.orgview.embed.to_dict()
            e_fields = e_dict.get('fields')

            if(role['role'] == 'DPS'):
                #update mc update_group_mc
                mc += 1
                dps_count = e_fields[3].get('value')
                d_count = int(dps_count) + 1
                #self.view.orgview.dpsvalue.append(f'{selectedChar} - {interaction.user.name}\n')
                self.db.update_group_mc(self.view.g_id, mc, guild_name)
                self.view.orgview.embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                dps_string = e_fields[6].get('value')
                new_dps_string = dps_string + f'\n{selectedChar} ({char_ilvl}) - {interaction.user.name}\n'
                self.view.orgview.embed.set_field_at(6, name='DPS', value=new_dps_string)

            else:
                mc += 1
                supp_count = e_fields[4].get('value')
                s_count = int(supp_count) + 1
                self.db.update_group_mc(self.view.g_id, mc, guild_name)
                self.view.orgview.embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)
                supp_string = e_fields[7].get('value')
                new_supp_string = supp_string + f'\n{selectedChar} ({char_ilvl}) - {interaction.user.name}\n'
                self.view.orgview.embed.set_field_at(7, name='SUPP', value=new_supp_string)

            #self.view.orgview.user_chars.clear() #clear list
            self.db.close()
            await self.view.thread.add_user(interaction.user)

            await interaction.response.edit_message(view=self.view)
            channel = interaction.guild.get_channel(interaction.channel.id)
            m = await channel.fetch_message(m_id)
            await m.edit(view=self.view.orgview, embed=self.view.orgview.embed)
            await interaction.delete_original_response()

        else:
            name = check['char_name']
            self.db.close()
            await interaction.response.send_message(f'you are already in this group with {name}', ephemeral=True)

class RaidType(discord.ui.Select):
    def __init__(self, parentview) -> None:
        self.parentview = parentview
        def set_options():
            types = ['Legion', 'Abyssal', 'Guardian']
            list = []
            for t in types:
                list.append(discord.SelectOption(label=t))
            return list
        super().__init__(custom_id='raid_type', placeholder='Choose a Raid Type', min_values=1, max_values=1, options=set_options(), disabled=False)

    async def callback(self, interaction: discord.Interaction):
        r_type = self.values[0]
        self.placeholder = self.values[0]
        self.parentview.add_item(RaidSelect(parentview=self.parentview, raid_type=r_type))
        self.disabled = True
        await interaction.response.edit_message(view=self.parentview, embed=self.parentview.embed)


class RaidSelect(discord.ui.Select):
    def __init__(self, parentview, raid_type) -> None:
        self.parentview = parentview
        self.raid_type= raid_type
        def set_options():
            list = []
            #print('legin creation ',self.parentview.raids['Valtan'])

            for key, value in self.parentview.raids.items():
                if value.get('type') == self.raid_type:
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




#----------------------------------------------------------------------------------------------------------------------------#

classes = []
raid_type = ['Legion', 'Guardian', 'Abyssal']

#---- TODO refactore set_raids for guilds -------#
def set_Raids(db, tables):
        result = db.get_raids('TechKeller')
        for r in result:
            modes = r.get('modes')
            modearray = modes.split(',')
            rdata = {'type':r.get('type'), 'modes':modearray, 'player':r.get('member')}
            raids[r.get('name')] = rdata

        logger.info('Raids are set')

async def raid_list_init(db, context):
    raid_file = open('data/loa_data.json')
    data = json.load(raid_file)

    for i in data['raids']:
        code = db.add_raids(i['name'], i['modes'], i['member'], i['rtype'])
        if code == 0:
            if i['rtype'] == 'Legion' or i['rtype'] == 'Abyssal':
                fname_lower = i['name'].lower()
                file = discord.File(f'ressources/{fname_lower}.png', filename=f'{fname_lower}.png')
                attachment = await context.send('Uploaded image', file=file)
                url = attachment.attachments[0].url
                db.save_image(fname_lower, url)

    raid_file.close()


async def persistent_setup(db, bot):
    result = db.get_messages()
    logger.debug(f'Message IDs: {result}')
    
    for id in result:
        m_id = id.get('m_id')
        c_id = id.get('c_id')
        chanell = bot.get_channel(c_id)
        msg = await chanell.fetch_message(m_id)
        #logger.debug(f'Dict mid:   {m_id}')
        #msg = bot.get_message(m_id)
        logger.debug(f'Retrived msg object: {msg}')
        #bot.add_view(view=TestFollow(msg.embeds[0]))#, message_id=msg.id)
    logger.info('Add all persistent views')

def load_classes():
    class_list = []
    classes_file = open('data/loa_data.json')
    data = json.load(classes_file)

    for i in data['classes']:
        class_list.append(i)

    classes_file.close()
   
    return class_list


def init():
    
    intents = discord.Intents.all()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    db = LBDB()
    return (bot, db)

def stop(bot, db):
    db.close()
    bot.close()

def run(bot, db):
    dotenv.load_dotenv()
    token = str(os.getenv("TOKEN"))
    
    
    @bot.event
    async def on_ready():
        logger.info(f"We have logged in as {bot.user} ")
        guilds = []
        for guild in bot.guilds:
            t = ''.join(l for l in guild.name if l.isalnum())
            guilds.append(t)

        db.setup(guilds)
        set_Raids(db, guilds)
        bot.add_view(JoinRaid())
        #await persistent_setup(db, bot)
        logger.info('Setup in general done')

    
    @bot.slash_command(name = "hi", description = "say hi")
    async def hello(ctx):
        await ctx.respond(f"hello {ctx.user}")

    @bot.slash_command(name="lfg", description="creates a raid")
    async def create_raid(ctx, title: discord.Option(str, 'Choose a title'), date: discord.Option(str, 'When?', required=True)):
        time = date
        db = LBDB()
        db.use_db()

        panel = discord.Embed(
            title=title,
            color=discord.Colour.blue(),
        )
        panel.add_field(name="Date/Time: ", value=time, inline=True)
        panel.set_author(name=ctx.author)

        await ctx.respond("A wild Raid spawns, come and join", embed=panel, view=LegionRaidCreation(db, raids, panel), ephemeral=True)

    
    @bot.slash_command(name="db_showtable", description="shows alll rows of given table")
    async def db_showtable(ctx, table: discord.Option(str, 'name of the table', required=True)):
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        db = LBDB()
        db.use_db()
        rows = db.show(table, tablename)
        #dicts = [{k: item[k] for k in item.keys()} for item in rows]
        #print(dicts)
        db.close()
        await ctx.respond(f'your table view {rows}', delete_after=30)
    
    @bot.slash_command(name="register_char", description="adds a given char of the user to the DB")
    async def db_addchars(ctx, char: discord.Option(str, 'Charname', required=True), cl: discord.Option(str, 'Class', required=True, choices=load_classes()), ilvl: discord.Option(int, 'item level', required=True), role: discord.Option(str, 'Role', required=True, choices=['DPS', 'SUPP'])):
        db = LBDB()
        db.use_db()
        table = ''.join(l for l in ctx.guild.name if l.isalnum())
        result = db.add_chars(char, cl, ctx.author.name, ilvl, role, table)
        db.close()
        await ctx.respond(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="update_char", description="updates the i-lvl of given char in the DB or deletes the given char")
    async def db_updatechars(ctx, charname: discord.Option(str, 'Charname', required=True), ilvl: discord.Option(int, 'ilvl', required=True), delete: discord.Option(str, 'delete', required=False, choices=['yes','no'], default='no')):
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        db = LBDB()
        db.use_db()
        result = db.update_chars(charname, ilvl, delete, tablename)
        db.close()
        await ctx.respond(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="show_chars", description="shows all chars of the user or if no explicit user is given shows your chars")
    async def db_getchars(ctx, user: discord.Option(str, 'User', required=False)):
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        panel = discord.Embed(
            title='Char overview',
            color=discord.Colour.blue(),
        )
        names = []
        classes = []
        ilvl =[]

        db = LBDB()
        db.use_db()

        if user:
            result = db.get_chars(user, tablename)
            #chardicts = [{k: item[k] for k in item.keys()} for item in result]
            for c in result:
                names.append(c.get('char_name'))
                classes.append(c.get('class'))
                ilvl.append(c.get('ilvl'))
            e_names = "\n".join(str(name) for name in names)
            e_class = "\n".join(str(c) for c in classes)
            e_ilvl = "\n".join(str(lvl) for lvl in ilvl)

            panel.add_field(name='Name', value=e_names)
            panel.add_field(name='Class', value=e_class)
            panel.add_field(name='ilvl', value=e_ilvl)
            db.close()
            await ctx.respond(f'Characters - {user}', embed=panel, ephemeral=True)
                
        else:    
            result = db.get_chars(ctx.author.name, tablename)
            #chardicts = [{k: item[k] for k in item.keys()} for item in result]
            for c in result:
                names.append(c.get('char_name'))
                classes.append(c.get('class'))
                ilvl.append(c.get('ilvl'))

            e_names = "\n".join(str(name) for name in names)
            e_class = "\n".join(str(c) for c in classes)
            e_ilvl = "\n".join(str(lvl) for lvl in ilvl)

            panel.add_field(name='Name', value=e_names)
            panel.add_field(name='Class', value=e_class)
            panel.add_field(name='ilvl', value=e_ilvl)
            db.close()
            await ctx.respond(f'Characters - {ctx.author.name}', embed=panel, ephemeral=True)

    @bot.slash_command(name="update_raids", description="Updates Raids")
    async def db_updateraids(ctx):
        db = LBDB()
        db.use_db()
        raid_file = open('data/loa_data.json')
        data = json.load(raid_file)
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())

        for i in data['raids']:
            code = db.add_raids(i['name'], i['modes'], i['member'], i['rtype'], 'TechKeller')
            if code != 0:
                if i['rtype'] == 'Legion' or i['rtype'] == 'Abyssal':
                    fname_lower = i['name'].lower()
                    file = discord.File(f'ressources/{fname_lower}.png', filename=f'{fname_lower}.png')
                    attachment = await ctx.send('Uploaded image', file=file)
                    #await asyncio.sleep(2)
                    url = attachment.attachments[0].url
                    db.save_image(fname_lower, url, 'TechKeller')

        
        url = db.get_image_url('default', 'TechKeller')
        if url is None:
            file = discord.File(f'ressources/loa.png', filename=f'loa.png')
            attachment = await ctx.send('Uploaded image', file=file)
            
            url = attachment.attachments[0].url
            db.save_image('default', url, 'TechKeller')


        raid_file.close()

        await ctx.send(f'added the new Raids', delete_after=20)      
        set_Raids(db, 'TechKeller')
        db.close()
    
    @bot.slash_command(name="upload_image", description="Upload specific raid image")
    async def upload_image(ctx, name:discord.Option(str, 'image name', required=True)):
        file = discord.File(f'ressources/{name}.png', filename=f'{name}.png')
        db = LBDB()
        db.use_db()
        attachment = await ctx.send('Uploaded image', file=file)
        url = attachment.attachments[0].url
        db.save_image(name, url, 'TechKeller')
        db.close()

    @bot.slash_command(name="add_raids", description="Adds a new Raid to lfg selection")
    async def db_addraid(ctx, name: discord.Option(str, 'Raidname', required=True), modes: discord.Option(str, 'Modes', required=True), member: discord.Option(int, 'Playercount', required=True), raidtype: discord.Option(str, 'rtype', choices=raid_type,required=True)):
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        db = LBDB()
        db.use_db()
        db.add_raids(name,modes,member,raidtype, 'TechKeller')

        await ctx.respond(f'added the new Raid {name}', ephemeral=True, delete_after=20)
        
        if raidtype == 'Legion' or raidtype == 'Abyssal':
            fname_lower = name.lower()
            file = discord.File(f'ressources/{fname_lower}.png', filename=f'{fname_lower}.png')
            attachment = await ctx.send('Uploaded image', file=file)
            url = attachment.attachments[0].url
            db.save_image(fname_lower, url, 'TechKeller')

        set_Raids(db)
        db.close()
    
    
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
        if ctx.author.name == 'mr.xilef':
            db = LBDB()
            db.use_db()
            res = db.raw_SQL(command)
            db.close()
            await ctx.respond(res, ephemeral=True, delete_after=20)
        else:
            await ctx.respond(f'tztztz, you are not allowed to use this command', ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="help")
    async def help(ctx):

        text="""
                1. ```/register_user``` -- registers your Discord-User to the Bot and Database\n
                2. ```/register_char``` -- registers one of many of your chars\n
                3. Now you are good to go and you can join and create Groups/Raids\n
                - with ```/show_chars``` you can get an overview of your registered chars\n
                - with ```/lfg``` you create a looking-for-group lobby\n
                """

        embed = discord.Embed(
            title='Help section for loabot',
            color=discord.Colour.dark_orange(),
        )
        embed.add_field(name='User-guide',value=text)

        await ctx.respond('Help section', embed=embed, ephemeral=True, delete_after=120)



    
    bot.run(token)

if __name__=="__main__":
    tuple = init()
    try:
        run(tuple[0], tuple[1])
    except KeyboardInterrupt:
        stop(tuple[0], tuple[1])