import operator
import sqlite3
import sys
import traceback
import functools

from discord.ext import commands


bot = commands.Bot(command_prefix='!', help_command=None)

db = sqlite3.connect('bot.db')

with db:
	db.cursor().execute('''
		CREATE TABLE IF NOT EXISTS tags (
			guild_id INTEGER NOT NULL,
			user_id INTEGER NOT NULL,
			name TEXT NOT NULL,
			content TEXT NOT NULL,
			PRIMARY KEY(guild_id, name)
		)
	''').close()

@bot.listen()
async def on_ready():
	print(f'Logged in as {bot.user}')

@bot.listen()
async def on_command_error(ctx: commands.Context, err):
	if isinstance(err, commands.MissingRequiredArgument):
		await ctx.send(str(err))
		return

	traceback.print_exception(type(err), err, err.__traceback__, file=sys.stderr)

@bot.command()
@commands.guild_only()
async def tags(ctx: commands.Context):
	names = None
	with db:
		cur = db.cursor()
		cur.execute(
			'SELECT name FROM tags WHERE guild_id = ?',
			(ctx.guild.id,)
		)
		names = cur.fetchall()
		cur.close()

	if not len(names):
		await ctx.send('_No tags found for this server_.')
		return

	await ctx.send(', '.join(map(lambda x: f'`{x[0]}`', names)))


@bot.group()
@commands.guild_only()
async def tag(ctx: commands.Context):
	if ctx.invoked_subcommand:
		return

	name = ctx.subcommand_passed
	content = None
	with db:
		cur = db.cursor()
		cur.execute(
			'SELECT content FROM tags WHERE guild_id = ? AND name = ?',
			(ctx.guild.id, name)
		)
		content = cur.fetchone()
		cur.close()

	if not content:
		await ctx.send(f'Tag `{name}` not found.')
		return

	await ctx.send(content[0])

@tag.command()
async def create(ctx: commands, name: str, *, content: str):
	subcommand_aliases = functools.reduce(operator.concat, map(lambda x: (*x.aliases, x.name), tag.commands))
	if name in subcommand_aliases:
		await ctx.send(f'{name} is a reserved name.')
		return

	try:
		with db:
			db.cursor().execute(
				'INSERT INTO tags VALUES (?, ?, ?, ?)',
				(ctx.guild.id, ctx.author.id, name, content)
			).close()
	except sqlite3.IntegrityError:
		await ctx.send(f'Tag `{name}` already exists.')
		return

	await ctx.send(f'Created tag `{name}`.')

@tag.command()
async def edit(ctx: commands, name: str, *, content: str):
	user_id = None
	with db:
		cur = db.cursor()
		cur.execute(
			'SELECT user_id FROM tags WHERE guild_id = ? AND name = ?',
			(ctx.guild.id, name)
		)
		user_id = cur.fetchone()
		cur.close()

	if not user_id:
		await ctx.send(f'Tag `{name}` doesn\'t exist.')
		return

	user_id = user_id[0]
	if user_id != ctx.author.id:
		await ctx.send(f'Tag `{name}` doesn\'t belong to you.')
		return

	with db:
		cur = db.cursor()
		cur.execute(
			'UPDATE tags SET content = ? WHERE guild_id = ? AND user_id = ? AND name = ?',
			(content, ctx.guild.id, ctx.author.id, name)
		)
		cur.close()

	await ctx.send(f'Tag `{name}` edited.')

@tag.command(aliases=['remove'])
async def delete(ctx: commands, name: str):
	user_id = None
	with db:
		cur = db.cursor()
		cur.execute(
			'SELECT user_id FROM tags WHERE guild_id = ? AND name = ?',
			(ctx.guild.id, name)
		)
		user_id = cur.fetchone()
		cur.close()

	if not user_id:
		await ctx.send(f'Tag `{name}` doesn\'t exist.')
		return

	user_id = user_id[0]
	if user_id != ctx.author.id:
		await ctx.send(f'Tag `{name}` doesn\'t belong to you.')
		return

	with db:
		cur = db.cursor()
		cur.execute(
			'DELETE FROM tags WHERE guild_id = ? AND user_id = ? AND name = ?',
			(ctx.guild.id, ctx.author.id, name)
		)
		cur.close()

	await ctx.send(f'Tag `{name}` deleted.')


if __name__ == '__main__':
	import os
	import sys

	token = os.getenv('BOT_TOKEN')
	if not token:
		sys.stderr.write('Missing BOT_TOKEN env var.\n')
		sys.exit(1)

	print('Starting...')
	bot.run(token)
