import os
from discord.ext import commands
import discord
import dotenv


class WelcomeBot(commands.Cog):

    def __init__(self, bot) -> None:
        self.bot = bot
        self.guild = {}
        self.guestRole = {}
        self.raidRole = {}
        self.ruleChannel = {}
        self.newmember = {}
        self.channels =  [1054764326776483920] #pre defined channels in which bot listens for reactions
        self.dmchannel = 0
    
    async def setupGuild(self):
        #self.guild = discord.utils.get(self.bot.guilds, name='Raid-Trainingsgruppe')
        self.guild = discord.utils.get(self.bot.guilds, name='MrXilef')
        self.guestRole = discord.utils.get(await self.guild.fetch_roles(), name='Gast')
        self.expraidRole = discord.utils.get(await self.guild.fetch_roles(), name='raidertest') #TODO korrekten rollen namen hinterlegen exp raider
        self.lernraidRole = discord.utils.get(await self.guild.fetch_roles(), name='raidertest') #TODO korrekten rollen namen hinterlegen learning raider
        #self.raidruleChannel = discord.utils.get(self.bot.get_all_channels(), name='raidregeln-und-mehr')
        self.ruleChannel = discord.utils.get(self.bot.get_all_channels(), name='rules')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        
        self.newmember = member
        desc = f'Bevor es losgehen kann, akzeptiere bitte die Regelen in <#{self.ruleChannel.id}>\nErzähle doch bitte etwas über dich und wie dein aktueller Stand in Lost Ark ist\n viel Spaß hier auf dem Server und immer ordentlich Loot!'
        embed = discord.Embed(title=f"Wilkommen {member.display_name},", description=desc)

        wm = await member.send(embed=embed)
        print(wm.channel.id)        
        self.channels.append(int(wm.channel.id))
        self.dmchannel = int(wm.channel.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        print(payload)

        #TODO test what happens if several member join at the same time, might break following logic because im checking conditions based on variables set when a member joins, 
        # could be overwritten when new member joins and the member before hasnt finished the process
        #

        if not self.newmember:
            pass
        elif payload.channel_id not in self.channels:
            pass
        else:
            if payload.user_id == self.bot.user.id:
                pass
            else:
                member = discord.utils.get(self.guild.members, id=payload.user_id)
                #erstes if nur zum testen
                if payload.emoji.name == '\u2705': #:white_check_mark
                    await member.add_roles(self.guestRole)
                    next = await member.send('Super, wähle jetzt bitte deinen Raidtyp \nExperienced = 1️⃣ Learning = 2️⃣')
                    await next.add_reaction('1️⃣')
                    await next.add_reaction('2️⃣')

                elif payload.emoji.name == '1️⃣':
                    await member.add_roles(self.expraidRole)
                    self.newmember = {}
                    self.channels.remove(self.dmchannel)
                elif payload.emoji.name == '2️⃣':
                    await member.add_roles(self.lernraidRole)
                    self.newmember = {}
                    self.channels.remove(self.dmchannel)
                elif payload.emoji.name == '❤️': #'\u2764': #:heart:
                    await member.add_roles(self.guestRole)
                    next = await member.send('Super, wähle jetzt bitte deinen Raidtyp \nExperienced = 1️⃣ Learning = 2️⃣')
                    await next.add_reaction('1️⃣')
                    await next.add_reaction('2️⃣')

        

        

def setup(bot):
    bot.add_cog(WelcomeBot(bot))
    