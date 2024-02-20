import os
from discord.ext import commands
import discord

class MemberManagement(commands.Cog):
    def __init__(self, bot:discord.bot) -> None:
        super().__init__()
        self.bot = bot
        self.guild = {}
    
    async def setupGuild(self):
        self.guild = discord.utils.get(self.bot.guilds, name='TechKeller')
        self.welcom_role = discord.utils.get(await self.guild.fetch_roles(), name='welcome')
        self.contributer_role = discord.utils.get(await self.guild.fetch_roles(), name='contributer')
        self.help_role = discord.utils.get(await self.guild.fetch_roles(), name='Bot-help')

        self.welcome_channel = discord.utils.get(self.bot.get_all_channels(), name='welcome-roles')
        self.rule_channel = discord.utils.get(self.bot.get_all_channels(), name='rules')
        print('done')

    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if int(payload.messsage_id) != 1193873640580730991:
            pass
        else:
            guild = self.bot.get_guild(payload.guild_id)
            
            if payload.emoji.name == '❓' :
                help_role = discord.utils.get(await guild.fetch_roles(), name='Bot-help')
                await payload.member.add_roles(help_role)
            elif payload.emoji.name == '🛠️':
                contributer_role = discord.utils.get(await guild.fetch_roles(), name='contributer')
                await payload.member.add_roles(contributer_role)


def setup(bot):
    bot.add_cog(MemberManagement(bot))
    
        




    