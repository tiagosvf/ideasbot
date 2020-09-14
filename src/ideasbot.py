import yaml
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

URL = 'https://ideasai.net/'


class Feed:
    def __init__(self, header_text, color, newest_position):
        self.header_text = header_text
        self.recent_ideas = []
        self.channels = []
        self.color = color
        self.newest_position = newest_position  # Position of the newest idea

    @staticmethod
    def unsubscribe_from_feeds(feeds, channel):
        for feed in feeds:
            try:
                feeds[feed].channels.remove(channel)
            except ValueError:
                pass


feeds = {"new": Feed("New ideas just in", 0xe5e900, "top"),
         "top": Feed("Today's top ideas", 0xff4742, "bottom")}


with open("settings.yaml") as file:
    settings = yaml.load(file, Loader=yaml.FullLoader)
    token = settings["discord"]["token"]
    refresh_frequency = settings["bot"]["refresh_frequency"]
    info_url = settings["bot"]["info_url"]

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
async def new(ctx):
    if ctx.channel not in feeds["new"].channels:
        feeds["new"].channels.append(ctx.channel)
        await ctx.send("```This channel is now subscribed to new ideas.```")
    else:
        await ctx.send("```This channel is already subscribed to new ideas.```")


@bot.command()
async def top(ctx):
    if ctx.channel not in feeds["top"].channels:
        feeds["top"].channels.append(ctx.channel)
        await ctx.send("```This channel is now subscribed to today's top ideas.```")
    else:
        await ctx.send("```This channel is already subscribed to today's top ideas.```")


@bot.command()
async def off(ctx):
    Feed.unsubscribe_from_feeds(feeds, ctx.channel)
    await ctx.send("```This channel has been unsubscribed.```")


@bot.command(aliases=["commands", "help"])
async def cmd(ctx):
    embed = discord.Embed(color=0xc200a8)
    embed.set_author(name="I keep you updated on new business ideas"
                          " generated by IdeasAI", url=f"{info_url}")
    embed.add_field(name="Commands",
                    value="`!ideas help`, `!ideas cmd` or `!ideas commands` › Show this message"
                          "\n"
                          "\n`!ideas new` › Subscribe to new ideas"
                          "\n`!ideas top` › Subscribe to today's top ideas"
                          "\n"
                          "\n`!ideas off` › Unsubscribe"
                          "\n\u200b")
    embed.set_footer(text="👨‍💻 by @tiagosvf, ⚡ by ideasai.net")
    await ctx.send(embed=embed)


@tasks.loop(seconds=refresh_frequency)
async def get_ideas():
    page = requests.get(URL, timeout=10)
    soup = BeautifulSoup(page.content, 'html.parser')

    elems = soup.findAll("h2")

    for name, feed in feeds.items():
        try:
            elem = next(h for h in elems if feed.header_text in h.text)
        except StopIteration:
            continue

        if elem and feed.newest_position == "bottom":
            elem = elems[elems.index(elem)+1]

        while elem:
            elem = (elem.next_sibling
                    if feed.newest_position == "top" else
                    elem.previous_sibling)

            if elem.name == "table":
                idea = elem.find(class_="idea")
                text = idea.text.strip()

                if text in feed.recent_ideas:
                    break

                feed.recent_ideas.append(text)

                if len(text) > 256:
                    embed = discord.Embed(
                        description=f"**{text}**", color=feed.color)
                else:
                    embed = discord.Embed(color=feed.color)
                    embed.set_author(name=f"{text}", url=f"{URL}")

                for channel in feed.channels:
                    await channel.send(embed=embed)
            elif elem.name == "h2":
                break

        feed.recent_ideas = feed.recent_ideas[-10:]


bot.run(token)
