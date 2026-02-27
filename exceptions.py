from discord.ext import commands

class NotInSetupChannel(commands.CheckFailure):
    pass

class MissingRequiredRole(commands.CheckFailure):
    pass