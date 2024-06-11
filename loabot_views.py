import discord
from discord.ui.item import Item
from loabot_db import LBDB
from loabot_modals import CharModal
import re
from exception_handling import interaction_handling, interaction_handling_defer

class RegisterChar(discord.ui.View):
    def __init__(self, timeout=30):
        super().__init__(timeout=timeout)
        self.db = LBDB()
        self.db.use_db()
        self.add_item(CharClassSelect(self.db, self))

    
    async def on_timeout(self) -> None:
        self.db.close()
        
    


class CharClassSelect(discord.ui.Select):
    def __init__(self, db: LBDB, parentview) -> None:
        self.db = db
        self.pview = parentview
        def set_options():
            classes = self.db.get_all_char_classes()
            c_list = []
            for i in classes:
                c_list.append(discord.SelectOption(label=i.get('class_name')))
            return c_list
        super().__init__(placeholder='Select Character class', min_values=1, max_values=1, options=set_options()) 
    
    async def callback(self, interaction: discord.Interaction):
        try:
            self.placeholder=self.values[0]
            self.disabled = True
            self.pview.add_item(CharSelectNew(self.db, self.values[0], self.pview))
            await interaction.response.edit_message(view=self.pview)
        except Exception as e:
            await interaction_handling(interaction, e)
        

    
class CharSelectNew(discord.ui.Select):
    def __init__(self, db: LBDB, value, parentview) -> None:
        self.db = db
        self.parent_value = value
        self.parentview = parentview 
        def set_options():
            chars = self.db.get_all_chars(self.parent_value)
            c_list = []
            for i in chars:
                c_list.append(discord.SelectOption(label=i.get('char_name')))
            return c_list
        super().__init__(placeholder='Select Character', min_values=1, max_values=1, options=set_options())
    
    async def callback(self, interaction: discord.Interaction):
        try:
            self.placeholder = self.values[0]
            self.disabled=True
            self.parentview.add_item(CharSelectRole(self.values[0], self.db))
            await interaction.response.edit_message(view=self.parentview)
        except Exception as e:
            await interaction_handling(interaction, e)


class CharSelectRole(discord.ui.Select):
    def __init__(self, char, db) -> None:
        self.char = char
        self.db = db
        def set_options():
            roles = ['DD', 'SUPP']
            r_list = []
            for i in roles:
                r_list.append(discord.SelectOption(label=i))
            return r_list
        super().__init__(placeholder='Select Character Role', min_values=1, max_values=1, options=set_options())
    
    async def callback(self, interaction: discord.Interaction):
        try:
            self.placeholder = self.values[0]
            self.disabled=True
            modal = CharModal(title='Set Char Details', char=self.char, role=self.values[0], db=self.db)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction_handling(interaction, e)

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
        try:
            await interaction.response.defer(ephemeral=True)
            db = LBDB()
            db.use_db()
            embed = interaction.message.embeds[0]
            guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

            
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
                await interaction.followup.send('User is not in thread / Benutzer ist nicht im Raid', ephemeral=True)
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
                    #self.dpsvalue.clear()
                    dps_string = fields[6].get('value')
                    re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                    new_dps_string = re.sub(re_pattern, '', dps_string, 1)
                    embed.set_field_at(6, name='DPS', value=new_dps_string)
                    embed.set_field_at(3,name='Anzahl DPS:', value=d_count)

                else:
                    mc -= 1
                    supp_count = fields[4].get('value')
                    s_count = int(supp_count) - 1                    
                    supp_string = fields[7].get('value')
                    re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                    new_supp_string = re.sub(re_pattern, '', supp_string, 1)
                    embed.set_field_at(7, name='SUPP', value=new_supp_string)
                    embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)

                    

                
                
                await self.thread.remove_user(user)
                await interaction.followup.send(f'removed user: {user.name}', ephemeral=True)
                channel = {}
                if interaction.guild.get_channel(interaction.channel.id) is None:
                    channel = interaction.guild.fetch_channel(interaction.channel.id)
                else:
                    channel = interaction.guild.get_channel(interaction.channel.id)
                m = await channel.fetch_message(m_id)
                await m.edit(view=self.view.orgview, embed=embed)

                db.update_group_mc(group_id, mc, guild_name)
                db.remove_groupmember(user.id, group_id, guild_name)

                db.close()
        except Exception as e:
            db.close()
            await interaction_handling_defer(interaction, e)


class CharSelect(discord.ui.Select):
    def __init__(self, optionlist, db, parent) -> None:
        self.olist = optionlist
        self.db = db
        self.parentview = parent
        def set_options():
            list=[]
            for char in optionlist:
                charname = char.split(' ')[0]
                list.append(discord.SelectOption(label=charname))
            return list
    
        super().__init__(custom_id='character_selection', placeholder='Choose your Character', min_values=1, max_values=1, options=set_options(), disabled=False)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            selectedChar = self.values[0]
            self.placeholder = self.values[0]

            charname = ""
            #capital_charname = charname.capitalize()

            guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())

            for char in self.olist:
                if char.split(' ')[0] == selectedChar:
                    charname = char
            #get selected char from db for role
            role = self.db.get_charRole(selectedChar, guild_name)
            #get raid id, user id

            #check if user is already connected to this raid id --> raidmember table
            check = self.db.raidmember_check(self.view.g_id, self.view.user_id, guild_name)

            #disable select menu to prevent unintended char switching
            self.disabled = True
            channel = {}
            if interaction.guild.get_channel(interaction.channel.id) is None:
                channel = await interaction.guild.fetch_channel(interaction.channel.id)
            else:
                channel = interaction.guild.get_channel(interaction.channel.id)
            
            #get message id
            message = self.db.get_message(self.view.g_id, guild_name)
            m_id = message['m_id']
            
            m = await channel.fetch_message(m_id)

            #get mc from raid
            res = self.db.get_group(self.view.g_id, guild_name)
            mc = res['raid_mc']

            #get message id
            

            #get char ilvl
            ilvl = self.db.get_char_ilvl(selectedChar, guild_name)
            char_ilvl = ilvl['ilvl']


            e_dict = self.view.orgview.embed.to_dict()
            e_fields = e_dict.get('fields')

            if(check is None):
                    
                

                if(role['role'] == 'DPS'):
                    #update mc update_group_mc
                    mc += 1
                    dps_count = e_fields[3].get('value')
                    d_count = int(dps_count) + 1
                    #self.view.orgview.dpsvalue.append(f'{selectedChar} - {interaction.user.name}\n')
                    
                    self.view.orgview.embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                    dps_string = e_fields[6].get('value')
                    new_dps_string = dps_string + f'\n{charname} ({char_ilvl}) - {interaction.user.name}\n'
                    self.view.orgview.embed.set_field_at(6, name='DPS', value=new_dps_string)
                    
                else:
                    mc += 1
                    supp_count = e_fields[4].get('value')
                    s_count = int(supp_count) + 1
                    self.view.orgview.embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)
                    supp_string = e_fields[7].get('value')
                    new_supp_string = supp_string + f'\n{charname} ({char_ilvl}) - {interaction.user.name}\n'
                    self.view.orgview.embed.set_field_at(7, name='SUPP', value=new_supp_string)

                #self.view.orgview.user_chars.clear() #clear list
                try:                   
                
                    await self.view.thread.add_user(interaction.user)            
                    
                    self.parentview.children[0].disabled = False
                    await m.edit(view=self.view.orgview, embed=self.view.orgview.embed)
                    await interaction.delete_original_response()
                    self.disabled = True
                    #m2 = await interaction.original_response()
                    #await m2.edit(view=self.view)
                    #await interaction.followup.send('Add you to the group / Du wurdest der Gruppe hinzugefügt', ephemeral=True)
                    self.db.add_groupmember(self.view.g_id, self.view.user_id, charname, guild_name)
                    self.db.update_group_mc(self.view.g_id, mc, guild_name)
                    self.db.close()
                    self.parentview.active = True
                    self.view.stop()
                except Exception as e:
                    self.db.close()
                    self.view.stop()
                    await interaction_handling_defer(interaction, e)

            else:
            
                old_char = self.view.old_char.split(' ')[0]
                old_role = self.db.get_charRole(old_char, guild_name)

                new_embed = {}

                if old_role['role'] == 'DPS':
                    mc -= 1
                    dps_count = e_fields[3].get('value')
                    d_count = int(dps_count) - 1                    
                    dps_string = e_fields[6].get('value')
                    re_pattern = re.compile(re.escape(old_char) + '.*?(\n|$)', re.DOTALL)
                    new_dps_string = re.sub(re_pattern, '', dps_string, 1)
                    self.view.orgview.embed.set_field_at(6, name='DPS', value=new_dps_string)
                    self.view.orgview.embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                    
                    message = await m.edit(view=self.view.orgview, embed=self.view.orgview.embed)
                    new_embed = message.embeds[0]
                    new_e_dict = new_embed.to_dict()
                    new_fields = new_e_dict.get('fields')


                    if(role['role'] == 'DPS'):                    
                        mc += 1
                        dps_count = new_fields[3].get('value')
                        d_count = int(dps_count) + 1
                        #self.db.update_group_mc(self.view.g_id, mc, guild_name)
                        new_embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                        dps_string = new_fields[6].get('value')
                        new_dps_string = dps_string + f'\n{charname} ({char_ilvl}) - {interaction.user.name}\n'
                        new_embed.set_field_at(6, name='DPS', value=new_dps_string)
                        
                    else:
                        #print('switched from dps to supp') --> maybe replace with log.debug
                        mc += 1
                        supp_count = new_fields[4].get('value')
                        s_count = int(supp_count) + 1
                        #self.db.update_group_mc(self.view.g_id, mc, guild_name)
                        new_embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)
                        supp_string = new_fields[7].get('value')
                        new_supp_string = supp_string + f'\n{charname} ({char_ilvl}) - {interaction.user.name}\n'
                        new_embed.set_field_at(7, name='SUPP', value=new_supp_string)

                else:
                    mc -= 1
                    supp_count = e_fields[4].get('value')
                    s_count = int(supp_count) - 1
                    #self.db.update_group_mc(self.view.g_id, mc, guild_name)
                    supp_string = e_fields[7].get('value')
                    re_pattern = re.compile(re.escape(old_char) + '.*?(\n|$)', re.DOTALL)
                    new_supp_string = re.sub(re_pattern, '', supp_string, 1)

                    self.view.orgview.embed.set_field_at(7, name='SUPP', value=new_supp_string)
                    self.view.orgview.embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)
                    #self.db.remove_groupmember(self.view.user_id, self.view.g_id, guild_name)
                    message = await m.edit(view=self.view.orgview, embed=self.view.orgview.embed)
                    #print('edit old supp mess') --> maybe replace with log.debug
                    new_embed = message.embeds[0]
                    new_e_dict = new_embed.to_dict()
                    new_fields = new_e_dict.get('fields')

                    
                    if(role['role'] == 'DPS'):
                        #print('switched to new dps') --> maybe replace with log.debug
                        mc += 1
                        dps_count = new_fields[3].get('value')
                        d_count = int(dps_count) + 1
                        #self.db.update_group_mc(self.view.g_id, mc, guild_name)
                        new_embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                        dps_string = new_fields[6].get('value')
                        new_dps_string = dps_string + f'\n{charname} ({char_ilvl}) - {interaction.user.name}\n'
                        new_embed.set_field_at(6, name='DPS', value=new_dps_string)
                        
                    else:
                        mc += 1
                        supp_count = new_fields[4].get('value')
                        s_count = int(supp_count) + 1
                        #self.db.update_group_mc(self.view.g_id, mc, guild_name)
                        new_embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)
                        supp_string = new_fields[7].get('value')
                        new_supp_string = supp_string + f'\n{charname} ({char_ilvl}) - {interaction.user.name}\n'
                        new_embed.set_field_at(7, name='SUPP', value=new_supp_string)              
                
                self.db.remove_groupmember(self.view.user_id, self.view.g_id, guild_name)
                self.db.add_groupmember(self.view.g_id, self.view.user_id, charname, guild_name)
                
                self.parentview.children[0].disabled = False
                await m.edit(view=self.view.orgview, embed=new_embed)
                await interaction.delete_original_response()
                self.disabled = True
                self.db.close()
                self.view.stop()
        except Exception as e:
            self.db.close()
            self.view.stop()
            await interaction_handling_defer(interaction, e)



class RaidType(discord.ui.Select):
    def __init__(self, parentview) -> None:
        self.parentview = parentview
        self.raids = []
        def set_options():
            types = ['Legion', 'Abyssal', 'Guardian']
            list = []
            for t in types:
                list.append(discord.SelectOption(label=t))
            return list
        super().__init__(custom_id='raid_type', placeholder='Choose a Raid Type', min_values=1, max_values=1, options=set_options(), disabled=False)

    async def callback(self, interaction: discord.Interaction):
        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())
        r_type = self.values[0]
        self.placeholder = self.values[0]
        db = LBDB()
        db.use_db()
        raids = db.get_typed_raids_inorder(guild_name, r_type)
        self.parentview.add_item(RaidSelect(parentview=self.parentview, raid_type=r_type, raids= raids))
        self.disabled = True

        try:
            await interaction.response.edit_message(view=self.parentview, embed=self.parentview.embed)
        except Exception as e:
            await interaction_handling(interaction, e)

class RaidSelect(discord.ui.Select):
    def __init__(self, parentview, raid_type, raids) -> None:
        self.parentview = parentview
        self.raid_type= raid_type
        self.raids = raids
        def set_options():
            list = []

            for r in self.raids:
                list.append(discord.SelectOption(label=r.get('name'), description=r.get('type')))
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
        except Exception as e:
            await interaction_handling(interaction, e)
    

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
        except Exception as e:
            await interaction_handling(interaction, e)


class RemoteCharSelect(discord.ui.Select):
    def __init__(self, optionlist, db, user, table, raid_id, channel) -> None:
        self.olist = optionlist
        self.db = db
        self.user = user
        self.table = table
        self.channel = channel
        self.raid_id = raid_id

        def set_options():
            list=[]
            for char in optionlist:
                #charname = char.split(' ')[0]
                list.append(discord.SelectOption(label=char.get('char_name')))
            return list
    
        super().__init__(custom_id='character_selection', placeholder='Choose the Character', min_values=1, max_values=1, options=set_options(), disabled=False)

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)
        selectedChar = self.values[0]
        self.placeholder = self.values[0]

        group = self.db.get_group(self.raid_id, self.table)
        msg_id = group.get('dc_id')

        msg = await self.channel.fetch_message(msg_id)

        m_view = discord.ui.View.from_message(msg)

        thread = await interaction.guild.fetch_channel(msg_id)

        charname = {}
        #capital_charname = charname.capitalize()

        
        for char in self.olist:
            if char.get('char_name') == selectedChar:
                charname = char
        #get selected char from db for role
                
        role_res = self.db.get_charRole(charname.get('char_name'), self.table)
        role = role_res.get('role')
        #get raid id, user id

        group_id = group.get('id')
        #check if user is already connected to this raid id --> raidmember table
        check = self.db.raidmember_check(group_id, self.user.id, self.table)

        #disable select menu to prevent unintended char switching
        self.disabled = True        

        #get mc from raid
        g_mc = group.get('raid_mc')

        #get message id


        #get char ilvl
        ilvl = charname.get('ilvl')

        embed = msg.embeds[0]

        e_dict = embed.to_dict()
        e_fields = e_dict.get('fields')

        admin_role_id = 1006783350188560416
        erklearbear_role_id = 1117824013931122758
        author = embed.author.name

        raid = e_fields[1].get('value')
        raidname = raid.split(' -')[0]

        res = self.db.get_raid_mc(raidname)
        mc = res['member']

        #g_res= self.db.get_group(group_id, self.table)
        #g_mc = g_res['raid_mc']

        if g_mc >= mc:
            self.db.close()
            await interaction.followup.send('Raid has max membercount', ephemeral=True)
        
        else:

            if interaction.user.name == author:
                if(check is None):
                    try:
                        #self.db.add_groupmember(group_id, self.user.id, charname.get('char_name'), self.table)    
                        

                        if(role == 'DPS'):
                            #update mc update_group_mc
                            g_mc += 1
                            dps_count = e_fields[3].get('value')
                            d_count = int(dps_count) + 1
                            embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                            dps_string = e_fields[6].get('value')
                            new_dps_string = dps_string + f'\n{charname.get("char_name")}{charname.get("emoji")} ({ilvl}) - {self.user.name}\n'
                            embed.set_field_at(6, name='DPS', value=new_dps_string)                
                        else:
                            g_mc += 1
                            supp_count = e_fields[4].get('value')
                            s_count = int(supp_count) + 1
                            embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)
                            supp_string = e_fields[7].get('value')
                            new_supp_string = supp_string + f'\n{charname.get("char_name")}{charname.get("emoji")} ({ilvl}) - {self.user.name}\n'
                            embed.set_field_at(7, name='SUPP', value=new_supp_string)

                        
                        
                        t = await thread.add_user(self.user)            
                        mes = await msg.edit(embed=embed)#view=m_view,

                        self.db.add_groupmember(group_id, self.user.id, charname.get('char_name'), self.table)
                        self.db.update_group_mc(group_id, g_mc, self.table) 
                        self.db.close()
                           
                    except Exception as e:
                        self.db.close()
                        await interaction_handling_defer(interaction, e)
                    
                            
                    
            elif interaction.user.get_role(erklearbear_role_id) or interaction.user.get_role(admin_role_id):            

                if(check is None):
                    try:                        
                        

                        if(role == 'DPS'):
                            #update mc update_group_mc
                            g_mc += 1
                            dps_count = e_fields[3].get('value')
                            d_count = int(dps_count) + 1
                            embed.set_field_at(3,name='Anzahl DPS:', value=d_count)
                            dps_string = e_fields[6].get('value')
                            new_dps_string = dps_string + f'\n{charname.get("char_name")}{charname.get("emoji")} ({ilvl}) - {self.user.name}\n'
                            embed.set_field_at(6, name='DPS', value=new_dps_string)                
                        else:
                            g_mc += 1
                            supp_count = e_fields[4].get('value')
                            s_count = int(supp_count) + 1
                            embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)
                            supp_string = e_fields[7].get('value')
                            new_supp_string = supp_string + f'\n{charname.get("char_name")}{charname.get("emoji")} ({ilvl}) - {self.user.name}\n'
                            embed.set_field_at(7, name='SUPP', value=new_supp_string)

                        
                        
                        await thread.add_user(self.user)            
                        
                        await msg.edit(embed=embed)#view=m_view,
                    
                    except Exception as e:
                        self.db.close()
                        await interaction_handling(interaction, e)
                    else:
                        self.db.add_groupmember(group_id, self.user.id, charname.get('char_name'), self.table)
                        self.db.update_group_mc(group_id, g_mc, self.table)
                        self.db.close()
            
            else:
                self.db.close()
                await interaction.followup.send('You are not a Mod or owner of this group', ephemeral=True)

           
