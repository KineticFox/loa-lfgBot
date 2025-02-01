import sys
import logging
from discord.ext import tasks, commands
from discord.ext.commands import Context
from discord.commands import SlashCommandGroup, guild_only
import discord
import re
sys.path.append('..')
from loabot_db import LBDB

class AdminCommands(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()

    admin = SlashCommandGroup(name='admin', description='Commands for administrative tasks', guild_only=True)

    @admin.command(name="add_raid")
    async def add_raid(self, ctx, name:discord.Option(str, 'Raid Name', required=True), modes:discord.Option(str, 'Raid Modes', required=True), member:discord.Option(int, 'Member count', required=True), raidtype:discord.Option(str, 'Raid type', choices=['Legion', 'Abyssal', 'Guardian', 'Kazeros', 'Epic'], required=True)):
        db = LBDB()

        db.use_db()
        raid_orders : list = db.get_raid_orders(raidtype)
        order_dict = raid_orders[-3:][0]
        res : int = db.add_raids(name,modes,member, raidtype, 'TechKeller', order_dict.get('raid_order') + 1)

        res = 0
        if res == 0:
            db.close()
            await ctx.respond(f'added the new Raid {name}', ephemeral=True, delete_after=20)
        elif res == 1:
            db.close()
            await ctx.respond(f'Raid with name {name} exists, updating instead', ephemeral=True, delete_after=20)
        
    
    @admin.command(name="add_thumbnail")
    async def add_thumbnail(self, ctx, name:discord.Option(str, 'Raid Name', required=True), url:discord.Option(str, 'Image url', required=True)):
        db = LBDB()
        db.use_db()

        return_code = db.save_image(name, url, 'TechKeller')

        if return_code == 0:
            await ctx.respond(f'added the new image {name}', ephemeral=True, delete_after=20)
        elif return_code == 1:
            await ctx.respond(f'image for Raid {name} already exists', ephemeral=True, delete_after=20)
        elif return_code == 2:
            await ctx.respond(f'Raid {name} does not exist', ephemeral=True, delete_after=20)
        
        db.close()
    
    @admin.command(name="set_admin_role")
    async def add_admin_role(self, ctx, role:discord.Role):
        await ctx.defer(ephemeral=True)
        guild_name = ''.join(l for l in ctx.guild.name if l.isalnum())
        db = LBDB()
        db.use_db()
        
        u_id = role.id
        
        result = db.add_admin(u_id, guild_name)

        db.close()
        if result == 0:
            await ctx.respond("Add Role as admin role", ephemeral=True, delete_after=20)
        elif result == 1:
            await ctx.respond("Admin role already exist", ephemeral=True, delete_after=20)
    
    @admin.command(name="delete_user")
    async def delete_user(self, ctx, user:discord.User):
        await ctx.defer(ephemeral=True, invisible=True)
        db = LBDB()
        db.use_db()
        final_message = []
        tablename = ''.join(l for l in ctx.guild.name if l.isalnum())
        #add logic
        #get user ID & DB user is
        raw_user = db.get_raw_user(user.id, tablename)
        raw_user_dict = raw_user[0]
        internal_user_id = raw_user_dict.get('id')
        #get possible groups of user
        groups_of_user = db.get_my_raids(user.id, tablename)
        
         
        #kick from those groups

        #char_result = db.raidmember_check(group_id, user.id, guild_name)
        if len(groups_of_user) == 0:
            await ctx.followup.send('User is in no groups, continuing to delete his chars.', ephemeral=True)
            final_message.append('User was not in any group.\n')
        else:
            
            try:
                for group in groups_of_user:
                    group_id =group.get('id')
                    message = db.get_message(group_id, tablename)
                    m_id = message['m_id']
                    char = group['char_name']
                    #get role of user
                    clean_char_name = char.split(' ')[0]
                    role_result = db.get_charRole(clean_char_name, tablename)
                    role = role_result['role']

                    group_result = db.get_group(group_id, tablename)
                    mc = group_result['raid_mc']

                    ilvl = db.get_char_ilvl(clean_char_name, tablename)
                    char_ilvl = ilvl['ilvl']

                    discord_message = await ctx.fetch_message(m_id)

                    message_embed = discord_message.embeds[0]

                    embed_dict =message_embed.to_dict()
                    fields = embed_dict.get('fields')
                    
                    if role == 'DPS':
                        mc -= 1
                        dps_count = fields[3].get('value')
                        d_count = int(dps_count) - 1
                        #self.dpsvalue.clear()
                        dps_string = fields[6].get('value')
                        re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                        new_dps_string = re.sub(re_pattern, '', dps_string, 1)
                        message_embed.set_field_at(6, name='DPS', value=new_dps_string)
                        message_embed.set_field_at(3,name='Anzahl DPS:', value=d_count)

                    else:
                        mc -= 1
                        supp_count = fields[4].get('value')
                        s_count = int(supp_count) - 1                    
                        supp_string = fields[7].get('value')
                        re_pattern = re.compile(re.escape(char) + '.*?(\n|$)', re.DOTALL)
                        new_supp_string = re.sub(re_pattern, '', supp_string, 1)
                        message_embed.set_field_at(7, name='SUPP', value=new_supp_string)
                        message_embed.set_field_at(4,name='Anzahl SUPP:', value=s_count)

                    view = discord.ui.View.from_message(discord_message)
                    await discord_message.edit(view=view, embed=message_embed)

                    db.update_group_mc(group_id, mc, tablename)
                    db.remove_groupmember(user.id, group_id, tablename)

                db.close()
                final_message.append(f'User was deleted from {len(groups_of_user)} groups.\n')
                
            except Exception as e:
                db.close()
                #await interaction_handling_defer(interaction, e)


        #delte chars of user
        
        #delete user

        await ctx.respond(''.join(final_message))

def setup(bot):
    bot.add_cog(AdminCommands(bot))