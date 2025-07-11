import os
import json
import discord
from discord import app_commands
from discord.utils import get
from dotenv import load_dotenv
from discord.errors import Forbidden
import requests
import asyncio
from datetime import datetime, timezone
import uuid
import random
import string
from pymongo import MongoClient
import io

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["your_database"]
users_collection = db["users"]
users_collection = db["users"]
WARNINGS_FILE = "warnings.json"
active_bugs = {}
HEARTBEAT_URL = "https://uptime.betterstack.com/api/v1/heartbeat/cRxyZzYTNESifDhYL22mBzoJ"

BUG_REPORT_CHANNEL_NAME = "bug-reports"  # Change this to match your bug report channel name

REQUIRED_FIELDS = [
    "bug title:",
    "steps to reproduce:",
    "expected result:",
    "actual result:",
    "platform:"
]

def load_warnings():
    global user_warnings
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, "r") as f:
            user_warnings = json.load(f)
    else:
        user_warnings = {}

# Save warnings to JSON file
def save_warnings():
    with open(WARNINGS_FILE, "w") as f:
        json.dump(user_warnings, f, indent=4)

def is_valid_bug_report(content: str) -> bool:
    content_lower = content.lower()
    return all(field in content_lower for field in REQUIRED_FIELDS)

def generate_bug_id() -> str:
    return "bug-" + ''.join(random.choices(string.digits, k=4))

FAQ_TEXT = """
**Geo Interactive FAQ**

**Q: What is Geo Interactive?**  
A: Geo Interactive is a creative and independent game development project led by a passionate solo developer dedicated to exploring new ideas and pushing the boundaries of interactive storytelling. Rather than being a traditional company, Geo Interactive represents a dynamic portfolio of original games across multiple genres. The focus is on creating engaging, thoughtful experiences that emphasize meaningful player choices, innovative mechanics, and immersive worlds.

**Q: What types of games does Geo Interactive develop?**  
A: Our projects span a variety of genres to cater to different player interests. This includes cozy pixel art adventures that evoke nostalgia, browser-based strategy games that challenge your decision-making skills, simulation games that provide rich, interactive systems, roleplaying experiences filled with deep storytelling, trading card games designed with unique mechanics, and open-world life sims where players can shape their own stories. We love experimenting with different game styles and combining elements to create fresh, memorable gameplay.

**Q: How are your games developed?**  
A: Geo Interactive games are built using a mix of custom-developed tools alongside existing game engines and frameworks. This hybrid approach allows for flexibility in design and technical innovation, enabling the creation of games that are both accessible to a broad audience and rich in detail. The development process is driven by creativity and iteration, with a strong focus on quality and player experience.

**Q: Is Geo Interactive a registered company or studio?**  
A: No, Geo Interactive is not a formally registered company or traditional game studio. Instead, it is a personal and evolving project of an indie developer who manages everything from design and programming to art and storytelling. This independence allows for greater creative freedom and the ability to rapidly explore new concepts without corporate constraints.

**Q: What motivates Geo Interactive’s work?**  
A: At the heart of Geo Interactive is a passion for game design, storytelling, and community engagement. The developer is motivated by curiosity, the joy of crafting unique gameplay experiences, and a desire to connect with players through worlds that are fun, meaningful, and memorable. Each game is an opportunity to experiment, learn, and share a piece of that creative journey.

**Q: What is the ultimate goal of Geo Interactive?**  
A: The goal is to continue growing a diverse portfolio of games that players love to explore and enjoy. Moving forward, Geo Interactive is focusing more on **quality over quantity** — meaning fewer updates and new projects, but with much deeper, more polished, and fun gameplay experiences. This approach ensures each release offers meaningful content and a satisfying experience, rather than rushing frequent updates. Whether it’s diving into a richly crafted pixel art world, collecting creatures with unique traits, or making impactful choices in open-ended simulations, Geo Interactive aims to create games that truly resonate and stand the test of time.

**Q: Can I support or get involved with Geo Interactive?**  
A: Absolutely! Geo Interactive welcomes community involvement and collaboration. There are several ways to get involved:

- **Partner Program:** Designed for those who want to collaborate closely on projects, contribute ideas, or share resources.  
- **Affiliate Program:** For supporters who want to help promote Geo Interactive games and benefit from shared opportunities.  
- **Collaboration Opportunities:** Open to creatives like artists, writers, musicians, and developers interested in contributing to current or future projects.

To learn more about joining any of these programs, please reach out through our official contact channels. Geo Interactive values every form of support and looks forward to building a strong community around its games.

**Q: What does “indie” mean in the context of Geo Interactive?**  
A: "Indie" stands for "independent." Geo Interactive is an indie project, meaning it is created by a solo developer or small team without backing from large publishers or companies. This independence allows full creative freedom, letting the developer explore unique ideas, artistic styles, and gameplay mechanics without commercial pressures. Indie games often bring fresh, innovative experiences to players.

**Q: How can I stay updated on Geo Interactive projects?**  
A: Stay connected by following Geo Interactive on social media platforms, subscribing to newsletters, or joining official community groups if available. This is the best way to receive news about upcoming releases, updates, and ways to participate.
"""

user_warnings = {}

async def send_heartbeat():
    while True:
        try:
            response = requests.get(HEARTBEAT_URL)
            print("✅ Heartbeat sent:", response.status_code)
        except Exception as e:
            print("❌ Failed to send heartbeat:", e)
        await asyncio.sleep(300)  # Every 5 minutes (adjust if needed)


# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
raw_guilds = os.getenv('ALLOWED_GUILD_IDS')
OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

if not TOKEN:
    raise Exception("DISCORD_BOT_TOKEN is missing in .env")
if not raw_guilds:
    raise Exception("ALLOWED_GUILD_IDS is missing in .env")

ALLOWED_GUILDS = {int(gid.strip()) for gid in raw_guilds.split(',')}

# Constants
SUPPORT_ROLE_NAME = "Support"
ESCALATION_ROLE_NAME = "Management+"  # Change to match your actual role name
LEGAL_ROLE_NAME = "Legal Team"  # Change if your Legal role has a different name
TICKET_CATEGORY_NAME = "Tickets"
TICKET_LOG_CHANNEL_NAME = "ticket-logs"
TICKET_DATA_FILE = "tickets.json"
FAQ_CHANNEL_ID = int(os.getenv('FAQ_CHANNEL_ID'))


def has_safeguarding_role(member: discord.Member) -> bool:
    return any(role.name == "Safeguarding Team" for role in member.roles)
def has_support_role(member: discord.Member) -> bool:
    return any(role.name == "Support" for role in member.roles)

def has_management_role(member: discord.Member) -> bool:
    return any(role.name == "Management+" for role in member.roles)

# Load ticket data or create new
if os.path.exists(TICKET_DATA_FILE):
    with open(TICKET_DATA_FILE, "r") as f:
        ticket_data = json.load(f)
else:
    ticket_data = {"last_ticket_number": 0}

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        for guild_id in ALLOWED_GUILDS:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

client = MyClient()
client.owner_id = 774016490348609567
def guild_check(interaction: discord.Interaction) -> bool:
    return interaction.guild_id in ALLOWED_GUILDS

def save_ticket_data():
    with open(TICKET_DATA_FILE, "w") as f:
        json.dump(ticket_data, f, indent=4)

@client.tree.command(name="ping", description="Replies with Pong!")
@app_commands.check(guild_check)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@ping.error
async def ping_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("This server can't use this command.", ephemeral=True)

@client.tree.command(name="ticket", description="Open a support ticket")
@app_commands.check(guild_check)
async def ticket(interaction: discord.Interaction):
    guild = interaction.guild
    support_role = get(guild.roles, name=SUPPORT_ROLE_NAME)

    if support_role is None:
        await interaction.response.send_message(
            f"Role {SUPPORT_ROLE_NAME} not found.", ephemeral=True)
        return

    # Ticket category
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if category is None:
        category = await guild.create_category(TICKET_CATEGORY_NAME)

    # Increment ticket number
    ticket_data["last_ticket_number"] += 1
    ticket_number = ticket_data["last_ticket_number"]
    save_ticket_data()

    channel_name = f"ticket-{ticket_number}"

    # Permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category
    )

    await ticket_channel.send(
        f"{interaction.user.mention} Thank you for contacting {support_role.mention}! A team member will be with you shortly.")

    await interaction.response.send_message(
        f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

    # Log to mod channel
    log_channel = discord.utils.get(guild.text_channels, name=TICKET_LOG_CHANNEL_NAME)
    if log_channel:
        await log_channel.send(
            f"📩 Ticket #{ticket_number} opened by {interaction.user.mention} ({interaction.user}) in {ticket_channel.mention}"
        )

@client.tree.command(name="close", description="Close your current ticket")
@app_commands.check(guild_check)
async def close(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
        return

    ticket_number = interaction.channel.name.split("-")[-1]
    await interaction.response.send_message("Closing ticket...", ephemeral=True)

    # Log to mod channel
    log_channel = discord.utils.get(interaction.guild.text_channels, name=TICKET_LOG_CHANNEL_NAME)
    if log_channel:
        await log_channel.send(
            f"✅ Ticket #{ticket_number} closed by {interaction.user.mention} in #{interaction.channel.name}"
        )

    await interaction.channel.delete()

@client.tree.command(name="close_request", description="Request to close this ticket")
@app_commands.check(guild_check)
async def close_request(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
        return

    support_role = get(interaction.guild.roles, name=SUPPORT_ROLE_NAME)
    if support_role is None:
        await interaction.response.send_message(f"Role {SUPPORT_ROLE_NAME} not found in this server.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"Your close request has been sent to {support_role.mention}. A staff member will review it shortly.",
        ephemeral=True
    )

    # Notify support role in the ticket channel
    await interaction.channel.send(
        f"{support_role.mention}, {interaction.user.mention} has requested to close this ticket."
    )

@client.tree.command(name="close_all", description="Close all open tickets in this server")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
async def close_all(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    category = discord.utils.get(interaction.guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        await interaction.followup.send("No ticket category found.", ephemeral=True)
        return

    ticket_channels = [ch for ch in category.channels if ch.name.startswith("ticket-")]
    count = 0
    for ch in ticket_channels:
        try:
            await ch.delete()
            count += 1
        except Forbidden:
            await interaction.followup.send(f"Missing permission to delete {ch.mention}", ephemeral=True)
    await interaction.followup.send(f"Closed {count} ticket(s).", ephemeral=True)

@client.tree.command(name="claim", description="Claim this ticket")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
async def claim(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
        return
    await interaction.response.send_message(f"{interaction.user.mention} has claimed this ticket.", ephemeral=False)
    # Optionally, you can store claims in a dict or DB if you want

@client.tree.command(name="add_user", description="Add a user to this ticket")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
@app_commands.describe(user="User to add to the ticket")
async def add_user(interaction: discord.Interaction, user: discord.Member):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
        return
    try:
        await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"{user.mention} has been added to the ticket.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to add user: {e}", ephemeral=True)

@client.tree.command(name="remove_user", description="Remove a user from this ticket")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
@app_commands.describe(user="User to remove from the ticket")
async def remove_user(interaction: discord.Interaction, user: discord.Member):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
        return
    try:
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"{user.mention} has been removed from the ticket.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to remove user: {e}", ephemeral=True)

@client.tree.command(name="ticket_info", description="Show info about this ticket")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
async def ticket_info(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)
        return

    ticket_number = interaction.channel.name.split("-")[-1]

    # Find who created the ticket by checking permission overwrites (first user with read permission)
    creator = None
    for target, overwrite in interaction.channel.overwrites.items():
        if isinstance(target, discord.Member):
            if overwrite.read_messages:
                creator = target
                break

    embed = discord.Embed(title=f"Ticket #{ticket_number} info", color=discord.Color.blue())
    embed.add_field(name="Channel", value=interaction.channel.mention)
    embed.add_field(name="Ticket Number", value=ticket_number)
    embed.add_field(name="Creator", value=creator.mention if creator else "Unknown")
    embed.add_field(name="Support Role", value=SUPPORT_ROLE_NAME)
    await interaction.response.send_message(embed=embed, ephemeral=True) 

@client.tree.command(name="escalate", description="Escalate this ticket to management")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
@app_commands.describe(reason="Reason for escalating the ticket")
async def escalate(interaction: discord.Interaction, reason: str = "No reason provided"):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
        return

    # Find the escalation role
    role = discord.utils.get(interaction.guild.roles, name=ESCALATION_ROLE_NAME)
    if not role:
        await interaction.response.send_message(f"Escalation role '{ESCALATION_ROLE_NAME}' not found.", ephemeral=True)
        return

    await interaction.channel.send(f"🚨 Ticket escalated by {interaction.user.mention} — {role.mention}\n**Reason:** {reason}")
    await interaction.response.send_message("Ticket escalated.", ephemeral=True)

@client.tree.command(name="el", description="Escalate this ticket to the legal team")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
@app_commands.describe(reason="Reason for escalating to legal")
async def el(interaction: discord.Interaction, reason: str = "No reason provided"):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=LEGAL_ROLE_NAME)
    if not role:
        await interaction.response.send_message(f"Legal role '{LEGAL_ROLE_NAME}' not found.", ephemeral=True)
        return

    # Send alert in the ticket channel
    await interaction.channel.send(f"⚖️ Ticket escalated to **Legal** by {interaction.user.mention} — {role.mention}\n**Reason:** {reason}")
    await interaction.response.send_message("Ticket escalated to Legal.", ephemeral=True)

    # DM the owner
    owner = await client.fetch_user(OWNER_ID)
    try:
        await owner.send(
            f"🚨 A ticket in **{interaction.guild.name}** was escalated to Legal by {interaction.user.mention}.\n"
            f"**Channel:** {interaction.channel.name}\n"
            f"**Reason:** {reason}\n"
            f"**Link:** https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}"
        )
    except discord.Forbidden:
        print("Failed to send DM to owner.")

@client.tree.command(name="rename_ticket", description="Rename this ticket channel.")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
@app_commands.describe(new_name="The new name for the ticket channel")
async def rename_ticket(interaction: discord.Interaction, new_name: str):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("You can only rename ticket channels.", ephemeral=True)
        return

    new_name = new_name.lower().replace(" ", "-")
    await interaction.channel.edit(name=new_name)
    await interaction.response.send_message(f"✏️ Ticket renamed to {new_name}.", ephemeral=False)

@client.tree.command(name="help", description="Show help information.")
async def help_command(interaction: discord.Interaction):
    help_text = """
**Available Commands:**
• /help - Show this help message.
• /pingtest - Check the bot's latency.
• /ticket - Create a new support ticket.
• /close - Close the current ticket.
• /reopen - Reopen a closed ticket.
• /rename_ticket - Rename the ticket channel.
• /el - Escalate the ticket to legal team.
• /escalate - Escalate the ticket to management.
(And more...)

*Use these commands in your server's ticket channels or supported servers.*
"""
    await interaction.response.send_message(help_text, ephemeral=True)

@client.tree.command(name="pingtest", description="Check bot latency.")
async def pingtest(interaction: discord.Interaction):
    latency = round(client.latency * 1000)  # Convert to ms
    await interaction.response.send_message(f"Ping Test Latency: {latency}ms", ephemeral=False)



# ---------------------------------
# 1. Ban a user for Safeguarding
# ---------------------------------
@client.tree.command(name="ban_safeguard", description="Ban a user for Safeguarding with reason and optional unban date.")
@app_commands.describe(
    user="User to ban",
    reason="Reason for the ban",
    unban_date="Optional unban date (YYYY-MM-DD)"
)
async def ban_safeguard(interaction: discord.Interaction, user: discord.Member, reason: str, unban_date: str = None):
    if not has_safeguarding_role(interaction.user):
        await interaction.response.send_message("You must have the Safeguarding role to use this command.", ephemeral=True)
        return

    unban_dt = None
    if unban_date:
        try:
            unban_dt = datetime.strptime(unban_date, "%Y-%m-%d")
            if unban_dt < datetime.utcnow():
                await interaction.response.send_message("Unban date cannot be in the past.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Invalid unban date format! Use YYYY-MM-DD.", ephemeral=True)
            return

    appeal_server_invite = "https://geointeractive.online/appeal"  # Replace with your actual invite link

    dm_message = (
        f"You have been banned from **{interaction.guild.name}** for Safeguarding reasons.\n"
        f"Reason: {reason}\n"
        f"Unban date: {unban_date or 'No unban date specified.'}\n\n"
        f"If you believe this was a mistake or wish to appeal, please join the appeal server here:\n{appeal_server_invite}"
    )

    # Attempt to send DM before banning
    try:
        await user.send(dm_message)
    except Exception:
        # DM failed, possibly user has DMs off; continue anyway
        pass

    reason_full = f"Safeguarding | {reason}"
    if unban_dt:
        reason_full += f" | Unban on {unban_date}"

    try:
        await user.ban(reason=reason_full)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to ban this user.", ephemeral=True)
        return
    except discord.HTTPException:
        await interaction.response.send_message("Failed to ban user due to an error.", ephemeral=True)
        return

    await interaction.response.send_message(f"{user.mention} has been banned for Safeguarding.\nReason: {reason}\nUnban date: {unban_date or 'None'}")


# ---------------------------------
# 2. Unban a user
# ---------------------------------
@client.tree.command(name="unban_safeguard", description="Unban a user previously banned for Safeguarding.")
@app_commands.describe(
    user="The full username with discriminator (e.g. User#1234) to unban"
)
async def unban_safeguard(interaction: discord.Interaction, user: str):
    if not has_safeguarding_role(interaction.user):
        await interaction.response.send_message("You must have the Safeguarding role to use this command.", ephemeral=True)
        return

    banned_users = await interaction.guild.bans()
    try:
        user_name, user_discrim = user.split('#')
    except ValueError:
        await interaction.response.send_message("Please provide the username in the format Name#1234.", ephemeral=True)
        return

    for ban_entry in banned_users:
        banned_user = ban_entry.user
        if (banned_user.name, banned_user.discriminator) == (user_name, user_discrim):
            try:
                await interaction.guild.unban(banned_user)
            except discord.Forbidden:
                await interaction.response.send_message("I do not have permission to unban this user.", ephemeral=True)
                return
            except discord.HTTPException:
                await interaction.response.send_message("Failed to unban user due to an error.", ephemeral=True)
                return

            # Send DM to user after unbanning
            try:
                dm_message = (
                    f"Hello {banned_user.name},\n\n"
                    f"You have been unbanned from **{interaction.guild.name}**.\n"
                    f"Welcome back! You can now rejoin the server."
                )
                await banned_user.send(dm_message)
            except Exception:
                # User DMs might be closed, just ignore
                pass

            await interaction.response.send_message(f"Unbanned {banned_user.mention} and sent a DM notification.")
            return

    await interaction.response.send_message(f"User `{user}` not found in the ban list.", ephemeral=True)


# ---------------------------------
# 3. View ban info
# ---------------------------------
@client.tree.command(name="ban_info", description="View ban information for a user.")
@app_commands.describe(
    user="The full username with discriminator (e.g. User#1234)"
)
async def ban_info(interaction: discord.Interaction, user: str):
    if not has_safeguarding_role(interaction.user):
        await interaction.response.send_message("You must have the Safeguarding role to use this command.", ephemeral=True)
        return

    banned_users = await interaction.guild.bans()
    try:
        user_name, user_discrim = user.split('#')
    except ValueError:
        await interaction.response.send_message("Please provide the username in the format Name#1234.", ephemeral=True)
        return

    for ban_entry in banned_users:
        banned_user = ban_entry.user
        if (banned_user.name, banned_user.discriminator) == (user_name, user_discrim):
            reason = ban_entry.reason or "No reason provided"
            await interaction.response.send_message(f"Ban info for {banned_user.mention}:\nReason: {reason}")
            return

    await interaction.response.send_message(f"User `{user}` not found in the ban list.", ephemeral=True)

# ---------------------------------
# 4. List all banned users
# ---------------------------------
@client.tree.command(name="list_bans", description="List all banned users in the server.")
async def list_bans(interaction: discord.Interaction):
    if not has_safeguarding_role(interaction.user):
        await interaction.response.send_message("You must have the Safeguarding role to use this command.", ephemeral=True)
        return

    banned_users = await interaction.guild.bans()
    if not banned_users:
        await interaction.response.send_message("No users are currently banned.", ephemeral=True)
        return

    msg = "Currently banned users:\n"
    for ban_entry in banned_users:
        user = ban_entry.user
        reason = ban_entry.reason or "No reason"
        msg += f"- {user.name}#{user.discriminator} | Reason: {reason}\n"

    # Make sure message doesn't exceed Discord limits
    if len(msg) > 1900:
        msg = msg[:1900] + "\n...[truncated]"

    await interaction.response.send_message(msg, ephemeral=True)

# ---------------------------------
# 5. Report a safeguarding concern (open to all)
# ---------------------------------
@client.tree.command(name="safeguard_report", description="Report a safeguarding concern or incident.")
@app_commands.describe(
    user="User involved in the concern",
    details="Details of the safeguarding concern"
)
async def safeguard_report(interaction: discord.Interaction, user: discord.Member, details: str):
    mod_channel = discord.utils.get(interaction.guild.text_channels, name="safeguarding-logs")
    if mod_channel:
        embed = discord.Embed(title="New Safeguarding Report", color=0xff0000, timestamp=datetime.utcnow())
        embed.add_field(name="Reported User", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Reported By", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        embed.add_field(name="Details", value=details, inline=False)
        await mod_channel.send(embed=embed)

        await interaction.response.send_message(f"Safeguarding report about {user.mention} has been logged.", ephemeral=True)
    else:
        await interaction.response.send_message("Safeguarding logs channel not found. Please create a #safeguarding-logs channel.", ephemeral=True)    

# In-memory report store (replace with DB or JSON for persistence)
active_reports = {}

@client.tree.command(name="report", description="Report a user to the moderators.")
@app_commands.describe(
    user="The user you're reporting",
    reason="Reason for reporting the user"
)
async def report(interaction: discord.Interaction, user: discord.Member, reason: str):
    report_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow()

    # Prepare embed
    embed = discord.Embed(
        title="📢 New User Report",
        color=0xff0000,
        timestamp=timestamp
    )
    embed.add_field(name="Report ID", value=report_id, inline=False)
    embed.add_field(name="Reported User", value=f"{user} ({user.id})", inline=False)
    embed.add_field(name="Reported By", value=f"{interaction.user} ({interaction.user.id})", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    # Send to mod channel
    mod_channel = discord.utils.get(interaction.guild.text_channels, name="reports")
    if mod_channel:
        await mod_channel.send(embed=embed)
    else:
        await interaction.response.send_message("Report channel not found.", ephemeral=True)
        return

    # Save to active reports
    active_reports[report_id] = {
        "user_id": user.id,
        "reporter_id": interaction.user.id,
        "reason": reason,
        "timestamp": timestamp,
        "claimed_by": None,
        "resolved": False
    }

    # Send DM confirmation
    try:
        dm_embed = embed.copy()
        dm_embed.title = "📝 Your Report Has Been Submitted"
        await interaction.user.send(embed=dm_embed)
    except Exception:
        pass  # Ignore DM failure

    await interaction.response.send_message("✅ Your report has been submitted.", ephemeral=True)



@client.tree.command(name="claim_report", description="Claim a report to handle it.")
@app_commands.describe(report_id="The ID of the report you want to claim")
async def claim_report(interaction: discord.Interaction, report_id: str):
    if not has_support_role(interaction.user):
        await interaction.response.send_message("❌ Only Support team members can claim reports.", ephemeral=True)
        return

    report = active_reports.get(report_id)
    if not report:
        await interaction.response.send_message("⚠️ Invalid report ID.", ephemeral=True)
        return

    if report.get("claimed_by"):
        claimed_by = report["claimed_by"]
        # Try to fetch the user mention
        user = interaction.guild.get_member(claimed_by)
        if not user:
            try:
                user = await interaction.guild.fetch_member(claimed_by)
            except discord.NotFound:
                user = None
        mention = user.mention if user else f"<@{claimed_by}>"
        await interaction.response.send_message(f"⚠️ This report is already claimed by {mention}.", ephemeral=True)
        return

    report["claimed_by"] = interaction.user.id

    # DM the reporter
    reporter = interaction.guild.get_member(report["reporter_id"])
    if reporter is None:
        try:
            reporter = await interaction.guild.fetch_member(report["reporter_id"])
        except discord.NotFound:
            reporter = None

    if reporter:
        try:
            await reporter.send(
                f"📌 Your report (ID: `{report_id}`) has been **claimed** by **{interaction.user.display_name}**.\n"
                "They are currently reviewing your report."
            )
        except discord.Forbidden:
            pass  # Reporter DMs closed, ignore

    # Confirmation to claimer
    await interaction.response.send_message(f"✅ You have claimed report `{report_id}`.", ephemeral=True)

    # Log claim in mod channel
    mod_channel = discord.utils.get(interaction.guild.text_channels, name="reports")
    if mod_channel:
        await mod_channel.send(
            f"🛡️ Support member {interaction.user.mention} has claimed report `{report_id}`."
        )



@client.tree.command(name="update_report", description="Send an update to the reporter of a report.")
@app_commands.describe(
    report_id="The ID of the report to update",
    update_message="The message to send to the reporter"
)
async def update_report(interaction: discord.Interaction, report_id: str, update_message: str):
    if not (has_support_role(interaction.user) or has_management_role(interaction.user)):
        await interaction.response.send_message("❌ You don't have permission to update reports.", ephemeral=True)
        return

    report = active_reports.get(report_id)
    if not report:
        await interaction.response.send_message("⚠️ Invalid report ID.", ephemeral=True)
        return

    reporter = interaction.guild.get_member(report["reporter_id"])
    if not reporter:
        await interaction.response.send_message("⚠️ Reporter not found in server.", ephemeral=True)
        return

    # Send the update to the reporter via DM
    try:
        await reporter.send(
            f"📢 Update on your report (ID: `{report_id}`):\n"
            f"**{update_message}**\n\n"
            f"— from {interaction.user.display_name}"
        )
    except:
        await interaction.response.send_message("❌ Could not DM the reporter. They may have DMs off.", ephemeral=True)
        return

    await interaction.response.send_message(f"✅ Update sent to the reporter of report `{report_id}`.", ephemeral=True)

    mod_channel = discord.utils.get(interaction.guild.text_channels, name="reports")
    if mod_channel:
        await mod_channel.send(f"✉️ {interaction.user.mention} sent an update to report `{report_id}`:\n> {update_message}")



@client.tree.command(name="resolve_report", description="Resolve a report.")
@app_commands.describe(
    report_id="The ID of the report you want to resolve",
    resolution="How the issue was resolved"
)
async def resolve_report(interaction: discord.Interaction, report_id: str, resolution: str):
    if not has_management_role(interaction.user):
        await interaction.response.send_message("❌ Only Management+ can resolve reports.", ephemeral=True)
        return

    report = active_reports.get(report_id)
    if not report:
        await interaction.response.send_message("⚠️ Invalid report ID.", ephemeral=True)
        return

    if report["resolved"]:
        await interaction.response.send_message("⚠️ This report is already resolved.", ephemeral=True)
        return

    report["resolved"] = True
    report["resolution"] = resolution

    # Try to get reporter by ID — fallback to fetch if not cached
    reporter = interaction.guild.get_member(report["reporter_id"])
    if reporter is None:
        try:
            reporter = await interaction.guild.fetch_member(report["reporter_id"])
        except discord.NotFound:
            reporter = None

    # Notify reporter if possible
    if reporter:
        try:
            await reporter.send(
                f"📢 Your report (ID: `{report_id}`) has been resolved by **{interaction.user.display_name}**.\n\n"
                f"📄 **Resolution:**\n{resolution}\n\n"
                "Thank you for your report. If you have concerns, you may submit another or reply to staff."
            )
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Reporter has DMs disabled. Could not notify them.", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Report `{report_id}` resolved and reporter notified.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Could not find the reporter to notify them.", ephemeral=True)

    # Log to staff channel
    mod_channel = discord.utils.get(interaction.guild.text_channels, name="reports")
    if mod_channel:
        await mod_channel.send(
            f"✅ `{interaction.user}` resolved report `{report_id}`.\n"
            f"📋 Resolution: {resolution}"
        )


MAX_LEN = 2000

def split_message(text):
    return [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)]

@client.tree.command(name="postfaq", description="Post the Geo Interactive FAQ in the FAQ channel.")
async def postfaq(interaction: discord.Interaction):
    if interaction.user.id != client.owner_id:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    channel = client.get_channel(FAQ_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message("❌ FAQ channel not found. Please check the channel ID.", ephemeral=True)
        return

    try:
        parts = split_message(FAQ_TEXT)
        for part in parts:
            await channel.send(part)
        await interaction.response.send_message(f"✅ FAQ posted successfully in {channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to post FAQ: {e}", ephemeral=True)


@client.tree.command(name="warn", description="Warn a user with a reason.")
@app_commands.describe(user="The user to warn", reason="Reason for the warning")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not has_support_role(interaction.user):
        await interaction.response.send_message("❌ You need the Support role to warn users.", ephemeral=True)
        return

    if user.bot:
        await interaction.response.send_message("🤖 You cannot warn bots.", ephemeral=True)
        return

    warning = {
        "reason": reason,
        "date": datetime.now(timezone.utc).isoformat(),
        "moderator_id": interaction.user.id
    }

    user_id_str = str(user.id)
    warnings = user_warnings.get(user_id_str, [])
    warnings.append(warning)
    user_warnings[user_id_str] = warnings
    save_warnings()

    try:
        await user.send(f"⚠️ You have been warned in **{interaction.guild.name}** for: **{reason}**")
    except discord.Forbidden:
        pass

    await interaction.response.send_message(f"✅ {user.mention} has been warned for: **{reason}**", ephemeral=False)

# ========== VIEW WARNINGS ==========
@client.tree.command(name="warnings", description="Check warnings of a user.")
@app_commands.describe(user="The user to check warnings for")
async def warnings(interaction: discord.Interaction, user: discord.Member):
    if not has_support_role(interaction.user):
        await interaction.response.send_message("❌ You need the Support role to view warnings.", ephemeral=True)
        return

    user_id_str = str(user.id)
    warnings = user_warnings.get(user_id_str, [])
    if not warnings:
        await interaction.response.send_message(f"ℹ️ {user.mention} has no warnings.", ephemeral=True)
        return

    embed = discord.Embed(title=f"⚠️ Warnings for {user.display_name}", color=discord.Color.orange())
    for i, w in enumerate(warnings, 1):
        mod = interaction.guild.get_member(int(w["moderator_id"]))
        mod_name = mod.display_name if mod else "Unknown"
        embed.add_field(
            name=f"Warning {i}",
            value=f"**Reason:** {w['reason']}\n**Date:** {w['date']}\n**Moderator:** {mod_name}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== CLEAR WARNINGS ==========
@client.tree.command(name="clear_warnings", description="Clear all warnings of a user.")
@app_commands.describe(user="The user to clear warnings for")
async def clear_warnings(interaction: discord.Interaction, user: discord.Member):
    if not has_management_role(interaction.user):
        await interaction.response.send_message("❌ Only Management+ can clear warnings.", ephemeral=True)
        return

    user_id_str = str(user.id)
    if user_id_str not in user_warnings or not user_warnings[user_id_str]:
        await interaction.response.send_message(f"ℹ️ {user.mention} has no warnings to clear.", ephemeral=True)
        return

    user_warnings[user_id_str] = []
    save_warnings()

    await interaction.response.send_message(f"✅ Cleared all warnings for {user.mention}.", ephemeral=False)

    try:
        await user.send(f"✅ Your warnings have been cleared in **{interaction.guild.name}**.")
    except discord.Forbidden:
        pass

# ========== REMOVE ONE WARNING ==========
@client.tree.command(name="remove_warning", description="Remove a specific warning from a user.")
@app_commands.describe(user="The user whose warning to remove", number="The warning number to remove (1-based)")
async def remove_warning(interaction: discord.Interaction, user: discord.Member, number: int):
    if not has_management_role(interaction.user):
        await interaction.response.send_message("❌ Only Management+ can remove warnings.", ephemeral=True)
        return

    user_id_str = str(user.id)
    warnings = user_warnings.get(user_id_str, [])
    if not warnings:
        await interaction.response.send_message(f"ℹ️ {user.mention} has no warnings.", ephemeral=True)
        return

    if number < 1 or number > len(warnings):
        await interaction.response.send_message(f"❌ Invalid warning number. This user has {len(warnings)} warning(s).", ephemeral=True)
        return

    removed = warnings.pop(number - 1)
    user_warnings[user_id_str] = warnings
    save_warnings()

    await interaction.response.send_message(
        f"🧹 Removed warning #{number} from {user.mention}.\n**Reason:** {removed['reason']}",
        ephemeral=False
    )

    try:
        await user.send(f"🧹 One of your warnings in **{interaction.guild.name}** has been removed:\n**Reason:** {removed['reason']}")
    except discord.Forbidden:
        pass

@client.tree.command(name="bug_report", description="Submit a detailed bug report.")
@app_commands.describe(details="Follow the format in the pins to submit your bug report.")
async def bug_report(interaction: discord.Interaction, details: str):
    if not is_valid_bug_report(details):
        await interaction.response.send_message(
            "❌ Hey! Please use the **correct bug report format** listed in the channel pins.\n"
            "If you weren’t reporting a bug, please use the correct channel for chatting.",
            ephemeral=True
        )
        return

    bug_id = generate_bug_id()

    active_bugs[bug_id] = {
        "reporter_id": interaction.user.id,
        "details": details,
        "claimed_by": None,
        "resolved": False
    }

    await interaction.response.send_message(
        f"✅ Thanks for your bug report! It has been filed under ID `{bug_id}`. You’ll be notified with updates soon.",
        ephemeral=True
    )

    # DM the reporter a copy
    try:
        await interaction.user.send(f"📄 Your bug report (`{bug_id}`):\n\n{details}")
    except discord.Forbidden:
        pass  # Ignore if user has DMs disabled

    # Post to the bug report log channel
    bug_channel = discord.utils.get(interaction.guild.text_channels, name=BUG_REPORT_CHANNEL_NAME)
    if bug_channel:
        embed = discord.Embed(
            title=f"🐞 Bug Report `{bug_id}`",
            description=details,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Submitted by {interaction.user} ({interaction.user.id})")
        await bug_channel.send(embed=embed)



@client.tree.command(name="claim_bug", description="Claim a bug report to investigate it.")
@app_commands.describe(bug_id="The ID of the bug you want to claim")
async def claim_bug(interaction: discord.Interaction, bug_id: str):
    if not any(role.name == SUPPORT_ROLE_NAME for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ You must be part of the **Support** team to claim bug reports.", ephemeral=True
        )
        return

    bug = active_bugs.get(bug_id)
    if not bug:
        await interaction.response.send_message("❌ That bug ID doesn't exist.", ephemeral=True)
        return

    if bug.get("claimed_by"):
        await interaction.response.send_message("⚠️ This bug has already been claimed.", ephemeral=True)
        return

    bug["claimed_by"] = interaction.user.id

    # Notify reporter
    reporter = interaction.guild.get_member(bug["reporter_id"])
    if reporter:
        try:
            await reporter.send(
                f"🔔 Your bug report `{bug_id}` has been **claimed** by **{interaction.user.name}** and is being looked at."
            )
        except:
            pass

    await interaction.response.send_message(f"✅ You have claimed bug `{bug_id}`.", ephemeral=True)

    bug_channel = discord.utils.get(interaction.guild.text_channels, name=BUG_REPORT_CHANNEL_NAME)
    if bug_channel:
        await bug_channel.send(f"🔧 `{bug_id}` was claimed by **{interaction.user.mention}**.")

@client.tree.command(name="resolve_bug", description="Mark a bug report as resolved.")
@app_commands.describe(bug_id="The ID of the bug you want to mark as resolved")
async def resolve_bug(interaction: discord.Interaction, bug_id: str):
    if not any(role.name == ESCALATION_ROLE_NAME for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ Only **Management+** can resolve bugs.", ephemeral=True
        )
        return

    bug = active_bugs.get(bug_id)
    if not bug:
        await interaction.response.send_message("❌ That bug ID doesn't exist.", ephemeral=True)
        return

    if bug.get("resolved"):
        await interaction.response.send_message("⚠️ This bug has already been resolved.", ephemeral=True)
        return

    bug["resolved"] = True

    # Notify reporter
    reporter = interaction.guild.get_member(bug["reporter_id"])
    if reporter:
        try:
            await reporter.send(f"✅ Your bug report `{bug_id}` has been **resolved** by **{interaction.user.name}**.")
        except:
            pass

    await interaction.response.send_message(f"✅ Bug `{bug_id}` has been marked as resolved.", ephemeral=True)

    bug_channel = discord.utils.get(interaction.guild.text_channels, name=BUG_REPORT_CHANNEL_NAME)
    if bug_channel:
        await bug_channel.send(f"✅ `{bug_id}` was resolved by **{interaction.user.mention}**.")


@client.tree.command(
    name="safeguarding_notice",
    description="Send a safeguarding notice to a specified user."
)
@app_commands.describe(user="The user to send the safeguarding notice to")
async def safeguarding_notice(interaction: discord.Interaction, user: discord.Member):
    # Check if command user has the safeguarding role
    if not has_safeguarding_role(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    # Compose the embed message
    embed = discord.Embed(
        title="🔒 Safeguarding Notice",
        color=discord.Color.orange()
    )
    embed.add_field(
        name="Age Verification Review",
        value=(
            "Your account is currently under age verification review as part of our safeguarding procedures.\n\n"
            "**Who this applies to:**\n"
            "- Our services are only for users aged **13 and above**.\n"
            "- If you are under 13, please be honest and let us know — no documents are required, and your data won't be stored permanently.\n"
            "- If you are 13 or older, we may request a quick check to confirm your age."
        ),
        inline=False
    )
    embed.add_field(
        name="Important",
        value=(
            "Avoiding or ignoring this process may result in your account being suspended or banned.\n\n"
            "We appreciate your cooperation in keeping our community safe."
        ),
        inline=False
    )
    embed.set_footer(text="We will send a follow-up soon with more details on next steps.")

    # Attempt to send DM to the user
    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Could not send DM to {user.mention}. They might have DMs disabled or blocked the bot.",
            ephemeral=True
        )
        return

    # Confirm to the command invoker
    await interaction.response.send_message(
        f"✅ Safeguarding notice successfully sent to {user.mention}.",
        ephemeral=True
    )


@client.tree.command(name="profile", description="Get user profile by username")
@app_commands.describe(username="The username to look up")
async def profile(interaction: discord.Interaction, username: str):
    user = users_collection.find_one({"username": username})

    if user:
        await interaction.response.send_message(
            f"🧾 Profile for **{user['username']}**\n📛 Tag: **{user['tag']}**"
        )
    else:
        await interaction.response.send_message(
            f"❌ User '{username}' not found.",
            ephemeral=True
        )

@client.tree.command(name="reopen_ticket", description="Reopen a previously closed ticket.")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
@app_commands.describe(user="The user whose ticket should be reopened")
async def reopen_ticket(interaction: discord.Interaction, user: discord.Member):
    category = discord.utils.get(interaction.guild.categories, name=TICKET_CATEGORY_NAME)
    if category is None:
        category = await interaction.guild.create_category(TICKET_CATEGORY_NAME)

    # Increment ticket number again
    ticket_data["last_ticket_number"] += 1
    ticket_number = ticket_data["last_ticket_number"]
    save_ticket_data()

    channel_name = f"ticket-{ticket_number}"
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    ticket_channel = await interaction.guild.create_text_channel(
        name=channel_name, overwrites=overwrites, category=category
    )

    await ticket_channel.send(
        f"{user.mention} Your ticket has been reopened. A staff member will be with you shortly."
    )
    await interaction.response.send_message(f"Reopened ticket {ticket_channel.mention} for {user.mention}", ephemeral=True)

@client.tree.command(name="transcript", description="Download ticket transcript (basic)")
@app_commands.check(guild_check)
@app_commands.checks.has_role(SUPPORT_ROLE_NAME)
async def transcript(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used inside a ticket.", ephemeral=True)
        return

    messages = []
    async for message in interaction.channel.history(limit=100):
        messages.append(f"[{message.created_at}] {message.author.display_name}: {message.content}")

    transcript_text = "\n".join(reversed(messages))  # Oldest first
    file = discord.File(fp=io.StringIO(transcript_text), filename="transcript.txt")
    await interaction.response.send_message("Here is the transcript:", file=file, ephemeral=True)


#-----------------------------no commmands past here-----------------------------------------

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print("Bot is ready!")
    client.loop.create_task(send_heartbeat())  # ✅ Moved heartbeat here

@client.event
async def on_command_completion(interaction: discord.Interaction):
    try:
        log_channel = client.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            print("Log channel not found.")
            return

        options_desc = "No options"
        if interaction.data and "options" in interaction.data:
            opts = interaction.data["options"]
            options_desc = "\n".join(f"**{opt['name']}**: {opt.get('value')}" for opt in opts)

        embed = discord.Embed(
            title="Command Used",
            color=discord.Color.blurple(),
            timestamp=interaction.created_at
        )
        embed.add_field(name="User", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        embed.add_field(name="Command", value=interaction.command.name, inline=False)
        embed.add_field(name="Channel", value=f"{interaction.channel} ({interaction.channel.id})", inline=False)
        embed.add_field(name="Guild", value=f"{interaction.guild} ({interaction.guild.id})", inline=False)
        embed.add_field(name="Options", value=options_desc, inline=False)

        await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error logging command: {e}")

client.run(TOKEN)