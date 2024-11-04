import sys
import logging
from discord.ext import tasks, commands
from discord.ext.commands import Context
from discord.commands import SlashCommandGroup, guild_only
import discord
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

def setup(bot):
    bot.add_cog(AdminCommands(bot))