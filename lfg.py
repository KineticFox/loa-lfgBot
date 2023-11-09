import os
import discord
from discord.components import SelectOption
from discord.enums import ChannelType, ComponentType
from discord.ext import commands
from discord.interactions import Interaction
from discord.ui.item import Item
import dotenv
from loabot_db import LBDB
import json
from time import sleep
import asyncio
import logging
import re
import time


logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formater = logging.Formatter('%(asctime)s - %(levelname)s %(name)s:%(msg)s', '%y-%m-%d, %H:%M')
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
        #await interaction.response.defer()
        embed = interaction.message.embeds[0]
        chanell = {}

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
        
        try:
            m = await chanell.send('A Wild Raid spawns, come and join', embed=embed , view=JoinRaid())
            thread = await m.create_thread(name=f"{embed.title}")
            thread_id = thread.id        
            r_id = self.db.store_group(edict.get('title'), fields[1].get('value'), fields[2].get('value'), fields[0].get('value'), thread_id, guild_name)
        except discord.errors as e:
            logger.warning(f'DC Error in creatRaid callback - {e}')


        if r_id is None or len(r_id) == 0:
            self.db.close()
            logger.warning(f'Raid creation failed for {interaction.user.name}')
            await interaction.response.send_message('Something went wrong!',  ephemeral=True)
            await m.delete()
            await thread.delete()   
        else:             
            raid_id = r_id['LAST_INSERT_ID()']
            self.db.add_message(m.id, raid_id, guild_name)
            embed.add_field(name='ID', value=raid_id)
            await interaction.response.defer()
            await interaction.delete_original_response()
            await m.edit(embed=embed ,view=JoinRaid())
            self.db.close()
            logger.debug(f'stored raid group with ID {raid_id}')
            


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

    @discord.ui.button(
        label='Join raid',
        style=discord.ButtonStyle.green,
        custom_id= 'join_button'
    )

    async def join_callback(self, button, interaction):
        db = LBDB()
        db.use_db()
        m_id = interaction.message.id
        c_id = interaction.channel.id
        user = interaction.user.name
        member = interaction.guild.get_member_named(user)
        u_id = member.id  
        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())
        self.embed = interaction.message.embeds[0]             
        await interaction.response.defer()
        result = db.select_chars(u_id, guild_name)
        edict = self.embed.to_dict()
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
            await interaction.followup.send('Please register your user and chars first! / Bitte erstelle zuerst einen Charakter!')
        elif len(result) == 0:
            db.close()
            await interaction.followup.send('No registered chars found. Please register your chars first! / Kein Charakter von dir gefunden, bitte erstelle zuerst einen Charakter',  ephemeral=True)
        elif join_check is not None:
            db.close()
            char = join_check['char_name']
            await interaction.followup.send(f'You are already in this raid with {char} / Du bist schon in dieser Gruppe mit {char} eingetragen', ephemeral=True)
        elif g_mc >= mc:
            db.close()
            await interaction.followup.send(f'This group has the max member count reached / Diese Gruppe hat die maximale Mitgliederanzahl erreicht', ephemeral=True)
        else:
            panel = discord.Embed(
                title='Please choose your Character / Bitte wähle deinen Charakter',
                color=discord.Colour.blue(),
            )

            chanell = await interaction.guild.fetch_channel(c_id)
            thread = chanell.get_thread(m_id)
            await interaction.followup.send(ephemeral=True, view=JoinDialogue(self, db, group_id, thread, m_id, u_id, guild_name), embed=panel)



    @discord.ui.button(
            label='Kick member',
            style=discord.ButtonStyle.danger,
            custom_id='kick_m'
    )

    async def kick_callback(self, button, interaction):

        user_list = []
        embed = interaction.message.embeds[0]
        author = embed.author.name
        embed_dict = embed.to_dict()

        if interaction.user.name != author:
            await interaction.response.send_message('You are not party leader/ Du bist nicht der Partyleiter!!', ephemeral=True)
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
                await interaction.response.send_message('No users to kick in this thread / Es sind keine User in der Gruppe', ephemeral=True)
            else:
                await interaction.response.send_message(ephemeral=True, view=KickView(user_list, thread, self), embed=embed)
  
    @discord.ui.button(
        label='Leave',
        style=discord.ButtonStyle.blurple,
        custom_id='leave_thread'
    )


    async def leave_callback(self, button, interaction):
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
            await interaction.response.send_message('You can not leave please delete group / Du kannst die gruppe nicht verlassen bitte lösche die Gruppe', ephemeral=True)
        elif char_result is None:
            db.close()
            await interaction.response.send_message('You can not leave, you are not member of the party / Du bist kein Mitglied der Gruppe', ephemeral=True)
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
                    await interaction.response.edit_message(embed=embed, view=self)
                    await thread.remove_user(interaction.user)
                except discord.errors as e:
                    logger.warning(f'DC Error in leave callback- {e}')
                    await interaction.response.send('Something went wrong, try again or seek for help / Etwas ist schiefgelaufen, probiere es nochmal oder frag nach Hilfe', ephemeral=True)
            else:
                db.close()
                try:
                    await interaction.response.edit_message(embed=embed, view=self)
                    await thread.remove_user(interaction.user)
                except discord.errors as e:
                    logger.warning(f'DC Error in leave callback - {e}')
                    await interaction.response.send_message('Something went wrong, try again or seek for help / Etwas ist schiefgelaufen, probiere es nochmal oder frag nach Hilfe', ephemeral=True) 
                    
    @discord.ui.button(
        label='Delete',
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
            await interaction.response.defer()
            await interaction.message.delete()
        else:
            db.close()
            await interaction.response.send_message('you can not delete the party because you are not the owner / Du kannst die Gruppe nicht löschen, da du nicht der Leiter bist.', ephemeral=True)

#--------------------- Subclassed view elements -----------------------------------#

class JoinDialogue(discord.ui.View):
    def __init__(self, orgview, db,group_id, thread, message, user_id, guild_name):
        self.orgview = orgview
        self.db = db
        self.user_chars = []
        self.g_id = group_id
        self.thread = thread
        self.message = message
        self.user_id = user_id
        self.guild_name = guild_name
        def setup_chars():
            result = self.db.select_chars(self.user_id, self.guild_name)  
            #temp_char_list = [{k: item[k] for k in item.keys()} for item in result]
            for d in result:
                self.user_chars.append(f'{d.get("char_name")} {d.get("emoji")}')


        setup_chars()
        super().__init__(
            timeout=40, 
            disable_on_timeout=True
            )
        
        self.add_item(CharSelect(self.user_chars, self.db))

class KickView(discord.ui.View):
    def __init__(self, memberlist, thread, orgview):
        self.mlist = memberlist
        self.thread = thread
        self.orgview = orgview
        super().__init__(timeout=40, disable_on_timeout=True)

        self.add_item(KickDialogue(self.mlist, self.thread))
    
class KickDialogue(discord.ui.Select):
    def __init__(self, mlist, thread) -> None:
        self.memberlist = mlist
        self.thread = thread
        def set_options():
            list=[]
            for m in mlist:
                list.append(discord.SelectOption(label=m.name))
            return list
        super().__init__(custom_id='memberlist', placeholder='Choose member', min_values=1, max_values=1, options=set_options(), disabled=False)
    
    async def callback(self, interaction: discord.Interaction):
        db = LBDB()
        db.use_db()
        embed = interaction.message.embeds[0]
        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        await interaction.response.defer(ephemeral=True)
        embed_dict = embed.to_dict()
        fields = embed_dict.get('fields')
        group_id = fields[8].get('value')

        member_name = self.values[0]

        user = {}
        for m in self.memberlist:
            if m.name == member_name:
                user = m

        #get char of user
        char_result = db.raidmember_check(group_id, user.id, guild_name)
        
        if char_result is None:
            db.close()
            await interaction.followup.send('User is not in thread / Benutzer ist nicht im Raid')
        else:
            message = db.get_message(group_id, guild_name)
            m_id = message['m_id']
            char = char_result['char_name']
            #get role of user
            clean_char_name = char.split(' ')[0]
            role_result = db.get_charRole(clean_char_name, guild_name)
            role = role_result['role']

            group_result = db.get_group(group_id, guild_name)
            mc = group_result['raid_mc']

            ilvl = db.get_char_ilvl(clean_char_name, guild_name)
            char_ilvl = ilvl['ilvl']

            if role == 'DPS':
                mc -= 1
                dps_count = fields[3].get('value')
                d_count = int(dps_count) - 1
                db.update_group_mc(group_id, mc, guild_name)
                #self.dpsvalue.clear()
                dps_string = fields[6].get('value')

                re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                new_dps_string = re.sub(re_pattern, '', dps_string, 1)
                embed.set_field_at(6, name='DPS', value=new_dps_string)
                embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                db.remove_groupmember(user.id, group_id, guild_name)

            else:
                mc -= 1
                supp_count = fields[4].get('value')
                s_count = int(supp_count) - 1
                db.update_group_mc(group_id, mc, guild_name)
                #self.suppvalue.clear()
                supp_string = fields[7].get('value')
                re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                new_supp_string = re.sub(re_pattern, '', supp_string, 1)

                embed.set_field_at(7, name='SUPP', value=new_supp_string)
                embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)

                db.remove_groupmember(user.id, group_id, guild_name)

            db.close()

            try:
                await self.thread.remove_user(user)
                await interaction.followup.send(f'removed user: {user.name}', ephemeral=True)
                channel = {}
                if interaction.guild.get_channel(interaction.channel.id) is None:
                    channel = interaction.guild.fetch_channel(interaction.channel.id)
                else:
                    channel = interaction.guild.get_channel(interaction.channel.id)
                m = await channel.fetch_message(m_id)
                await m.edit(view=self.view.orgview, embed=embed)
            except discord.errors as e:
                logger.warning(f'DC Error in kick callback - {e}')
                await interaction.followup.send('Something went wrong, try again or seek for help / Etwas ist schiefgelaufen, probiere es nochmal oder frag nach Hilfe', ephemeral=True)

    



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

        charname = selectedChar.split(' ')[0]
        capital_charname = charname.capitalize()

        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

        #get selected char from db for role
        role = self.db.get_charRole(capital_charname, guild_name)
        #get raid id, user id

        #check if user is already connected to this raid id --> raidmember table
        check = self.db.raidmember_check(self.view.g_id, self.view.user_id, guild_name)

        #disable select menu to prevent unintended char switching
        self.disabled = True

        if(check is None):
            self.db.add_groupmember(self.view.g_id, self.view.user_id, selectedChar, guild_name)

            #get mc from raid
            res = self.db.get_group(self.view.g_id, guild_name)
            mc = res['raid_mc']

            #get message id
            message = self.db.get_message(self.view.g_id, guild_name)
            m_id = message['m_id']

            #get char ilvl
            ilvl = self.db.get_char_ilvl(capital_charname, guild_name)
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
            try:
                await self.view.thread.add_user(interaction.user)

                await interaction.response.edit_message(view=self.view)
                #await interaction.followup.edit_message
                channel = {}
                if interaction.guild.get_channel(interaction.channel.id) is None:
                    channel = await interaction.guild.fetch_channel(interaction.channel.id)
                else:
                    channel = interaction.guild.get_channel(interaction.channel.id)

                m = await channel.fetch_message(m_id)
                await m.edit(view=self.view.orgview, embed=self.view.orgview.embed)
                await interaction.delete_original_response()
            except discord.errors as e:
                logger.warning(f'DC Error in charSelect callback - {e}')
                await interaction.response.send_message('Something went wrong, try again or seek for help / Etwas ist schiefgelaufen, probiere es nochmal oder frag nach Hilfe', ephemeral=True) 
        else:
            name = check['char_name']
            self.db.close()
            await interaction.response.send_message(f'you are already in this group with {name} / Du bist schon mit {name} angemeldet', ephemeral=True)

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
        try:
            await interaction.response.edit_message(view=self.parentview, embed=self.parentview.embed)
        except discord.errors as e:
            logger.warning(f'DC Error in raidType callback - {e}')
            await interaction.response.send_message('Something went wrong / Etwas ist schiefgelaufen', ephemeral=True) 


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
        try:
            await interaction.response.edit_message(view=self.parentview, embed=self.parentview.embed)
        except discord.errors as e:
            logger.warning(f'DC Error in raidSelect callback - {e}')
            await interaction.response.send_message('Something went wrong / Etwas ist schiefgelaufen', ephemeral=True)

class RaidModeSelect(discord.ui.Select):
    def __init__(self, parentview, mode) -> None:
        self.parentview = parentview
        self.mode = mode
        def set_options():
            list = []
            list.append(discord.SelectOption(label='Static', description='For static groups'))
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
        try:
            await interaction.response.edit_message(view=self.parentview, embed=self.parentview.embed)
        except discord.errors as e:
            await interaction.response.send_message('Something went wrong / Etwas ist schiefgelaufen', ephemeral=True)




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
    bot = commands.Bot(command_prefix='!', intents=intents)
    return bot

def stop(bot):
    bot.close()

def run(bot):
    dotenv.load_dotenv()
    token = str(os.getenv("TOKEN"))
    
    
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
        db.close()
        logger.info('Setup in general done')

    
    @bot.slash_command(name = "hi", description = "say hi")
    async def hello(ctx):
        await ctx.respond(f"hello {ctx.user}")

    @bot.slash_command(name="lfg", description="creates a raid, no emojis allowed in title / Erstellt eine lfg-Party, keine emojis erlaubt.")
    async def create_raid(ctx, title: discord.Option(str, 'Choose a title', max_length=70), date: discord.Option(str, 'Date + time or short text', required=True, max_length=40)):
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

    
    @bot.slash_command(name="db_showtable", description="shows all rows of given table")
    async def db_showtable(ctx, table: discord.Option(str, 'name of the table', required=True)):
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        db = LBDB()
        db.use_db()
        rows = db.show(table, tablename)
        #dicts = [{k: item[k] for k in item.keys()} for item in rows]
        #print(dicts)
        db.close()
        await ctx.respond(f'your table view {rows}', delete_after=30)
    
    @bot.slash_command(name="register_char", description="Adds a given char of the user to the DB / Fügt für deinen Benutzer einen Charakter hinzu")
    async def db_addchars(ctx, char: discord.Option(str, 'Charname', required=True, max_length=69), cl: discord.Option(str, 'Class', required=True, choices=load_classes()), ilvl: discord.Option(int, 'item level', required=True), role: discord.Option(str, 'Role', required=True, choices=['DPS', 'SUPP'])):
        db = LBDB()
        db.use_db()
        member = ctx.guild.get_member_named(ctx.author.name)
        u_id = member.id
        await ctx.defer(ephemeral=True)
        classes_file = open('data/loa_data.json')
        data = json.load(classes_file)
        
        emoji = ''

        for i in data['emojis']:
            res = re.search('<:(.*):',i)
            e = res.group(1)
            if cl.lower() == e:
                emoji = i
            elif e == 'artistt' and cl.lower() == 'artist':
                emoji = i


        classes_file.close()

        table = ''.join(l for l in ctx.guild.name if l.isalnum())
        result = db.add_chars(char, cl, ctx.author.name, ilvl, role, table, u_id, emoji)
        db.close()
        await ctx.respond(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="update_char", description="Updates the i-lvl of given char or deletes it / Ändert das i-lvl des Charakters oder löscht ihn")
    async def db_updatechars(ctx, charname: discord.Option(str, 'Charname', required=True, max_length=69), ilvl: discord.Option(int, 'ilvl', required=True), delete: discord.Option(str, 'delete', required=False, choices=['yes','no'], default='no')):
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        await ctx.defer(ephemeral=True)
        
        db = LBDB()
        db.use_db()
        result = db.update_chars(charname, ilvl, delete, tablename)
        db.close()
        await ctx.send_followup(result, ephemeral=True, delete_after=20)
    
    @bot.slash_command(name="show_chars", description="Shows all chars of the user / Zeigt alle Charaktere des Spielers an")
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
        await ctx.defer(ephemeral=True)
        if amount:
            #await ctx.channel.purge(limit=amount, bulk=False)
            #await ctx.respond(f'deleted {amount} messages',ephemeral=True, delete_after=10)
            for i in range(0, amount):
                await ctx.channel.purge(limit=5, bulk=False)
                await ctx.followup.send(f'deleted {amount -1} messages', ephemeral=True, delete_after=10)
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
                1. ```/register_char``` -- registers one of many of your chars/registriert einen von vielen deiner chars\n
                2. Now you are good to go and you can join and create Groups/Raids / Jetzt kannst du Gruppen beitreten und erstellen\n
                - with ```/show_chars``` you can get an overview of your registered chars / zeigt eine Übersicht deiner Chars an\n
                - with ```/lfg``` you create a looking-for-group lobby / Befehl um Gruppen zu erstellen\n

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

    @bot.slash_command(name="my_raids")
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

        #chardicts = [{k: item[k] for k in item.keys()} for item in result]
        for g in group_list:
            chars.append(g.get('char_name'))
            raid.append(g.get('raid'))
            
            channel = await bot.fetch_channel(g.get('dc_id'))
            #link = await channel.create_invite()
            print(channel.jump_url)
            title.append(channel.jump_url)

        e_chars = "\n".join(str(char) for char in chars)
        e_raid = "\n".join(str(r) for r in raid)
        e_title = "\n".join(str(t) for t in title)

        panel.add_field(name='Char', value=e_chars)
        panel.add_field(name='Raid', value=e_raid)
        panel.add_field(name='Title', value=e_title)

        await ctx.followup.send(f'Your active Groups / Deine aktiven Gruppen ', embed=panel, ephemeral=True)

    @bot.slash_command(name='user_maintenance')
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

        #for name in all_names:
        #    n = name['name']
        #    member = ctx.guild.get_member_named(name['name'])
        #    u_id = member.id
        #    db.update_user(tablename, n, u_id)

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
    
    bot.run(token)

if __name__=="__main__":
    bot = init()
    try:
        run(bot)
    except KeyboardInterrupt:
        stop(bot)