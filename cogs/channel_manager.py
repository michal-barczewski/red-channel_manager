import discord
import os
import logging

from discord.ext import commands
from discord import ChannelType

from cogs.utils.dataIO import dataIO

default_data = {
    'channelGroups': {}
}
logger = logging.getLogger("channel_manager")
logger.setLevel(logging.DEBUG)
class ChannelManager:
    """My custom cog that does stuff!"""

    def __init__(self, bot):
        self.bot = bot
        self.data = None
        self.baseDataPath = "data/channel_manager"
        self.dataFilePath = os.path.join(self.baseDataPath,"data.json")
        if not os.path.exists(self.baseDataPath):
            os.mkdir(self.baseDataPath)
        if not os.path.isfile(self.dataFilePath) \
                or not dataIO.is_valid_json(self.dataFilePath):
            self.data = default_data
            self.save_data()
        else:
            self.data = dataIO.load_json(self.dataFilePath)
        logger.debug("self data is: {0}",self.data)

    def save_data(self):
        dataIO.save_json(self.dataFilePath, self.data)

    @commands.command(pass_context=True)
    async def showdata(self,ctx):
        await self.bot.say(self.data)

    @commands.command(pass_context=True)
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
    @commands.command(pass_context=True)
    async def listchans(self, ctx):
        all_chans = ctx.message.server.channels
        voice_chans = [channel for channel in all_chans if channel.type==ChannelType.voice]
        lines = ["{0.name} - {0.position}".format(channel) for channel in voice_chans]
        await self.bot.say("\n".join(lines))

    @commands.command(pass_context=True)
    async def move(self, ctx, name, position):
        chan = findByName(ctx.message.server.channels, name)
        if (chan is not None):
            await self.bot.say("moving channel '{0}' to position '{1}'".format(chan, position))
            edited_chan = await self.bot.edit_channel(chan,position=position)
            await self.bot.say("edited chan '{0}'".format(edited_chan))

    @commands.command(pass_context = True)
    async def addgroup(self, ctx, groupName):
        server = ctx.message.server
        if (server.id not in self.data['channelGroups']):
            self.data['channelGroups'][server.id] = {}
        self.data['channelGroups'][server.id][groupName] = True
        self.save_data()

    #def update(self):
        #groupToChannels = {}
        #for (se)



def findByName(channels, name):
    for channel in channels:
        if (channel.name==name):
            return channel

def setup(bot):
    bot.add_cog(ChannelManager(bot))
