from loabot_logger import logger

async def interaction_handling(interaction, exception):
    logger.warning(f'{interaction.guild.name} -- {exception}')
    await interaction.response.send_message(f'Something went wrong -- {exception}', ephemeral=True)

async def interaction_handling_defer(interaction, exception):
    logger.warning(f'{interaction.guild.name} -- {exception}')
    await interaction.followup.send(f'Something went wrong -- {exception}', ephemeral=True)