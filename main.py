import os
import discord
from discord.ext import commands
import dotenv

import logging


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formater = logging.Formatter('%(name)s:%(levelname)s: %(msg)s')
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False


def run():

    dotenv.load_dotenv()
    token = str(os.getenv("TOKEN"))
    intents = discord.Intents.all()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)


    @bot.event
    async def on_ready():
        logger.info(f"We have logged in as {bot.user}")
    
    @bot.command()
    #async def enablecommands(ctx, command: discord.Option(str, choices=cogs, required=True)):
    async def load(ctx, extension):
        bot.load_extension(f'cogs.{extension}')
        if extension == 'greetingBot':
            greeting = bot.get_cog('WelcomeBot')
            await greeting.setupGuild()
        elif extension == 'loabot':
            logger.info('DB setup')
        await bot.sync_commands(method='auto')
        await ctx.send(f'cog loaded, it may take while until the slashcommands are available', delete_after=20)
    
    @bot.command()
    async def reload(ctx, extension):
        bot.reload_extension(f'cogs.{extension}')
        if extension == 'greetingBot':
            greeting = bot.get_cog('WelcomeBot')
            await greeting.setupGuild()
        await ctx.send(f'cog  reloaded', delete_after=30)
    
    @bot.command()
    async def unload(ctx, extension):
        bot.unload_extension(f'cogs.{extension}')
        await ctx.send('cog unloaded', delete_after=30)
    
    @bot.command()
    async def showextensions(ctx):

        extensions = []
        for e in bot.extensions:
            extensions.append(e)
        
        await ctx.send('Loaded extensions: ' + ' '.join(extensions), delete_after=60)

    
    bot.run(token)

if __name__=="__main__":
    run()