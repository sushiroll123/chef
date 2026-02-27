import discord
from discord.ext import commands
import logging
from checks import *
from exceptions import *
from dotenv import load_dotenv
import os
import webserver

load_dotenv()
DISCORDKEY = os.getenv('DISCORD_TOKEN')
COOKING_PASS = os.getenv('COOKING_PASS')
INTERNAL_PASS = os.getenv('INTERNAL_PASS')
FINANCE_PASS = os.getenv('FINANCE_PASS')
MARKETING_PASS = os.getenv('MARKETING_PASS')
PARTNERSHIP_PASS = os.getenv('PARTNERSHIP_PASS')
DIRECTOR_PASS = os.getenv('DIRECTOR_PASS')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

EXEC_ROLES = ["cooking", "internal", "finance", "partnership", "marketing", "director"]
ROLES_WITH_PERMS = ("exec", "temp-exec", "Admin")
EXEC_ROLE_NAME = "exec"
TEMP_EXEC_ROLE_NAME = "temp-exec"

SETUP_CHANNEL_ID = 1476166843021525098

PASSWORDS = { 
    "cooking": COOKING_PASS,
    "internal": INTERNAL_PASS,
    "finance": FINANCE_PASS,
    "marketing": MARKETING_PASS,
    "parternship": PARTNERSHIP_PASS,
    "director": DIRECTOR_PASS
}

with open('setup_instructions.txt', 'r') as f:
    SETUP_INSTRUCTIONS = f.read()

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready to cook!")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("You don't have perms lil bro")
    elif isinstance(error, commands.CommandNotFound):
        return

# messages
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # easter egg
    try:
        if "are you ready chef?" in message.content.lower():
            await message.channel.send(f"I'm ready chef {message.author.mention}!")
    except Exception as e:
        print(f"Error from on_message: {e}")

    await bot.process_commands(message)

# display list of exec roles
@bot.command()
@has_exec_roles(EXEC_ROLES)
@in_setup_channel(SETUP_CHANNEL_ID)
async def roles(ctx):
    rolls_list = EXEC_ROLES
    await ctx.send('\n'.join(rolls_list))

# mass delete messages 
@bot.command()
@commands.has_role('Admin')
async def purge(ctx):
    await ctx.channel.purge(limit=100)

# dm user setup steps
@bot.command()
@has_exec_roles(EXEC_ROLES)
@in_setup_channel(SETUP_CHANNEL_ID)
async def setup(ctx):
    await ctx.author.send(SETUP_INSTRUCTIONS)

# quick yes/no poll
@bot.command()
@commands.has_any_role("director", "Admin")
async def poll(ctx, *, question):
    embed = discord.Embed(title=question, description="yes or no")
    poll_msg = await ctx.send(embed=embed)
    await poll_msg.add_reaction("👍")
    await poll_msg.add_reaction("👎")

# removing role
@bot.command()
@has_exec_roles(EXEC_ROLES)
@in_setup_channel(SETUP_CHANNEL_ID)
async def leave(ctx, *, role_name):
    start_msg = ctx.message
    role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), ctx.author.roles)
    if role:
        await ctx.channel.send("type role name again to confirm:")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
        msg = await user_input(ctx, check, 30.0, start_msg)
        if msg is None:
            return
        
        if msg.content.lower() == role_name.lower():
            await ctx.author.remove_roles(role)
            last_msg = await ctx.channel.send(f"{ctx.author.mention} has left {role_name}!")
            await ctx.channel.purge(limit=100, after=start_msg, before=last_msg)
            await start_msg.delete()
        else:
            last_msg = await ctx.send("Role name did not match, action cancelled")
            await ctx.channel.purge(limit=100, after=start_msg, before=last_msg)
            await start_msg.delete()
    else:
        last_msg = await ctx.channel.send("You don't have that role lol")
        await ctx.channel.purge(limit=100, after=start_msg, before=last_msg)
        await start_msg.delete()

# assigning role
@bot.command()
@has_exec_roles(EXEC_ROLES)
@in_setup_channel(SETUP_CHANNEL_ID)
async def join(ctx):
    start_msg = ctx.message
    await ctx.channel.send("Which role do you want to join?")

    def check(msg):
        return msg.channel == ctx.channel and msg.author == ctx.author
    
    role_name_msg = await user_input(ctx, check, 60.0, start_msg)
    if role_name_msg is None:
        return
    role_name = role_name_msg.content
    
    role = discord.utils.find(
        lambda r: r.name.lower() == role_name.lower() and role_name.lower() in EXEC_ROLES, 
        ctx.guild.roles
        )
    
    if role in ctx.author.roles:
        last_msg = await ctx.channel.send("You already have that role greedyass")
        await ctx.channel.purge(limit=100, after=start_msg, before=last_msg)
        await start_msg.delete()
        return
    
    if role:
        await ctx.channel.send("please enter password for role:")            

        attempts = 3
        last_msg = await verify_password(ctx, check, attempts, role_name, role, 60.0, start_msg)
        if last_msg is None:
            return
    else:
        last_msg = await ctx.channel.send("Role not found, check spelling stupid. \nUse !roles for" \
                                            "list of possible roles")
    
    await ctx.channel.purge(limit=100, after=start_msg, before=last_msg)
    await start_msg.delete()
    return

# helper for assign, returns user input, deletes user message
async def user_input(ctx, check, timeout, start_msg=None):
    try:
        msg = await bot.wait_for('message', check=check, timeout=timeout)
        return msg
    except TimeoutError:
        last_msg = await ctx.channel.send("Took too long buddy...")
        if start_msg:
            await ctx.channel.purge(limit=100, after=start_msg, before=last_msg)
            await start_msg.delete()
        return
    
# helper for verify_password, checks passwords
def check_password(role_name, pswd):
    return PASSWORDS.get(role_name.lower()) == pswd
    
# helper for assign, verifies passwords
async def verify_password(ctx, check, attempts, role_name, role, time_limit, start_msg=None):
    pswd = await user_input(ctx, check, time_limit, start_msg)
    if pswd is None:
        return
    await pswd.delete()
    
    if attempts <= 0:
        return await ctx.channel.send("you have no attempts")
    
    while attempts > 0:
                if(check_password(role_name.lower(), pswd.content)):
                    temp_exec_role = discord.utils.get(ctx.author.roles, name=TEMP_EXEC_ROLE_NAME)
                    await ctx.author.add_roles(role)

                    await ctx.author.add_roles(discord.utils.get(ctx.guild.roles, name=EXEC_ROLE_NAME))
                    if temp_exec_role:
                        await ctx.author.remove_roles(temp_exec_role)

                    return await ctx.channel.send(f"{ctx.author.mention} is now a part of {role_name}!")
                else:
                    attempts -= 1
                    if attempts > 0:
                        await ctx.channel.send(f"wrong password stupid, {attempts} attempt(s) remaining:")
                        pswd = await user_input(ctx, check, time_limit, start_msg)
                        if pswd is None:
                            return
                        await pswd.delete()
                        
                    else:
                        return await ctx.channel.send("Too many incorrect attemps bro, action cancelled")

webserver.keep_alive()
bot.run(DISCORDKEY, log_handler=handler, log_level=logging.DEBUG)
