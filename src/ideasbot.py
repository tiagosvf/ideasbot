import yaml
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

URL = 'https://ideasai.net/'
recent_ideas = []
channel_list = []

with open("settings.yaml") as file:
    settings = yaml.load(file, Loader=yaml.FullLoader)
    token = settings["discord"]["token"]
    refresh_frequency = settings["bot"]["refresh_frequency"]

bot = commands.Bot(command_prefix='!ideas ')
bot.remove_command('help')


@bot.event
async def on_ready():
    get_ideas.start()


@bot.command()
async def on(ctx):
    if ctx.channel not in channel_list:
        channel_list.append(ctx.channel)
        await ctx.send("```Bot has been activated in this channel. "
                       "\nYou will now start to receive new ideas```")
    else:
        await ctx.send("```Bot is already active in this channel.```")


@bot.command()
async def off(ctx):
    if ctx.channel not in channel_list:
        channel_list.append(ctx.channel)
        await ctx.send("```Bot has been deactivated in this channel.```")

@tasks.loop(seconds=refresh_frequency)
async def get_ideas():
    global recent_ideas

    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    elem = soup.findAll("h2", limit=1)[0]

    while True:
        elem = elem.next_sibling

        if elem.name == "table":
            idea = elem.find(class_="idea")
            text = idea.text.strip()

            if text in recent_ideas:
                break

            recent_ideas.append(text)

            if len(text) > 256:
                embed = discord.Embed(
                    description=f"**{text}**", color=0xfaa61a)
            else:
                embed = discord.Embed(color=0xfaa61a)
                embed.set_author(name=f"{text}", url=f"{URL}")

            for channel in channel_list:
                await channel.send(embed=embed)
        elif elem.name == "h2":
            break

    recent_ideas = recent_ideas[-10:]

bot.run(token)
