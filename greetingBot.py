import os
import discord
import dotenv

dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))
intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, name='Raid-Trainigsgruppe')
    guild2 = discord.utils.get(bot.guilds, name='MrXilef')
    guest = discord.utils.get(await guild2.fetch_roles(), name='Gast')
    #roles= await guild.fetch_roles()
    raider = discord.utils.get(await guild2.fetch_roles(), name='raider')
    print(guild, guild2, raider.id, guest)
    print(bot.user.id)


@bot.event
async def on_member_join(member):
    guild = discord.utils.get(bot.guilds )
    channel = discord.utils.get(bot.get_all_channels(), name='rules')
    desc = f'Bevor es losgehen kann, akzeptiere bitte die Regelen in <#{channel.id}>\nErzähle doch bitte etwas über dich und wie dein aktueller Stand in Lost Ark ist\n viel Spaß hier auf dem Server und immer ordentlich Loot!'
    embed = discord.Embed(title=f"Wilkommen {member.display_name},", description=desc)

    wm = await member.send(embed=embed)
    
    await wm.add_reaction('\u2705')

@bot.event
async def on_raw_reaction_add(payload):
    guild = discord.utils.get(bot.guilds, name='MrXilef')
    guest = discord.utils.get(await guild.fetch_roles(), name='@gast')
    raider = discord.utils.get(await guild.fetch_roles(), name='raidertest')
    print(payload)

    if payload.user_id == bot.user.id:
        pass
    else:
        member = discord.utils.get(guild.members, id=payload.user_id)
        if payload.emoji.name == '\u2705':
            
            await member.add_roles(guest)
            next = await member.send('Ok gut wähle jetzt bitte deinen Raidtyp \nExperienced = 1️⃣ Learning = 2️⃣')
            await next.add_reaction('1️⃣')
            await next.add_reaction('2️⃣')

        elif payload.emoji.name == '1️⃣':
            await member.add_roles(raider)
        elif payload.emoji.name == '2️⃣':
            print('lern')

bot.run(token)