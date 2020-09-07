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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!ideas help"))
    get_ideas.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("```Command not found. Try !ideas help```")

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


@bot.command(aliases=["commands", "help"])
async def cmd(ctx):
    embed = discord.Embed(title="I keep you updated on new ideas"
                                " generated by IdeasAI",
                          description="\u200b\u200b", color=0xc200a8)
    embed.add_field(name="Commands",
                    value="`!ideas help`, `!ideas cmd` or `!ideas commands` › Show this message"
                          "\n"
                          "\n`!ideas on` › Activate bot in this channel"
                          "\n`!ideas off` › Deactivate bot in this channel"
                          "\n\u200b")
    embed.set_footer(text="👨‍💻 by @tiagosvf, ⚡ by ideasai.net")
    await ctx.send(embed=embed)


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
