import os
import yaml
import discord
import requests
import asyncio
import data
import json
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
import threading

URL = 'https://ideasai.net/'
MAX_THREADS = 3
initialized = False
current_threads = 0

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


def async_from_sync(function, *args, **kwargs):
    """
    Wrapper to allow calling async functions from sync
    and running them in the main event loop
    """

    res = function(*args, **kwargs)
    asyncio.run_coroutine_threadsafe(res, loop).result()


def file_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


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

    @staticmethod
    def read_subscriptions():
        try:
            json_s = data.read()
            data_s = json.loads(json_s)
            for f in data_s['feeds']:
                feed = feeds.get(f['name'])
                for channel in f['channels']:
                    id = int(channel['id'])
                    channel = bot.get_channel(id)
                    if channel:
                        feed.channels.append(channel)
        except KeyError:
            pass

    async def get_feed_channels(self):
        data_list = []
        for channel in self.channels:
            data_list.append({'id': f"{channel.id}"})
            await asyncio.sleep(0.01)
        return data_list

    @staticmethod
    async def save_subscriptions():
        data_s = {}
        data_s['feeds'] = []
        for name, feed in feeds.items():
            channels = await feed.get_feed_channels()
            data_s["feeds"].append({'name': name, 'channels': channels})
            await asyncio.sleep(0.01)
        data.save(data_s)


feeds = {"new": Feed("New ideas just in", 0xe5e900, "top"),
         "top": Feed("Today's top ideas", 0xff4742, "bottom")}


with open(file_path("settings.yaml")) as file:
    settings = yaml.load(file, Loader=yaml.FullLoader)
    token = settings["discord"]["token"]
    refresh_frequency = settings["bot"]["refresh_frequency"]
    info_url = settings["bot"]["info_url"]

bot = commands.Bot(command_prefix='!ideas ')
bot.remove_command('help')


@bot.event
async def on_connect():
    global initialized
    if not initialized:
        Feed.read_subscriptions()
        initialized = True

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!ideas help"))
    get_ideas_task.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("```Command not found. Try !ideas help```")


@bot.command()
async def new(ctx):
    if ctx.channel not in feeds["new"].channels:
        feeds["new"].channels.append(ctx.channel)
        await Feed.save_subscriptions()
        await ctx.send("```This channel is now subscribed to new ideas.```")
    else:
        await ctx.send("```This channel is already subscribed to new ideas.```")


@bot.command()
async def top(ctx):
    if ctx.channel not in feeds["top"].channels:
        feeds["top"].channels.append(ctx.channel)
        await Feed.save_subscriptions()
        await ctx.send("```This channel is now subscribed to today's top ideas.```")
    else:
        await ctx.send("```This channel is already subscribed to today's top ideas.```")


@bot.command()
async def off(ctx):
    Feed.unsubscribe_from_feeds(feeds, ctx.channel)
    await Feed.save_subscriptions()
    await ctx.send("```This channel has been unsubscribed.```")


@bot.command(aliases=["commands", "help"])
async def cmd(ctx):
    embed = discord.Embed(color=0xc200a8)
    embed.set_author(name="I keep you updated on new business ideas"
                          " generated by IdeasAI", url=f"{info_url}")
    embed.add_field(name="Commands",
                    value="`!ideas help`, `!ideas cmd` or `!ideas commands` › Show this message"
                          "\n"
                          "\n`!ideas new` › Subscribe to\u2004🔔\u2004new ideas"
                          "\n`!ideas top` › Subscribe to\u2004❤️\u2004today's top ideas"
                          "\n"
                          "\n`!ideas off` › Unsubscribe"
                          "\n\u200b")
    embed.set_footer(text="👨‍💻 by @tiagosvf, ⚡ by ideasai.net")
    await ctx.send(embed=embed)


def get_ideas():
    try:
        global current_threads
        current_threads += 1

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
                        async_from_sync(channel.send, embed=embed)
                elif elem.name == "h2":
                    break

            feed.recent_ideas = feed.recent_ideas[-10:]

        current_threads -= 1
    except requests.exceptions.ReadTimeout:
        pass


@tasks.loop(seconds=refresh_frequency)
async def get_ideas_task():
    if current_threads < MAX_THREADS:
        get_ideas_thread = threading.Thread(target=get_ideas, name="Getter")
        get_ideas_thread.start()


def main():
    bot.run(token)


if __name__ == "__main__":
    main()
