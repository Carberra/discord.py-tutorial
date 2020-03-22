"""
Tutorial Bot (dispybot.py)
 Copyright (C) Parafoxia 2019.
 Copyright (C) Carberra 2019.

This is the bot that I created on the Carberra programming channel. The tutorial series it featured in can be found here:
 https://www.youtube.com/playlist?list=PLYeOw6sTSy6bHr2w8nOV0CpKskuOuU1XE

This bot can be freely copied and modified without permission, but not sold as is.

This bot is not the most well constructed thing in existance, but serves as an entry-point into Discord bot programming. It
was designed to be simple, and should be used as a starting point more than a finished product.

Things to try:
 - Move the database commands to another .py file, and get the bot to import it here.
    Hint: this can be done simply by creating a file called "db.py" and using "import db"!
 - Try creating a exponential levelling system. The current one is linear, but it would be good
    to make it harder to level up the higher someone's level is, right?
 - The reaction video was very popular, so here's something to give you more practise with the `on_reaction_add(...)` and
    `on_reaction_remove(...)` as opposed to their `on_raw...` counterparts:
    - Add a voting system to the bot! Create a system which takes the question and options (this doesn't have to be done with
       one command), and sends a message (with reactions) that your members can use to vote with. After the vote is complete, make
       the bot output the winner! This task is somewhat advanced, but should give you a really good overall sense of how the
       API operates.

If you want to check the Carberra channel out, use this link: https://www.youtube.com/channel/UC13cYu7lec-oOcqQf5L-brg. There will
 be more tutorial series' coming soon, so stay tuned!
"""

from asyncio import sleep
from datetime import datetime, timedelta
from random import choice, randrange
from sqlite3 import connect
from sys import exit
from traceback import format_exc
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import utils, Activity, ActivityType, Client, Embed, Colour
from discord import Member as DiscordMember
from discord.errors import Forbidden
from discord.ext.commands import has_permissions, Bot, Greedy
from discord.ext.commands import BadArgument, CommandNotFound, MissingPermissions, MissingRequiredArgument

TOKEN = "your-token-here"
PREFIX = "!"
CURSES = ("cunt", "faggot", "nigger")
VERSION = "1.1.8"
CHANGES = """
- Stop Tutorial Bot interfering with S4's gateway systems.
"""

Me = Bot(command_prefix=PREFIX, max_messages=100)
Guild = object()
Database = connect("dispybot/database.db", check_same_thread=False)
# ^ Updated in v1.1.1 to include `check_same_thread`.
#    Use this if your program complains about making changes on different threads.
#    The directory was also changed so the bot could access the database on the server.
Cursor = Database.cursor()
Scheduler = AsyncIOScheduler()

started = False

#	classes

class database:
	def field(command, *values):
		"""Return a value from a specific field."""
		Cursor.execute(command, tuple(values))
		fetch = Cursor.fetchone()
		if fetch is not None:
			return fetch[0]
		return

	def one_record(command, *values):
		"""Return a single record (row) as a tuple."""
		Cursor.execute(command, tuple(values))
		return Cursor.fetchone()

	def records(command, *values):
		"""Return many records (rows) as a list of tuples."""
		Cursor.execute(command, tuple(values))
		return Cursor.fetchall()

	def column(command, *values):
		"""Return a column as a list."""
		Cursor.execute(command, tuple(values))
		return [item[0] for item in Cursor.fetchall()]

	def execute(command, *values):
		"""Execute an SQL command."""
		Cursor.execute(command, tuple(values))
		return

	def update():
		"""Updates the database, so new members are added, and old ones removed.
		This is only run at start-up."""
		for Member in [Member for Member in Guild.members if not Member.bot]:
			database.execute("INSERT OR IGNORE INTO users (UserID) VALUES (?)", Member.id)
		for userid in database.column("SELECT UserID from users"):
			if Guild.get_member(userid) is None:
				database.execute("DELETE FROM users WHERE UserID = ?", userid)
		Database.commit()
		return

	def commit():
		"""Commits (saves) the database."""
		Database.commit()
		return

	def disconnect():
		"""Closes the database connection."""
		Database.close()
		return

class get:
	def channel(channelname):
		"""Returns a channel object from the channel name."""
		return utils.get(Guild.text_channels, name=channelname)

	def role(rolename):
		"""Returns a role object from the role name."""
		return utils.get(Guild.roles, name=rolename)

	def superior(Member1, Member2):
		"""Returns the Member with the highest role."""
		if Member1.top_role.position > Member2.top_role.position:
			return Member1
		elif Member1.top_role.position < Member2.top_role.position:
			return Member2
		return

class colours:
	roles = {
		"❤️" : "Red",
		"💛" : "Yellow",
		"💚" : "Green",
		"💙" : "Blue",
		"💜" : "Purple",
		"🖤" : "Black",
	}

	async def assign(Payload):
		"""Assigns a colour role to the member.
		`Payload` is used as this is made using a raw HTTP request."""
		Member = Guild.get_member(Payload.user_id)
		if any([get.role(rolename) in Member.roles for rolename in colours.roles.values()]):
			try:
				await Member.send("⚠ You already have a colour role. Unreact the one you have first.")
			except Forbidden:
				await get.channel("general").send(f"⚠ {Member.mention}, you already have a colour role. Unreact the one you have first.")
			Message = await Me.get_channel(Payload.channel_id).fetch_message(Payload.message_id)
			await Message.remove_reaction(Payload.emoji.name, Member)
			return

		await Member.edit(roles=[*Member.roles, get.role(colours.roles[Payload.emoji.name])])
		return

	async def remove(Payload):
		"""Removes a colour role to the member.
		`Payload` is used as this is made using a raw HTTP request."""
		Member = Guild.get_member(Payload.user_id)
		try:
			await Member.edit(roles=[Role for Role in Member.roles if Role is not get.role(colours.roles[Payload.emoji.name])])
		except AttributeError:
			pass
		return

class levelling:
	async def add_xp(Message):
		"""Adds XP the member."""
		XPLockedUntil = datetime.strptime(
			database.field("SELECT XPLockedUntil FROM users WHERE UserID = ?", Message.author.id),
			"%Y-%m-%d %H:%M:%S",
		)

		if XPLockedUntil < datetime.utcnow():
			xp_add = randrange(5, 21)
			database.execute("UPDATE users SET XP = XP + ? WHERE UserID = ?", xp_add, Message.author.id)
			database.execute("UPDATE users SET XPLockedUntil = datetime('now', '+60 seconds') WHERE UserID = ?",
							  Message.author.id)
			await levelling.check_level_up(Message)
		return

	async def check_level_up(Message):
		"""Checks if the member has levelled up."""
		xp, cur_level = database.one_record("SELECT XP, Level FROM users WHERE UserID = ?", Message.author.id)
		new_level = xp // 100
		if new_level > cur_level:
			database.execute("UPDATE users SET Level = ? WHERE UserID = ?", new_level, Message.author.id)
			await Message.channel.send(f"Congratulations {Message.author.mention}, you're now level **{new_level}**!")
		return

class automod:
	async def check_curses(Message):
		"""Checks passes message for curses (swear words)."""
		if any([curse in Message.content.lower() for curse in CURSES]):
			await Message.delete()
			await Message.channel.send(f"{Message.author.mention}, don't use language like that in here!")
			await automod.add_strike(Message)
			return True
		return False

	async def add_strike(Message):
		"""Adds a strike to a member."""
		database.execute("UPDATE users SET Strikes = Strikes + 1 WHERE UserID = ?", Message.author.id)
		strikes = database.field("SELECT Strikes FROM users WHERE UserID = ?", Message.author.id)
		if strikes == 5:
			await automod.kick_member(Message)
		elif strikes >= 3:
			await automod.mute_member(Message, strikes)
		return

	async def mute_member(Message, strikes):
		"""Mutes a member."""
		if strikes == 3:
			database.execute("UPDATE users SET MutedUntil = datetime('now', '+3600 seconds') WHERE UserID = ?", Message.author.id)
		elif strikes == 4:
			database.execute("UPDATE users SET MutedUntil = datetime('now', '+86400 seconds') WHERE UserID = ?", Message.author.id)
		database.execute("UPDATE users SET PreviousRoles = ? WHERE UserID = ?", serialise_roles(Message.author), Message.author.id)
		await Message.author.edit(roles=[get.role("Muted")])
		await Message.channel.send(f"That's strike number **{strikes}** {Message.author.mention}, I'm muting you for {1 if strikes == 3 else 24} hours.")
		return

	async def kick_member(Message):
		"""Kicks a member."""
		try:
			await Message.author.send("You've been kicked for cursing too much.")
		except Forbidden:
			pass
		await Message.author.kick(reason="Cursing too much.")
		return

	async def check_muted():
		"""Checks if muted members should be unmuted. This is a scheduled task, and does not need
		to be called manually."""
		for Member in Guild.members:
			if get.role("Muted") in Member.roles:
				MutedUntil = datetime.strptime(
					database.field("SELECT MutedUntil FROM users WHERE UserID = ?", Member.id),
					"%Y-%m-%d %H:%M:%S",
				)
				if MutedUntil < datetime.utcnow():
					await Member.edit(roles=deserialise_roles(Member))
					database.execute("UPDATE users SET MutedUntil = NULL WHERE UserID = ?", Member.id)
					await get.channel("general").send(f"You're now unmuted again {Member.mention}. Try and keep it clean now, yeah?")
		return

def serialise_roles(Member):
	"""Turns a list of roles in a comma-seperated string."""
	return ",".join([Role.name for Role in Member.roles])

def deserialise_roles(Member):
	"""Turns a comma-seperated string into a list of roles."""
	return [get.role(role) for role in database.field("SELECT PreviousRoles FROM users WHERE UserID = ?", Member.id).split(",")]

async def send_rules_reminder():
	"""A scheduled function that simply sends a reminder."""
	await get.channel("general").send(f"Remember to adhere to the server rules! Swing by the {get.channel('rules')} room to refresh yourself if needed.")
	return

async def announce_update():
	"""Announces updates. This is run at start-up."""
	if VERSION != database.field("SELECT Value FROM system WHERE Key = 'version'"):
		await get.channel("announcements").send(f"I've been updated to version **{VERSION}**! Here are the latest changes:```{CHANGES}```")
		database.execute("UPDATE system SET Value = ? WHERE Key = 'version'", VERSION)
	return

async def set_activity(activity):
	"""Sets the bot's activity. This is not normally called, unless you want to set
	the next activity manually."""
	kind, name = activity.split(" ", maxsplit=1)
	kinds = {
		"playing" : ActivityType.playing,
		"watching" : ActivityType.watching,
		"listening-to" : ActivityType.listening,
	}
	await Me.change_presence(activity=Activity(name=name, type=kinds[kind]))
	return

async def choose_next_activity():
	"""Chooses the next activity to be set for the bot. Do not use if you wish
	to set activities manually."""
	possible_activities = [
		"playing with the API",
		"watching Carberra's videos",
		"watching Superboo's videos",
		"listening-to the screams of the eternal",
	]
	await set_activity(choice(possible_activities))
	return

def start_scheduled():
	"""Starts scheduled activities in one place."""
	Scheduler.add_job(database.commit, CronTrigger())
	Scheduler.add_job(send_rules_reminder, CronTrigger(day_of_week=0, hour=12, minute=0, second=0))
	Scheduler.add_job(automod.check_muted, CronTrigger(second=",".join([str(sec) for sec in range(0, 60, 2)])))
	Scheduler.add_job(choose_next_activity, CronTrigger(minute="0,30"))
	Scheduler.start()
	return

#	commands

# To make a custom help command, you first have to get rid of the default one.
Me.remove_command("help")
@Me.command(name="help")
async def help(Ctx):
    HelpEmbed = Embed(title=f"Help with Tutorial Bot", description="**Help command developed by Hydraa#3074.**\n\n**Info** \n``!userinfo`` Displays user info on specified target.\n``!videos`` Toggles video alerts whenever Carberra posts a new video.\n``!announcements`` Toggles server alerts.\n``!humans`` Displays the number of non-bot members.\n``!serverinfo`` Displays server information.\n\n**Moderation**\n``!kick`` Kicks all given members, not just one!\n``!ban`` Bans all given members, not just one!\n``!clear [amount=100]`` Clears up to 100 messages less then 14 days old.\n\n**Misc**\n``!hi`` Gives you a friendly greeting!\n``!slap <member>`` Slap someone silly!\n``!dice`` Rolls a d6 die.", timestamp=Ctx.message.created_at, colour=Colour.red())
    HelpEmbed.set_thumbnail(url=Guild.icon_url)
    await Ctx.send(embed=HelpEmbed)

@Me.command(name="hi")
async def say_hi(Ctx):
	"""Says hi!"""
	await Ctx.send(f"Hey {Ctx.author.mention}!")
	return

@Me.command(name="dice")
async def roll_dice(Ctx):
	"""Rolls a die."""
	await Ctx.send(f"{Ctx.author.display_name}, you rolled a **{randrange(1, 7)}**!")
	return

@Me.command(name="slap")
async def slap_member(Ctx, Target:DiscordMember):
	"""Slaps a member."""
	await Ctx.send(f"**{Ctx.author.display_name}** just slapped {Target.mention} silly!")
	return

@Me.command(name="members")
async def member_count(Ctx):
	"""Displays the number of members in the server."""
	await Ctx.send(f"There are **{len(Guild.members)}** members in {Ctx.guild.name}.")
	return

@Me.command(name="humans")
async def human_count(Ctx):
	"""Dissplays the number of non-bot members in the server."""
	await Ctx.send(f"There are **{len([Member for Member in Guild.members if not Member.bot])}** humans in {Ctx.guild.name}.")
	return

@Me.command(name="shutdown", hidden=True)
@has_permissions(administrator=True)
async def shutdown(Ctx):
	"""Shuts the bot down."""
	await Ctx.send("I'm shutting down!")
	await get.channel("tb-stdout").send("I'm shutting down!")
	# ^ Line added in v1.1.1.
	await Me.logout()
	sys.exit(0)
	return

@Me.command(name="clear")
@has_permissions(manage_messages=True)
async def clear_messages(Ctx, number:int=100):
	"""Deletes up to the most recent 100 messages. This only works for messages that are
	less than 14 days old. You can create a function without these restrictions, by making
	a function that deletes the messages one by one. That was not covered in the tutorial,
	as it is considered API abuse, however, for custom single-server bots, it won't be an
	issue."""
	await Ctx.message.delete()
	await Ctx.channel.delete_messages(await Ctx.history(limit=number).flatten())
	DoneMessage = await Ctx.send("Done.")
	await sleep(5)
	await DoneMessage.delete()
	return

@Me.command(name="kick")
@has_permissions(kick_members=True)
async def kick_members(Ctx, targets:Greedy[DiscordMember], *, reason:Optional[str]=""):
	"""Kicks all given members, not just one at a time!"""
	for Target in targets:
		if Ctx.author is get.superior(Ctx.author, Target):
			await Target.kick(reason=reason)
	await Ctx.send("Done.")
	return

@Me.command(name="ban")
@has_permissions(ban_members=True)
async def ban_members(Ctx, targets:Greedy[DiscordMember], *, reason:Optional[str]=""):
	"""Bans all given members, not just one at a time!"""
	for Target in targets:
		if Ctx.author is get.superior(Ctx.author, Target):
			await Target.ban(reason=reason, delete_message_days=7)
	await Ctx.send("Done.")
	return

@Me.command(name="userinfo")
async def user_info(Ctx, Target:Optional[DiscordMember]):
	"""Displays user info. If no member is given, it defaults to the command invoker."""
	if Target is None:
		Target = Ctx.author

	header = f"User information - {Target.display_name}\n\n"
	rows = {
		"Account name"     : Target.name,
		"Disciminiator"    : Target.discriminator,
		"ID"               : Target.id,
		"Is bot"           : "Yes" if Target.bot else "No",
		"Top role"         : Target.top_role,
		"Nº of roles"      : len(Target.roles),
		"Current status"   : str(Target.status).title(),
		"Current activity" : f"{str(Target.activity.type).title().split('.')[1]} {Target.activity.name}" if Target.activity is not None else "None",
		"Created at"       : Target.created_at.strftime("%d/%m/%Y %H:%M:%S"),
		"Joined at"        : Target.joined_at.strftime("%d/%m/%Y %H:%M:%S"),
	}
	table = header + "\n".join([f"{key}{' '*(max([len(key) for key in rows.keys()])+2-len(key))}{value}" for key, value in rows.items()])
	await Ctx.send(f"```{table}```{Target.avatar_url}")
	return

@Me.command(name="serverinfo")
async def guild_info(Ctx):
	"""Displays server information."""
	header = f"Server information - {Ctx.guild.name}\n\n"
	rows = {
		"Name"                  : Ctx.guild.name,
		"ID"                    : Ctx.guild.id,
		"Region"                : str(Ctx.guild.region).title(),
		"Owner"                 : Ctx.guild.owner.display_name,
		"Shard ID"              : Ctx.guild.shard_id,
		"Created on"            : Ctx.guild.created_at.strftime("%d/%m/%y %H:%M:%S"),
		"Most recent member"    : [Member for Member in Guild.members if Member.joined_at is max([Member.joined_at for Member in Guild.members])][0].display_name,
		"...joined"             : max([Member.joined_at for Member in Guild.members]).strftime("%d/%m/%y %H:%M:%S"),
		"Nº of members"         : len(Guild.members),
		"...of which human"     : len([Member for Member in Guild.members if not Member.bot]),
		"...of which bots"      : len([Member for Member in Guild.members if Member.bot]),
		"Nº of banned members"  : len(await Ctx.guild.bans()),
		"Nº of categories"      : len(Ctx.guild.categories),
		"Nº of text channels"   : len(Ctx.guild.text_channels),
		"Nº of voice channels"  : len(Ctx.guild.voice_channels),
		"Nº of roles"           : len(Ctx.guild.roles),
		"Nº of invites"         : len(await Ctx.guild.invites()),
	}
	table = header + "\n".join([f"{key}{' '*(max([len(key) for key in rows.keys()])+2-len(key))}{value}" for key, value in rows.items()])
	await Ctx.send(f"```{table}```{Ctx.guild.icon_url}")
	return

@Me.command(name="videos")
async def optin_to_videos(Ctx):
	if get.role("Videos") not in Ctx.author.roles:
		await Ctx.author.edit(roles=[*Ctx.author.roles, get.role("Videos")])
		await Ctx.send("You'll now be alerted of new videos. To stop these alerts, type ` !videos ` again.")
	else:
		await Ctx.author.edit(roles=[Role for Role in Ctx.author.roles if Role is not get.role("Videos")])
		await Ctx.send("You'll no longer be alerted of new videos. To receive these alerts again, type ` !videos `.")
	return

@Me.command(name="announcements")
async def optin_to_announcements(Ctx):
	if get.role("Announcements") not in Ctx.author.roles:
		await Ctx.author.edit(roles=[*Ctx.author.roles, get.role("Announcements")])
		await Ctx.send("You'll now be alerted of new announcements and updates. To stop these alerts, type ` !announcements ` again.")
	else:
		await Ctx.author.edit(roles=[Role for Role in Ctx.author.roles if Role is not get.role("Announcements")])
		await Ctx.send("You'll no longer be alerted of new announcements and updates. To receive these alerts again, type ` !announcements `.")
	return

@Me.command(name="blanketopt", hidden=True)
@has_permissions(administrator=True)
async def blanketopt(Ctx):
	for Member in Ctx.guild.members:
		if not Member.bot and Ctx.guild.me.top_role.position > Member.top_role.position:
			await Member.edit(roles=[*Member.roles, get.role("Videos"), get.role("Announcements")])
	return

#	events

@Me.event
async def on_ready():
	"""Called automatically when the bot starts."""
	global started, Guild
	if not started:
		Guild = Me.get_guild(626608699942764544) # Use your own server's ID here!
		database.update()
		await announce_update()
		start_scheduled()
		await get.channel("tb-stdout").send("I'm online!")
		started = True
	else:
		await get.channel("tb-stdout").send("I've reconnected.")
	return

@Me.event
async def on_member_join(Member):
	"""Called automatically when a member joins the server."""
	if not Member.bot:
		database.execute("INSERT INTO users (UserID) VALUES (?)", Member.id)
		Database.commit()
		# await Member.edit(roles=[*Member.roles, get.role("Videos"), get.role("Announcements")])
		# How did I not know about this before?! Updated in v1.1.8
		await Member.add_roles(get.role("Announcements"), get.role("Videos"))
		await get.channel("welcome").send(f"Welcome to **{Member.guild.name}** {Member.mention}! Head over to {get.channel('general').mention} and say hi!")
	else:
		await get.channel("welcome").send(f"A new bot, **{Member.name}**, just joined.")
	return

@Me.event
async def on_member_remove(Member):
	"""Called automatically when a member leaves the server."""
	if not Member.bot:
		database.execute("DELETE FROM users WHERE UserID = ?", Member.id)
		Database.commit()
		await get.channel("goodbye").send(f"**{Member.display_name}** is no longer in the server. Goodbye!")
	return

@Me.event
async def on_error(event, *args, **kwargs):
	"""Called automatically whenever there's an error (usually a programming error)."""
	await get.channel("tb-stdout").send(f"```{format_exc()[-1994:]}```")
	raise
	return

@Me.event
async def on_command_error(Ctx, Exc):
	"""Called automatically whenever there's an error following a command invokation."""
	if isinstance(Exc, CommandNotFound):
		return

	if isinstance(Exc, MissingRequiredArgument):
		await Ctx.send("⚠ Missing required argument.")
		return

	if isinstance(Exc, BadArgument):
		await Ctx.send("⚠ Bad argument.")
		return

	if isinstance(Exc, MissingPermissions):
		await Ctx.send("⚠ You are not allowed scrub!")
		return

	await Ctx.send("⚠ An unknown error occured.")
	raise Exc
	return

@Me.event
async def on_raw_reaction_add(Payload):
	"""Called automatically whenever a reaction is added to a message.
	This is an HTTP-based version of `on_reaction_add(...)`. In 99% of cases, you would
	use that instead. Note that that function is completely different, but was covered in
	Part 5 of the video series."""
	if Payload.message_id == 653941017870860308 and Payload.emoji.name in "❤️💛💚💙💜🖤":
		await colours.assign(Payload)
	return

@Me.event
async def on_raw_reaction_remove(Payload):
	"""Called automatically whenever a reaction is removed from a message.
	This is an HTTP-based version of `on_reaction_remove(...)`. In 99% of cases, you would
	use that instead. Note that that function is completely different, but was covered in
	Part 5 of the video series."""
	if Payload.message_id == 653941017870860308 and Payload.emoji.name in "❤️💛💚💙💜🖤":
		await colours.remove(Payload)
	return

@Me.event
async def on_message(Message):
	"""Called automatically whenever a message is send to the server."""
	if not Message.author.bot and not await automod.check_curses(Message):
		await levelling.add_xp(Message)
		await Me.process_commands(Message)
	return

Me.run(TOKEN)