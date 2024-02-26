import discord
from discord.ui.input_text import InputText
from loabot_db import LBDB

class CharModal(discord.ui.Modal):
    def __init__(self, char, role, db, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.char = char
        self.role = role
        self.db = db
        self.add_item(discord.ui.InputText(label=f'Character Name'))
        self.add_item(discord.ui.InputText(label='item level (Please only use Integer)'))
        self.db = LBDB()
        self.db.use_db()

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.guild.get_member_named(interaction.user.name)
        u_id = member.id
        table = ''.join(l for l in interaction.guild.name if l.isalnum())

        char_data = self.db.get_char_data(self.char) 
        emoji = char_data.get('char_emoji')
        ilvl: str = self.children[1].value

        if '.' in ilvl:
            try:
                int_ilvl = int(ilvl.split('.')[0])
            except ValueError as e:
                await interaction.followup.send(e, delete_after=10, ephemeral=True)
        elif  ',' in ilvl:
            try:
                int_ilvl = int(ilvl.split(',')[0])
            except ValueError as e:
                await interaction.followup.send(e, delete_after=10, ephemeral=True)
        else:
            try:
                int_ilvl = int(ilvl)
            except ValueError as e:
                await interaction.followup.send(e, delete_after=10, ephemeral=True)

        
        #res = self.db.add_chars(self.children[0].value, self.char, interaction.user.name, int_ilvl, self.role, table, u_id, emoji)
        #self.db.close()
        print(int_ilvl)
        await interaction.followup.send('res', delete_after=10, ephemeral=True)


class DateModal(discord.ui.Modal):
    def __init__(self, title: str,view) -> None:
        super().__init__(title=title)
        self.view = view
        self.add_item(discord.ui.InputText(label='New Date/Neue Zeit'))   
    
    
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        guild_name = ''.join(l for l in interaction.guild.name if l.isalnum())
        date = self.children[0].value
        embed.set_field_at(0, name='Date/Time:', value=date)

        e_dict = embed.to_dict()
        fields = e_dict.get('fields')

        db = LBDB()
        db.use_db()

        db.update_date(guild_name, fields[8].get('value'), date)
        db.close()
        await interaction.response.send_message('Datum wurde geändert/Date changed', ephemeral=True)
        await interaction.message.edit(embed=embed, view=self.view)

        
