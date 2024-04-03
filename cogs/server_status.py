import sys, os
import requests
import logging
from bs4 import BeautifulSoup
from enum import Enum
from discord.ext import tasks, commands
from discord.ext.commands import Context
from discord.commands import SlashCommandGroup, guild_only
import discord

logger = logging.getLogger('ServerStatus')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formater = logging.Formatter('%(asctime)s - %(levelname)s %(name)s:%(msg)s', '%y-%m-%d, %H:%M') 
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False

class Region(Enum):
    NAW = 0
    NAE = 1
    EUC = 2
    SA = 3

    @classmethod
    def get_region(cls, name):
        try:
            return cls[name].value
        except KeyError as e:
            print(f'error: {e}')

class ServerStatus(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()

    status = SlashCommandGroup(name='server_status', description='Commands for checking lost ark server status', guild_only=True)

    @status.command(name='get_server_status')
    @commands.cooldown(1,120, commands.BucketType.user)
    async def server_Status(self, ctx, server = discord.Option(str, choices=['NAW', 'NAE', 'EUC', 'SA'], required=True)):
        await ctx.defer()
        region_int = Region.get_region(server)

        try:
            res = requests.get('https://www.playlostark.com/de-de/support/server-status')
            res.raise_for_status()
            #loabot_logger.logger.info(res.status_code)
        except requests.exceptions.HTTPError as e:
            logger.warning(e)


        cont = res.content

        soup = BeautifulSoup(cont, 'html.parser')

        #server_name = soup.find('div', class_='ags-ServerStatus-content-responses-response ags-ServerStatus-content-responses-response--centered ags-js-serverResponse is-active', attrs={'data-index': '2'})#.find('div', class_="ags-ServerStatus-content-responses-response-server-name")
        servers = soup.select(f'div[data-index="{region_int}"]')
        #server_status_maintenance = soup.find('div', class_=f'ags-ServerStatus-content-responses-response ags-ServerStatus-content-responses-response--centered ags-js-serverResponse is-active').find('div', class_='ags-ServerStatus-content-responses-response-server-status-wrapper').find('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--maintenance")
        #server_status_good = soup.find('div', class_=f'ags-ServerStatus-content-responses-response ags-ServerStatus-content-responses-response--centered ags-js-serverResponse is-active').find('div', class_='ags-ServerStatus-content-responses-response-server-status-wrapper').find('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--good" )
        #server_status_full = soup.find('div', class_=f'ags-ServerStatus-content-responses-response ags-ServerStatus-content-responses-response--centered ags-js-serverResponse is-active').find('div', class_='ags-ServerStatus-content-responses-response-server-status-wrapper').find('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--full" )
        #server_status_busy = soup.find('div', class_=f'ags-ServerStatus-content-responses-response ags-ServerStatus-content-responses-response--centered ags-js-serverResponse is-active').find('div', class_='ags-ServerStatus-content-responses-response-server-status-wrapper').find('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--busy" )
        #, data-index=2
        good_servers = []
        maintenance_servers = []
        full_servers= []
        busy_servers = []

        server_list = []

        for s in servers:
            server_list = s.find_all('div', class_="ags-ServerStatus-content-responses-response-server")

        for s in server_list:
            if s.findChild('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--good") is not None:
                good_servers.append(s.findChild('div', class_="ags-ServerStatus-content-responses-response-server-name").get_text().strip())
            
            elif s.findChild('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--maintenance") is not None:
                maintenance_servers.append(s.findChild('div', class_="ags-ServerStatus-content-responses-response-server-name").get_text().strip())
            
            elif s.findChild('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--full") is not None:
                full_servers.append(s.findChild('div', class_="ags-ServerStatus-content-responses-response-server-name").get_text().strip())
            
            elif s.findChild('div',class_="ags-ServerStatus-content-responses-response-server-status ags-ServerStatus-content-responses-response-server-status--busy") is not None:
                busy_servers.append(s.findChild('div', class_="ags-ServerStatus-content-responses-response-server-name").get_text().strip())




        server_name_list_good = []
        server_name_list_maintenance = []
        server_name_list_busy = []
        server_name_list_full = []

        for i in range(3):
            if len(maintenance_servers) != 0:
                for ms in maintenance_servers:
                    server_name_list_maintenance.append(ms)
                    maintenance_servers = []
            elif len(good_servers) != 0 :
                for gs in good_servers:
                    server_name_list_good.append(gs)
                    good_servers = []
            elif len(busy_servers) != 0 :
                for bs in busy_servers:
                    server_name_list_busy.append(bs)
                    busy_servers = []
            elif len(full_servers) != 0 :
                for fs in full_servers:
                    server_name_list_full.append(fs)
                    full_servers = []



        last_update = soup.find('div', class_="ags-ServerStatus-content-lastUpdated").get_text()

        update_clean = last_update.strip()

        await ctx.followup.send(f'Serverstatus for **{server}**:\n\n:white_check_mark: ({len(server_name_list_good)}): {", ".join(server_name_list_good)}\n:x: ({len(server_name_list_full)}): {",".join(server_name_list_full)}\n:yellow_circle: ({len(server_name_list_busy)}): {",".join(server_name_list_busy)}\n:tools: ({len(server_name_list_maintenance)}): {",".join(server_name_list_maintenance)}\n\n {last_update}', ephemeral=True, delete_after=120)



def setup(bot):
    bot.add_cog(ServerStatus(bot))