from discord.ext import tasks, commands
from discord.ext.commands import Context
from discord.commands import SlashCommandGroup, guild_only
import discord


class ShoutoutTask(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        #self.send_message.start()
        super().__init__()
    
    def cog_unload(self) -> None:
        self.send_message.cancel()

    shoutout = SlashCommandGroup(name='message_tasks', description='Tasks for sending repeating messages in given interval', guild_only=True, checks=[commands.is_owner()])


    @tasks.loop(seconds=2, count=2)
    async def send_message(self, ctx: Context, message:str, delte_counter: int):
        await ctx.send(message, delete_after=3540)


    async def stopping(self):
        print('stopped task')
        self.send_message.stop()


    @shoutout.command(name='start_shoutout')
    @commands.is_owner()
    async def start_shoutout(self, ctx, repetition:discord.Option(int,'repetition'), message: discord.Option(str,'message')): # type: ignore
        await ctx.respond('started task', ephemeral=True)
        self.send_message.count = repetition
        await self.send_message.start(ctx, message, repetition)

 
    @shoutout.command(name='stop_shoutout')
    @commands.is_owner()
    async def stop_shoutout(self,ctx):
        await self.stopping()
        await ctx.respond('stopped task', ephemeral=True)

    @shoutout.command(name='edit_time')
    async def edit_time(self, ctx, time: discord.Option(input_type=int, name='time', description='Numbers between 1 & 24')): # type: ignore
        self.send_message.change_interval(hours=time)

        await ctx.respon(f'change interval to {time}', ephemeral=True)


def setup(bot):
    bot.add_cog(ShoutoutTask(bot))