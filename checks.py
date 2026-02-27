from discord.ext import commands
from exceptions import *

# check if in setup channel
def in_setup_channel(channel_id):
    async def predicate(ctx):
        if ctx.channel.id != channel_id:
            raise NotInSetupChannel()
        return True
    return commands.check(predicate)

# check if has exec role
def has_exec_roles(roles):
    async def predicate(ctx):
        if not any(role.name in roles for role in ctx.author.roles):
            raise MissingRequiredRole()
        return True
    return commands.check(predicate)