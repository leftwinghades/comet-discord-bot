import discord
from discord.ext import commands
from music import Music
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("COMET_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX")

bot = commands.Bot(command_prefix=COMMAND_PREFIX)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def suisei(ctx):
    await ctx.send("Suisei wa kyou mo kawaii!")

bot.add_cog(Music(bot))
bot.run(TOKEN)