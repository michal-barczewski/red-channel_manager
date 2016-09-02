import discord
import os
import logging
import re

from discord.ext import commands
from discord import ChannelType

from red import send_cmd_help
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


logger = logging.getLogger("red.channel_manager")
logger.setLevel(logging.DEBUG)
class ChannelManager:
    """My custom cog that does stuff!"""

    def __init__(self, bot):
        self.bot = bot
        self.data = None
        self.baseDataPath = "data/channel_manager"
        self.dataFilePath = os.path.join(self.baseDataPath,"data.json")
        logger.debug("attempting to load settings from {0}".format(self.dataFilePath))
        if not os.path.exists(self.baseDataPath):
            logger.debug("settings directory at path {0} doesn't exist, creating it")
            os.mkdir(self.baseDataPath)
        if not os.path.isfile(self.dataFilePath) \
                or not dataIO.is_valid_json(self.dataFilePath):
            logger.debug("settings file doesn't exits, creating new file with default settings")
            self.data = {}
            self.save_data()
        else:
            self.data = dataIO.load_json(self.dataFilePath)
        logger.debug("loaded settings file with data: {0}".format(self.data))

    def save_data(self):
        dataIO.save_json(self.dataFilePath, self.data)

    @commands.group(pass_context=True)
    @checks.mod_or_permissions()
    async def cm(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @cm.command(pass_context=True)
    async def showdata(self,ctx):
        await self.bot.say(self.data)

    @cm.command(pass_context=True)
    async def addchan(self, ctx, new_name: str):
        """This does stuff!"""

        #Your code will go here
        #all_chans = [(channel.server.name,channel.name,channel.type, channel.position) for channel in self.bot.get_all_channels()]
        server = ctx.message.server
        if (server is not None):
            msg = "trying to create channel with name {new_name}, on server {server}".format(new_name=new_name, server=server)
            await self.bot.say(msg)
            new_chan = await self.bot.create_channel(server = server, name=new_name, type=ChannelType.voice)
            await self.bot.say("created channel {0}".format(new_chan))
            #await self.bot.say(all_chans)
        else:
            self.bot.say("no server id")
    @cm.command(pass_context=True)
    async def listchans(self, ctx):
        all_chans = ctx.message.server.channels
        voice_chans = [channel for channel in all_chans if channel.type==ChannelType.voice]
        lines = ["{0.name} - {0.position}".format(channel) for channel in voice_chans]
        await self.bot.say("\n".join(lines))

    @cm.command(pass_context=True)
    async def move(self, ctx, name, position):
        chan = findByName(ctx.message.server.channels, name)
        if (chan is not None):
            await self.bot.say("moving channel '{0}' to position '{1}'".format(chan, position))
            edited_chan = await self.bot.edit_channel(chan,position=position)
            await self.bot.say("edited chan '{0}'".format(edited_chan))

    @cm.command(pass_context = True)
    async def addgroup(self, ctx, group_name):
        channel_groups = self.get_channel_groups(ctx)

        channel_groups[group_name] = True
        self.save_data()

        logger.debug('added channel group {0!r}'.format(group_name))
        await self.bot.say('added channel group {0!r}'.format(group_name))

    @cm.command(name='removegroup', pass_context = True)
    async def remove_group(self, ctx, group_name):
        channel_groups = self.get_channel_groups(ctx)
        if group_name not in channel_groups:
            await self.bot.say('group {0!r} doesn\'t exist'.format(group_name))
        else:
            del channel_groups[group_name]
            self.save_data()
            await self.bot.say('removing group {0!r}'.format(group_name))

    @cm.command(name = 'upd', pass_context = True)
    async def update_groups(self, ctx):
        channel_groups = self.get_channel_groups(ctx)
        for group_name in channel_groups:
            await self.update_group(ctx.message.server, group_name)

    def create_channel_name(self, group_name, num):
        return '{group_name} #{num}'.format(group_name=group_name, num = num)

    async def update_group(self, server, group_name):
        logger.debug('updating channel group {0!r}'.format(group_name))
        pattern = re.compile(r'^('+re.escape(group_name)+r')\s+#(\d+)')
        logger.debug('using regex pattern {0!r}'.format(pattern))

        voice_chans = (channel for channel in server.channels if channel.type == ChannelType.voice)
        #group_chans = [channel for channel in voice_chans if pattern.match(channel.name)]
        group_chans = []
        for channel in voice_chans:
            match = pattern.match(channel.name)
            if match:
                chan_desc = {
                    'channel': channel,
                    'group_name': match.group(0),
                    'num': match.group(1)
                }
                group_chans.append(chan_desc)
        logger.debug('found channels for group {0!r}: {1!r}'.format(group_name, [ch['channel'].name for ch in group_chans]))

        first_chan_desc = None # first channel in group, rest of the channels should be put after this one if it exists
        if group_chans:
            first_chan_desc = group_chans[0]
            logger.debug('found first channel in group {0!r} - channel: {1.name!r}, position: {1.position!r}'.format(group_name, first_chan_desc['channel']))
        else:
            chan_name = self.create_channel_name(group_name,1)
            logger.info('group {0!r} had no channels, creating new channel with name {1!r}'.format(group_name, chan_name))
            await self.bot.create_channel(server=server, name=chan_name, type = ChannelType.voice)

        first_empty = None
        for idx, chan in enumerate(group_chans):
            if not chan['channel'].voice_members:
                first_empty = idx

        # build a list describing what channels in the group we currently have
        # we expect to have continous numbering, without duplicates, with one empty channel past the last used channel existing




    def get_data_for_server(self, ctx):
        #TODO: create a class to manage loading/saving data per server, with fields instead of using dict keys, handle saving sets
        server = ctx.message.server
        if server.id not in self.data:
            self.data[server.id] = {}
            self.save_data()
        return self.data[server.id]

    def get_channel_groups(self, ctx):
        data = self.get_data_for_server(ctx)
        if 'channelGroups' not in data:
            data['channelGroups'] = {}
            self.save_data()
        return data['channelGroups']

def findByName(channels, name):
    for channel in channels:
        if (channel.name==name):
            return channel

def setup(bot):
    bot.add_cog(ChannelManager(bot))
