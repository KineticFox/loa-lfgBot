import os
import discord
import dotenv
from discord.commands import SlashCommandGroup
from discord.ext import commands, pages

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))




# The basic bot instance in a separate file should look something like this:
intents = discord.Intents.default()
intents.message_content = True  # required for prefixed commands
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)
bot.load_extension("pages")
bot.run(token)