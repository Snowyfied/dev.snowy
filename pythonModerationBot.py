import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Saves the warns: {guild_id: {user_id: [(warn_time, warn_number), ...]}}
warns = {}

# Anti-spam setup
recent_messages = {}

ANTI_RAID_ACCOUNT_AGE_DAYS = 30
WARN_DURATION_DAYS = 7

@bot.event
async def on_ready():
    print(f'Bot online als {bot.user}')
    remove_old_warns.start()

# Anti-Raid: nur Accounts >30 Tage

@bot.event
async def on_member_join(member):
    account_age = datetime.utcnow() - member.created_at
    if account_age < timedelta(days=ANTI_RAID_ACCOUNT_AGE_DAYS):
        try:
            await member.kick(reason="Account zu neu – Anti-Raid")
        except:
            pass

# 
# Anti-Spam
# 
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = datetime.utcnow()
    user_id = message.author.id
    if user_id not in recent_messages:
        recent_messages[user_id] = []
    recent_messages[user_id].append(now)

    # Nachrichten älter als 5 Sekunden rauswerfen
    recent_messages[user_id] = [t for t in recent_messages[user_id] if (now - t).seconds < 5]

    if len(recent_messages[user_id]) > 5:  # >5 Message after 5 seconds -> Timeout
        try:
            await message.author.timeout(duration=60, reason="Spam")
        except:
            pass

    await bot.process_commands(message)

# Moderations Commands

@bot.tree.command(name="kick", description="Kicke einen User")
@app_commands.describe(user="User zum kicken")
async def kick(interaction: discord.Interaction, user: discord.Member):
    try:
        await user.kick()
        await interaction.response.send_message(f"{user} has been kicked.", ephemeral=True)
    except:
        await interaction.response.send_message("Fehler with click.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a user")
@app_commands.describe(user="User to Ban")
async def ban(interaction: discord.Interaction, user: discord.Member):
    try:
        await user.ban()
        await interaction.response.send_message(f"{user} wurde gebannt.", ephemeral=True)
    except:
        await interaction.response.send_message("Fehler beim Bannen.", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout einen User")
@app_commands.describe(user="User zum timeouten")
async def timeout(interaction: discord.Interaction, user: discord.Member):
    try:
        await user.timeout(duration=300)
        await interaction.response.send_message(f"{user} wurde für 5 Minuten gemuted.", ephemeral=True)
    except:
        await interaction.response.send_message("Fehler beim Timeout.", ephemeral=True)


# Warn System
@bot.tree.command(name="warn", description="Gebe einem User einen Warn")
@app_commands.describe(user="User der gewarnt wird", level="Warn-Level 1-3")
async def warn(interaction: discord.Interaction, user: discord.Member, level: int):
    guild_id = interaction.guild.id
    if guild_id not in warns:
        warns[guild_id] = {}
    if user.id not in warns[guild_id]:
        warns[guild_id][user.id] = []

    warns[guild_id][user.id].append((datetime.utcnow(), level))
    
    # this Checks if the user has 3 warns
    active_warns = [w for w in warns[guild_id][user.id] if (datetime.utcnow() - w[0]).days < WARN_DURATION_DAYS]
    if sum([1 for w in active_warns if w[1] == 3]) >= 1 or len(active_warns) >= 3:
        try:
            await user.ban(reason="3 Warns erreicht")
            await interaction.response.send_message(f"{user} wurde gebannt (3 Warns erreicht).", ephemeral=True)
            warns[guild_id][user.id] = []  # Reset nach Ban
        except:
            await interaction.response.send_message("Fehler beim Bannen nach Warns.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{user} wurde gewarnt (Level {level}).", ephemeral=True)

# This deletes old Warns
@tasks.loop(hours=24)
async def remove_old_warns():
    now = datetime.utcnow()
    for guild_id in warns:
        for user_id in warns[guild_id]:
            warns[guild_id][user_id] = [w for w in warns[guild_id][user_id] if (now - w[0]).days < WARN_DURATION_DAYS]


# With That you start the bot
bot.run("DEIN_BOT_TOKEN")
