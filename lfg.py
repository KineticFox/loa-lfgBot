import os
import discord
from discord.components import SelectOption
from discord.enums import ChannelType, ComponentType
from discord.ext import commands
from discord.interactions import Interaction
from discord.ui.input_text import InputText
from discord.ui.item import Item
from discord.ui import Button
import dotenv
from loabot_db import LBDB
import json
from time import sleep
import asyncio
import logging
import re
import time
import requests
from datetime import datetime
from loabot_modals import DateModal
from loabot_views import *
import random



logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formater = logging.Formatter('%(asctime)s - %(levelname)s %(name)s:%(msg)s', '%y-%m-%d, %H:%M')
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False

#----------------------------------------------------------------------------------------------------------------------------#
raids = {}

class RaidOverview(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.cooldown = commands.CooldownMapping.from_cooldown(1, 120, commands.BucketType.member)


    @discord.ui.button(
        label='Update',
        style=discord.ButtonStyle.green,
        custom_id='update_overview'

    )
    async def callback(self, button, interaction):
        await interaction.response.defer()

        bucket = self.cooldown.get_bucket(interaction.message)
        retry = bucket.update_rate_limit()
        if retry:
            return await interaction.followup.send(f'Try again in {round(retry, 1)} seconds', ephemeral=True)

        db = LBDB()
        db.use_db()
        tablename = ''.join(l for l in interaction.guild.name if l.isalnum())

        groups_list = db.get_group_overview(tablename)
        db.close()
        
        raid = []
        mode = []
        threads  = []
        membercount = []
        title = []
        embed = interaction.message.embeds[0]

        length_check = False
        embed_length= len(embed.description)

        for g in groups_list:
            membercount.append(g.get("raid_mc"))
            raid.append(f'{g.get("raid")}')
            m = g.get('raid_mode')
            mode.append(m.split(' ')[0])
            thread = await interaction.guild.fetch_channel(g.get('dc_id'))
            channel_id = thread.parent_id
            channel = await interaction.guild.fetch_channel(channel_id)            
            message = await channel.fetch_message(g.get('dc_id'))
            url = message.jump_url
            threads.append(url)
            new_length = len(threads) + embed_length
            if new_length >= 3900:
                length_check = True
            
            title.append(g.get('raid_title'))

        
        time = datetime.now()
        current_time = time.strftime("%H:%M:%S")

        if length_check:
            embed.add_field(name='Achtung', value='Aktuell gibt es zu viele offene Raids um alle anzuzeigen.')
            embed.set_footer(text=f'last updated at: {current_time}')
            await interaction.message.edit(embed=embed, view=self)
        
        else:

            text_list = [f'**Raidübersicht für {tablename}:**']
                    
            for i in range(len(threads)):
                text_list.append(f'**Thread**: {threads[i]}\t\t**Raid**: {raid[i]}\t\t**Mitglieder**: {membercount[i]}\t\t**Mode**: {mode[i]}')
            
            text = "\n".join(t for t in text_list) 

            embed.description=text      
            embed.set_footer(text=f'last updated at: {current_time}')
            await interaction.message.edit(embed=embed, view=self)

        


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
        await interaction.response.defer()
        self.db.close()
        
        await interaction.delete_original_response()
       

    @discord.ui.button(
        label="Create Raid",
        style=discord.ButtonStyle.green,
        row=4,
        custom_id='create',
        disabled=True
    )
    async def button_callback(self, button, interaction):
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        chanell = {}

        #await interaction.response.defer(ephemeral=True)

        if interaction.guild.get_channel(interaction.channel.id) is None:
            chanell = await interaction.guild.fetch_channel(interaction.channel.id)
        else:
            chanell = interaction.guild.get_channel(interaction.channel.id)

        edict = embed.to_dict()
        fields = edict.get('fields')

        fname = fields[1].get('value')
        fname_lower = fname.lower()

        type_result = self.db.get_raidtype(fname, 'TechKeller')
        type = type_result['type']

        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        custom = fname_lower.split(' ')[0]

        #upload image
        if type == 'Guardian' or custom == 'custom':
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
        
        try:
            m = await chanell.send('A Wild Raid spawns, come and join', embed=embed)
            thread = await m.create_thread(name=f"{embed.title}")
            thread_id = thread.id        
            

        except Exception as e:
            await interaction_handling_defer(interaction, e)
            await interaction.delete_original_response()
        
        else:
            r_id = self.db.store_group(edict.get('title'), fields[1].get('value'), fields[2].get('value'), fields[0].get('value'), thread_id, guild_name)

        if r_id is None or len(r_id) == 0:
            self.db.close()
            logger.warning(f'Raid creation failed for {interaction.user.name}')
            await interaction.followup.send('Something went wrong!')
            await m.delete()
            await thread.delete()   
        else:             
            raid_id = r_id['LAST_INSERT_ID()']
            self.db.add_message(m.id, raid_id, guild_name)
            embed.add_field(name='ID', value=raid_id)
            #await interaction.response.defer()
            await interaction.delete_original_response()
            await m.edit(embed=embed ,view=JoinRaid())
            self.db.close()
            logger.debug(f'stored raid group with ID {raid_id}')
    


#TODO: add exception handling from here on         


class JoinRaid(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        
        self.dps = 0
        self.supp = 0
        self.selectedChar = ''
        self.dpsvalue = []
        self.suppvalue= []
        #self.disabled = True
        self.parentview = self
        self.embed = None
        self.group_id = None
        #self.message = message
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 10, commands.BucketType.member)

    @discord.ui.button(
        label='Join raid',
        style=discord.ButtonStyle.green,
        custom_id= 'join_button'
    )

    async def join_callback(self, button, interaction):

        await interaction.response.defer()

        bucket = self.cooldown.get_bucket(interaction.message)
        retry = bucket.update_rate_limit()
        if retry:
            return await interaction.followup.send(f'Try again in {round(retry, 1)} seconds', ephemeral=True)
        else:    

            m_id = interaction.message.id
            c_id = interaction.channel.id
            user = interaction.user.name
            member = interaction.guild.get_member_named(user)
            u_id = member.id  
            embed = interaction.message.embeds[0]
            self.embed = embed
            db = LBDB()
            db.use_db()

            guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

            result = db.select_chars(u_id, guild_name)
            edict = embed.to_dict()
            fields = edict.get('fields')
            group_id = fields[8].get('value') #groupd tabel id
            thread_id = None
            thread = None
            raid = fields[1].get('value')
            raidname = raid.split(' -')[0]

            res = db.get_raid_mc(raidname)
            mc = res['member']

            g_res= db.get_group(group_id, guild_name)
            g_mc = g_res['raid_mc']

            
            #check if user is already connected to this raid id --> raidmember table
            join_check = db.raidmember_check(group_id, u_id, guild_name)
            

            if result is None:
                db.close()
                await interaction.followup.send(f'{interaction.user.mention} Please register your user and chars first! / Bitte erstelle zuerst einen Charakter!', ephemeral=True)
            elif len(result) == 0:
                db.close()
                await interaction.followup.send(f'{interaction.user.mention} No registered chars found. Please register your chars first! / Kein Charakter von dir gefunden, bitte erstelle zuerst einen Charakter',  ephemeral=True)
            elif join_check is not None:
                char = join_check['char_name']
                panel = discord.Embed(
                    title='Edit your char / Bearbeite deinen Charakter',
                    color=discord.Colour.blue(),
                )
                panel.add_field(name=chr(173), value=f'Wähle {char} erneut um sein ilvl zu erneurern oder wähle einen anderen char.')
                await interaction.message.edit(view=self)# new to disable button
                chanell = await interaction.guild.fetch_channel(c_id)
                thread = chanell.get_thread(m_id)
                update = True
                await interaction.followup.send(f'{interaction.user.mention}',ephemeral=True, view=JoinDialogue(self, db, group_id, thread, m_id, u_id, guild_name, chanell, old_char=char), embed=panel)
            elif g_mc >= mc:
                db.close()
                await interaction.followup.send(f'{interaction.user.mention} This group has the max member count reached / Diese Gruppe hat die maximale Mitgliederanzahl erreicht', ephemeral=True)
            else:
                panel = discord.Embed(
                    title='Please choose your Character / Bitte wähle deinen Charakter',
                    color=discord.Colour.blue(),
                )
                update = False
                await interaction.message.edit(view=self)# new to disable button
                chanell = await interaction.guild.fetch_channel(c_id)
                thread = chanell.get_thread(m_id)
                await interaction.followup.send(f'{interaction.user.mention}',ephemeral=True, view=JoinDialogue(self, db, group_id, thread, m_id, u_id, guild_name, chanell, old_char=None), embed=panel)
                




    @discord.ui.button(
            label='Kick member',
            style=discord.ButtonStyle.danger,
            custom_id='kick_m'
    )

    async def kick_callback(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        user_list = []
        embed = interaction.message.embeds[0]
        author = embed.author.name
        embed_dict = embed.to_dict()

        

        if interaction.user.name != author:
            await interaction.followup.send('You are not party leader/ Du bist nicht der Partyleiter!!', ephemeral=True)
        else:
            fields = embed_dict.get('fields')

            thread_id = None
            thread = None

            chanell = {}
            if interaction.guild.get_channel(interaction.channel.id) is None:
                chanell = await interaction.guild.fetch_channel(interaction.channel.id)
            else:
                chanell = interaction.guild.get_channel(interaction.channel.id)
            thread = chanell.get_thread(interaction.message.id)
            t_member = await thread.fetch_members()

            for m in t_member:
                member = await interaction.guild.fetch_member(m.id)
                if member.name == 'loaBot' or member.name == interaction.user.name or member.name == 'loabot-test':
                    continue
                else:
                    user_list.append(member)
            if len(user_list) == 0:
                await interaction.followup.send('No users to kick in this thread / Es sind keine User in der Gruppe', ephemeral=True)
            else:
                await interaction.followup.send(ephemeral=True, view=KickView(user_list, thread, self), embed=embed)
  
    @discord.ui.button(
        label='Leave',
        style=discord.ButtonStyle.blurple,
        custom_id='leave_thread'
    )


    async def leave_callback(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        db = LBDB()
        db.use_db()
        thread_id = None
        thread = None
        count = len(self.suppvalue) + len(self.dpsvalue)
        embed = interaction.message.embeds[0]
        chanell = {}
        if interaction.guild.get_channel(interaction.channel.id) is None:
            chanell = await interaction.guild.fetch_channel(interaction.channel.id)
        else:
            chanell = interaction.guild.get_channel(interaction.channel.id)
        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        member = interaction.guild.get_member_named(interaction.user.name)
        u_id = member.id 

        thread = chanell.get_thread(interaction.message.id)
        threadMeembers = await thread.fetch_members()

        #get group id
        embed_dict = embed.to_dict()
        fields = embed_dict.get('fields')
        group_id = fields[8].get('value')

        #get char of user
        char_result = db.raidmember_check(group_id, u_id, guild_name)
        
        #check if user is raid member 

        group_result = db.get_group(group_id, guild_name)
        mc = group_result['raid_mc']

        if mc <= 1:
            db.close()
            await interaction.followup.send('You can not leave please delete group / Du kannst die gruppe nicht verlassen bitte lösche die Gruppe', ephemeral=True)
        elif char_result is None:
            db.close()
            await interaction.followup.send('You can not leave, you are not member of the party / Du bist kein Mitglied der Gruppe', ephemeral=True)
        else:
            char = char_result['char_name']
            #get role of user
            clean_char_name = char.split(' ')[0]
            role_result = db.get_charRole(clean_char_name, guild_name)
            role = role_result['role']

            

            ilvl = db.get_char_ilvl(clean_char_name, guild_name)
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
                db.remove_groupmember(u_id, group_id, guild_name)

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

                db.remove_groupmember(u_id, group_id, guild_name)

            if embed.author.name == interaction.user.name:
                
                db_user_id = db.get_raidmember(group_id, guild_name)['user_id']
                db_user_name = db.get_username(db_user_id, guild_name)['name']

                embed.set_author(name=db_user_name)
                db.close()
                try:
                    await interaction.message.edit(embed=embed, view=self)
                    await thread.remove_user(interaction.user)
                except discord.errors as e:
                    logger.warning(f'DC Error in leave callback- {e}')
                    await interaction.followup.send('Something went wrong, try again or seek for help / Etwas ist schiefgelaufen, probiere es nochmal oder frag nach Hilfe', ephemeral=True)
            else:
                db.close()
                try:
                    #await interaction.response.edit_message(embed=embed, view=self)
                    await interaction.message.edit(embed=embed, view=self)
                    await thread.remove_user(interaction.user)
                except discord.errors as e:
                    logger.warning(f'DC Error in leave callback - {e}')
                    await interaction.followup.send('Something went wrong, try again or seek for help / Etwas ist schiefgelaufen, probiere es nochmal oder frag nach Hilfe', ephemeral=True) 
                    
    @discord.ui.button(
        label='Delete',
        style=discord.ButtonStyle.red,
        custom_id='delete_thread'
    )

    async def delete_callback(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        db = LBDB()
        db.use_db()
        embed = interaction.message.embeds[0]
        author = embed.author.name
        embed_dict = embed.to_dict()

        fields = embed_dict.get('fields')

        thread_id = None
        thread = None
        
        #admin_role = discord.utils.get(await interaction.guild.fetch_roles(), name='Dev')
        admin_role_id = 1006783350188560416

        chanell = {}
        if interaction.guild.get_channel(interaction.channel.id) is None:
            chanell = await interaction.guild.fetch_channel(interaction.channel.id)
        else:
            chanell = interaction.guild.get_channel(interaction.channel.id)

        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        thread = chanell.get_thread(interaction.message.id)

        if interaction.user.name == author:
            db.delete_raids(fields[8].get('value'), guild_name)
            db.close()
            await thread.delete()
            
            await interaction.message.delete()
        elif interaction.user.get_role(admin_role_id):
            db.delete_raids(fields[8].get('value'), guild_name)
            db.close()
            await thread.delete()
            
            await interaction.message.delete()
        else:
            db.close()
            await interaction.followup.send('you can not delete the party because you are not the owner / Du kannst die Gruppe nicht löschen, da du nicht der Leiter bist.', ephemeral=True)

    @discord.ui.button(
        label='Edit Date/time',
        style=discord.ButtonStyle.blurple,
        custom_id= 'date_button'
    )

    async def date_callback(self, button , interaction):
        #await interaction.response.defer()

        embed = interaction.message.embeds[0]
        author = embed.author.name

        if interaction.user.name == author:
            await interaction.response.send_modal(DateModal(title='Datum ändern',view=self))
        else:
            await interaction.response.send_message('You are not the Raidleader / Du bist nicht der Raidanführer!', ephemeral=True) 

        

#--------------------- Subclassed view elements -----------------------------------#

class JoinDialogue(discord.ui.View):
    def __init__(self, orgview, db,group_id, thread, message, user_id, guild_name, channel, old_char, timeout=20):
        self.orgview = orgview
        self.db = db
        self.user_chars = []
        self.g_id = group_id
        self.thread = thread
        self.message = message
        self.m = message
        self.user_id = user_id
        self.guild_name = guild_name
        self.channel = channel
        self.old_char = old_char
        def setup_chars():
            result = self.db.select_chars(self.user_id, self.guild_name)  

            for d in result:
                self.user_chars.append(f'{d.get("char_name")} {d.get("emoji")}')


        setup_chars()
        super().__init__(
            timeout=timeout, 
            #disable_on_timeout=True
            )
        
        self.add_item(CharSelect(self.user_chars, self.db, self.orgview))

    async def on_timeout(self):
        m = await self.channel.fetch_message(self.m)
        await m.edit(view=self.orgview, embed=self.orgview.embed)
        self.clear_items()
        self.stop()

class KickView(discord.ui.View):
    def __init__(self, memberlist, thread, orgview):
        self.mlist = memberlist
        self.thread = thread
        self.orgview = orgview
        super().__init__(timeout=40, disable_on_timeout=True)

        self.add_item(KickDialogue(self.mlist, self.thread))

#KickDialogue


    


#Charselect

            
#RaidType


#RaidSelect

#RaidModeSelect
        
class RemoteAddView(discord.ui.View):
    def __init__(self, user, table, channel, raid, chars, db):
        self.user = user
        self.table = table
        self.channel = channel
        self.raid_id = raid
        self.optionlist = chars
        self.db = db

        super().__init__(timeout=180, disable_on_timeout=True)
        self.add_item(RemoteCharSelect(self.optionlist, self.db, self.user, self.table, self.raid_id, self.channel))





#-------------------------------------------------------- Commands --------------------------------------------------------------------#

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

"""
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
"""

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
    bot = commands.Bot(command_prefix='!', intents=intents, owner_id=469479291147517952)
    return bot

def stop(bot):
    bot.close()

def run(bot):
    dotenv.load_dotenv()
    token = str(os.getenv("TOKEN"))

    

    @bot.command()
    @commands.is_owner()
    async def load_cog(ctx, cog):
        bot.load_extension(f'cogs.{cog}')

        if  cog == 'orga':
            welcome = bot.get_cog('MemberManagement')
            await welcome.setupGuild()
        
        await bot.register_commands()
        #await bot.sync_commands()
        
        await ctx.send(f'loaded {cog} cog', delete_after=10)

    
    @bot.command()
    @commands.is_owner()
    async def reload_cog(ctx, cog):

        bot.reload_extension(f'cogs.{cog}')

        if  cog == 'orga':
            welcome = bot.get_cog('WelcomeSetup')
            await welcome.setupGuild()
        
        #await bot.sync_commands()
        await ctx.send(f'reloaded {cog} cog', delete_after=10)

    
    @bot.command()
    @commands.is_owner()
    async def unload_cog(ctx, cog):
        bot.unload_extension(f'cogs.{cog}')

    
    
    @bot.event
    async def on_ready():
        logger.info(f"We have logged in as {bot.user} ")
        guilds = []
        db = LBDB()
        for guild in bot.guilds:
            t = ''.join(l for l in guild.name if l.isalnum())
            guilds.append(t)
        
        db.setup(guilds)
        set_Raids(db, guilds)
        bot.add_view(JoinRaid())
        bot.add_view(RaidOverview())
        db.close()
        logger.info('Setup in general done')

    
    @bot.slash_command(name = "hi", description = "say hi")
    @commands.is_owner()
    @discord.guild_only()
    async def hello(ctx):
        await ctx.respond(f"hello {ctx.user}")

    @bot.slash_command(name="lfg", description="creates a raid, no emojis allowed in title / Erstellt eine lfg-Party, keine emojis erlaubt.")
    @discord.guild_only()
    async def create_raid(ctx, title: discord.Option(str, 'Choose a title', max_length=70), date: discord.Option(str, 'Date + time or short text', required=True, max_length=40)): # type: ignore
        time = date
        #await ctx.defer(ephemeral=True)
        db = LBDB()
        db.use_db()

        panel = discord.Embed(
            title=title,
            color=discord.Colour.blue(),
        )
        name = ctx.author.name
        clean_name = name.split('#')[0]
        panel.add_field(name="Date/Time: ", value=time, inline=True)
        panel.set_author(name=clean_name)

        await ctx.respond("A wild raid spawns, come and join", embed=panel, view=LegionRaidCreation(db, raids, panel), ephemeral=True)

    
    # @bot.slash_command(name="register_char", description="Adds a given char of the user to the DB / Fügt für deinen Benutzer einen Charakter hinzu")
    # async def db_addchars(ctx, char: discord.Option(str, 'Charname', required=True, max_length=69), cl: discord.Option(str, 'Class', required=True, choices=load_classes()), ilvl: discord.Option(int, 'item level', required=True), role: discord.Option(str, 'Role', required=True, choices=['DD', 'SUPP'])): # type: ignore
    #     await ctx.defer(ephemeral=True)
    #     db = LBDB()
    #     db.use_db()
    #     member = ctx.guild.get_member_named(ctx.author.name)
    #     u_id = member.id
        
    #     classes_file = open('data/loa_data.json')
    #     data = json.load(classes_file)
        
    #     emoji = ''

    #     for i in data['emojis']:
    #         res = re.search('<:(.*):',i)
    #         e = res.group(1)
    #         if cl.lower() == e:
    #             emoji = i
    #         elif e == 'artistt' and cl.lower() == 'artist':
    #             emoji = i


    #     classes_file.close()

    #     if role == 'DD':
    #         role = 'DPS'

    #     table = ''.join(l for l in ctx.guild.name if l.isalnum())
    #     result = db.add_chars(char, cl, ctx.author.name, ilvl, role, table, u_id, emoji)
    #     db.close()
    #     await ctx.respond(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="update_char", description="Updates the i-lvl of given char or deletes it / Ändert das i-lvl des Charakters oder löscht ihn")
    @discord.guild_only()
    async def db_updatechars(ctx, charname: discord.Option(str, 'Charname', required=True, max_length=69), ilvl: discord.Option(int, 'ilvl', required=True), delete: discord.Option(str, 'delete', required=False, choices=['yes','no'], default='no')): # type: ignore
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        await ctx.defer(ephemeral=True)
        
        db = LBDB()
        db.use_db()
        user_id = ctx.user.id
        result = db.update_chars(charname, ilvl, delete, tablename, user_id)
        db.close()
        await ctx.send_followup(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="show_chars", description="Shows all chars of the user / Zeigt alle Charaktere des Spielers an")
    @discord.guild_only()
    async def db_getchars(ctx, user: discord.Member = None):
        await ctx.defer(ephemeral=True)
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

        if user is not None:
            raw_user = user.name
            username = raw_user.split('#')[0]
            member = ctx.guild.get_member_named(username)
            u_id = member.id
            result = db.get_chars(u_id, tablename)
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
            await ctx.followup.send(f'Characters - {username}', embed=panel, ephemeral=True)
                
        else:
            member = ctx.guild.get_member_named(ctx.author.name)
            u_id = member.id    
            result = db.get_chars(u_id, tablename)
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
            await ctx.followup.send(f'Characters - {ctx.author.name}', embed=panel, ephemeral=True)

    @bot.slash_command(name="update_raids", description="Updates Raids")
    @discord.guild_only()
    async def db_updateraids(ctx):
        await ctx.defer()
        db = LBDB()
        db.use_db()
        raid_file = open('data/loa_data.json')
        data = json.load(raid_file)
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())

        url = db.get_image_url('default', 'TechKeller')
        if url is None:
            file = discord.File(f'ressources/loa.png', filename=f'loa.png')
            attachment = await ctx.followup.send('Uploaded image', file=file)
            
            url = attachment.attachments[0].url
            db.save_image('default', url, 'TechKeller')

        for i in data['raids']:
            code = db.add_raids(i['name'], i['modes'], i['member'], i['rtype'], 'TechKeller')
            if code != 0:
                if i['rtype'] == 'Legion' or i['rtype'] == 'Abyssal':
                    fname_lower = i['name'].lower()
                    custom = fname_lower.split(' ')[0]
                    if custom == 'custom':
                        continue
                    file = discord.File(f'ressources/{fname_lower}.png', filename=f'{fname_lower}.png')
                    attachment = await ctx.followup.send('Uploaded image', file=file)
                    #await asyncio.sleep(2)
                    url = attachment.attachments[0].url
                    db.save_image(fname_lower, url, 'TechKeller')
                


        
        


        raid_file.close()

        await ctx.followup.send(f'added the new Raids', delete_after=20)      
        set_Raids(db, 'TechKeller')
        db.close()
    
    @bot.slash_command(name="upload_image", description="Upload specific raid image")
    @discord.guild_only()
    async def upload_image(ctx, name:discord.Option(str, 'image name', required=True)): # type: ignore
        file = discord.File(f'ressources/{name}.png', filename=f'{name}.png')
        db = LBDB()
        db.use_db()
        attachment = await ctx.send('Uploaded image', file=file)
        url = attachment.attachments[0].url
        db.save_image(name, url, 'TechKeller')
        db.close()

    @bot.slash_command(name="add_raids", description="Adds a new Raid to lfg selection")
    @discord.guild_only()
    async def db_addraid(ctx, name: discord.Option(str, 'Raidname', required=True), modes: discord.Option(str, 'Modes', required=True), member: discord.Option(int, 'Playercount', required=True), raidtype: discord.Option(str, 'rtype', choices=raid_type,required=True)): # type: ignore
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
    @discord.guild_only()
    async def clear_messages(ctx, amount:discord.Option(int, 'amount', required=False)): # type: ignore
        await ctx.defer(ephemeral=True)
        if amount:
            await ctx.channel.purge(limit=amount, bulk=False)
            await ctx.followup.send(f'deleted {amount} messages', ephemeral=True, delete_after=10)
                
        else:
            await ctx.channel.purge(limit=1, bulk=False)
            await ctx.respond(f'deleted 4 messages', ephemeral=True, delete_after=10)
    
    @bot.slash_command(name="sql")
    @discord.guild_only()
    @commands.is_owner()
    async def run_command(ctx, command:discord.Option(str, 'command', required=True)): # type: ignore
        db = LBDB()
        db.use_db()
        res = db.raw_SQL(command)
        db.close()
        await ctx.respond(res, ephemeral=True, delete_after=20)
        
    
    @bot.slash_command(name="help")
    async def help(ctx):

        text="""
                1. ```/register_char``` -- registers one of many of your chars/registriert einen von vielen deiner chars\n
                2. Now you are good to go and you can join and create Groups/Raids / Jetzt kannst du Gruppen beitreten und erstellen\n
                - with ```/show_chars``` you can get an overview of your registered chars / zeigt eine Übersicht deiner Chars an\n
                - with ```/lfg``` you create a looking-for-group lobby / Befehl um Gruppen zu erstellen\n
                - with ```/my_raids``` you get an overview of raids you participate in / Zeigt übersicht der raids in denen man angemeldet ist\n

                Notes:
                - Bitte keine Emojis verwenden in Textfeldern
                - date: ist ein Freitexfeld und dort kann auch etwas stehen wie "wird im thread besprochen"\n
                - mit ```/show_chars``` kann man sich auch chars von anderen anzeigen lassen mit dem zusätzlichen parameter 'user'\n
                """

        embed = discord.Embed(
            title='Help section for loabot',
            color=discord.Colour.dark_orange(),
        )
        embed.add_field(name='User-guide',value=text)

        await ctx.respond('Help section', embed=embed, ephemeral=True, delete_after=120)

    @bot.slash_command(name="animal_bomb", description='Displays a random cat or dog image. 20sec command cooldown and images are deleted after 10 min')
    @discord.guild_only()
    @commands.cooldown(1,20, commands.BucketType.user)
    async def cat_bomb(ctx, animal:discord.Option(str, choices=['cat', 'dog', 'duck', 'fox'], required=True)): # type: ignore
        await ctx.defer()

        if animal == 'cat':
            res = requests.get('https://api.thecatapi.com/v1/images/search')
            result = res.json()
            img = result[0].get('url')
        elif animal == 'dog':
            res = requests.get('https://api.thedogapi.com/v1/images/search')
            result = res.json()
            img = result[0].get('url')
        elif animal =='duck':
            res = requests.get('https://random-d.uk/api/random')
            result = res.json()
            img = result.get('url')
        elif animal == 'fox':
            
            c_random = random.randint(1,123) 
            res = requests.get(f'https://randomfox.ca/images/{c_random}.jpg')                  
            img = f'https://randomfox.ca/images/{c_random}.jpg'


        
        if res.status_code != 200:
            await ctx.followup.send('some api error', ephemeral=True)    
        else:            
            await ctx.followup.send(f'{img}', delete_after=600)

    @bot.event
    async def on_application_command_error(ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(error, ephemeral=True)
        elif isinstance(error, commands.NotOwner):
            await ctx.respond(error, ephemeral=True)
            logger.info(f'{ctx.guild.name}-{ctx.user.name}: {error}')
        else:
            await ctx.respond(error, ephemeral=True)
            logger.warning(f'{ctx.guild.name}: {error}')
            raise error
    

    @bot.slash_command(name="my_raids")
    @discord.guild_only()
    async def my_raids(ctx):
        await ctx.defer(ephemeral=True)
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        db = LBDB()
        db.use_db()
        member = ctx.guild.get_member_named(ctx.author.name)
        u_id = member.id  
        
        group_list = db.get_my_raids(u_id, tablename)
        db.close()

        panel = discord.Embed(
            title='Group overview / Gruppenübersicht',
            color=discord.Colour.green(),
        )
        chars = []
        raid = []
        title =[]
        dates = []

        for g in group_list:
            chars.append(g.get('char_name'))
            raid.append(g.get('raid'))
            dates.append(g.get('date'))
            
            channel = await bot.fetch_channel(g.get('dc_id'))
            #link = await channel.create_invite()
            title.append(f'{channel.jump_url} {g.get("date")}')

        e_chars = "\n".join(str(char) for char in chars)
        e_raid = "\n".join(str(r) for r in raid)
        e_title = "\n".join(str(t) for t in title)
        #e_dates = "\n".join(str(d) for d in dates)

        panel.add_field(name='Char', value=e_chars)
        panel.add_field(name='Raid', value=e_raid)
        panel.add_field(name='Title', value=e_title)

        await ctx.followup.send(f'Your active Groups / Deine aktiven Gruppen ', embed=panel, ephemeral=True)
    
    @bot.slash_command(name='raid_overview')
    @discord.guild_only()
    async def raids_overview(ctx):
        await ctx.defer()
        db = LBDB()
        db.use_db()
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())

        groups_list = db.get_group_overview(tablename)
        db.close()

        embed = discord.Embed(
            title='Raid overview / Raidübersicht',
            color=discord.Colour.green(),
        )
        
        raid = []
        mode = []
        threads  = []
        membercount = []
        title = []

        #add boolean
        length_check = False
        #add embed creation depending on boolean

        for g in groups_list:
            embed_length = len(embed.description)
                    
            m = g.get('raid_mode')
            
            thread = await bot.fetch_channel(g.get('dc_id'))
            channel_id = thread.parent_id
            channel = await bot.fetch_channel(channel_id)            
            message = await channel.fetch_message(g.get('dc_id'))
            url = message.jump_url

            threads.append(url)
            new_length = len(threads) + embed_length
            
            membercount.append(g.get("raid_mc"))
            raid.append(f'{g.get("raid")}')
            mode.append(m.split(' ')[0])
            title.append(g.get('raid_title'))

        time = datetime.now()
        current_time = time.strftime("%H:%M:%S")
        updated = f'last updated at: {current_time}'

        if length_check:
            embed.add_field(name='Achtung', value='Aktuell gibt es zu viele offene Raids um alle anzuzeigen.')
            embed.set_footer(text=updated)
            await ctx.followup.send(view=RaidOverview(), embed=embed)
        else:    

            text_list = [f'**Raidübersicht für {tablename}:**']
                    
            for i in range(len(threads)):
                text_list.append(f'**Thread**: {threads[i]}\t\t**Raid**: {raid[i]}\t\t**Mitglieder**: {membercount[i]}\t\t**Mode**: {mode[i]}') #**Titel**: {title[i]}\n
            
            
            embed.set_footer(text=updated)

            #text_list.append(f'\n*last updated at: {current_time}*')
            text = "\n".join(t for t in text_list)
            embed.description = text
            
            await ctx.followup.send(view=RaidOverview(), embed=embed)


    @bot.slash_command(name="add_dcadmin", description="Adds a user to the admin table ")
    @discord.guild_only()
    async def db_addadmin(ctx, user: discord.Member ):
        await ctx.defer(ephemeral=True)
        db = LBDB()
        db.use_db()
        member = user
        u_id = member.id
        
        result = db.add_admin(u_id)
        db.close()
        await ctx.respond(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="register_char", description="Adds a given char of the user to the DB / Fügt für deinen Benutzer einen Charakter hinzu")
    @discord.guild_only()
    async def test_modal(ctx):
        #modal = CharModal(title='test')
        await ctx.defer(ephemeral=True)
        await ctx.followup.send('Register your char',view=RegisterChar(), delete_after=120, ephemeral=True)

    @bot.slash_command(name="add_raidmember", description="Adds a given DC user with his chars to a raid")
    @discord.guild_only()
    async def add_raidmember(ctx, user: discord.Member, channel: discord.TextChannel, raid: int):
        await ctx.defer(ephemeral=True)
        db = LBDB()
        db.use_db()

        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())

        group = db.get_group(raid, tablename)

        chars = db.get_chars(user.id, tablename)

        msg_id = group.get('dc_id')

        msg = await channel.fetch_message(msg_id)#discord.utils.get(await channel)


        await ctx.followup.send('Add the chars of the user', view=RemoteAddView(user, tablename, channel, raid, chars, db))



    """  @bot.slash_command(name='user_maintenance')
    async def maintenance(ctx):
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        db = LBDB()
        db.use_db()
        await ctx.defer(ephemeral=True)
        all_names= db.all_user(tablename)
        all_chars = db.all_chars(tablename)

        classes_file = open('data/loa_data.json')
        data = json.load(classes_file)
        
        classes_file.close()
        for char in all_chars:
            emoji = ''
            name = char['char_name']
            for i in data['emojis']:
                res = re.search('<:(.*):',i)
                e = res.group(1)
                if char['class'].lower() == e:
                    emoji = i
                elif e == 'artistt' and char['class'].lower() == 'artist':
                    emoji = i
            db.update_emoji(tablename, name, emoji)
        
        await ctx.followup.send('done', ephemeral=True) 
    """
    
    bot.run(token)

if __name__=="__main__":
    bot = init()
    try:
        run(bot)
    except KeyboardInterrupt:
        stop(bot)