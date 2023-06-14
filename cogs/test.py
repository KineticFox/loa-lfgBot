import discord
from discord.ext import commands

class Tester(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()
        
    @discord.slash_command(name = "hi", description = "say hi")
    async def hello(self, ctx):
        await ctx.respond(f"hello {ctx.user}")


def setup(bot):
    bot.add_cog(Tester(bot=bot))