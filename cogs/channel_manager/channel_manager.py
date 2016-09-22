import asyncio
import json
import logging
import os
import random
import re
from collections import defaultdict, ChainMap
from datetime import datetime, timedelta
from operator import itemgetter
from typing import Any, List, Dict, Union, Set, Callable, Iterable, NewType

import discord
from discord import ChannelType, endpoints
from discord.channel import Channel
from discord.ext import commands

from cogs.utils import checks
from cogs.utils.dataIO import dataIO, CorruptedJSON

logger = logging.getLogger("red.channel_manager")
logger.setLevel(logging.INFO)

BaseValueType = NewType('BaseValueType', Union[str, int, float])
ValueType = NewType('ValueType', Union[BaseValueType, List[BaseValueType], Dict[str, BaseValueType]])


class Config:
    def __init__(self, defaults: Dict[str, ValueType] = None, data: Dict[str,Dict[str,BaseValueType]] = None):
        self.data = defaultdict(dict)
        if data is not None:
            self.data.update(data)
        self.defaults = defaults if defaults is not None else {}  # type: Dict[str, ValueType]

    def __eq__(self, other):
        if not isinstance(other, Config):
            return False
        elif self.defaults != other.defaults:
            return False
        else:
            return self.data == self.data

    def __str__(self):
        return str(self.__dict__)

    def get_location(self, path: List[str]):
        if path is None or len(path) == 0:
            return self.data['']
        location = ChainMap(self.data[''], self.defaults)
        current_path = ''
        for key in path:
            current_path = os.path.join(current_path, key)
            location = location.new_child(self.data[current_path])
        return location

    def set_var(self, name: str, value: ValueType, path: List[str] = None):
        if isinstance(value, (str, int, float, List, Dict)):
            location = self.get_location(path)
            location[name] = value
        else:
            raise TypeError('value should be one of following types: str, int, float, List, Dict')

    def delete_var(self, path: List[str], name: str):
        location = self.get_location(path)
        if name in location[name]:
            del location[name]

    def get_var(self, name: str, path: Iterable[str] = None) -> ValueType:
        """Retrieve variable value from specified path

        If value doesn't exist at specified path, value is looked up at lower levels,

        If variable is of mutable type then a copy of it will be returned, to modify it use set_var with copy as value

        :param name: name of the variable to retrieve
        :param path: path of the variable
        :return: value of the variable
        """

        location = self.get_location(path)
        value = location.get(name)
        logger.debug('retrieved variable {0!r}: value {1!r}, type {2!r}'.format(name, value, type(value)))
        if isinstance(value, (str, int, float)) or value is None:
            return value
        elif isinstance(value,(List,Set,Dict)):
            return value.copy()
        else:
            raise TypeError('tried to retrieve value of unsupported type (this should not be possible)')

    def save(self, file_name: str):
        with open(file_name, 'w+') as config_file:
            json.dump(self.data, config_file)

    def load(self, file_name: str):
        with open(file_name, 'r') as config_file:
            json_str = config_file.read()
            self.data = json.loads(json_str)


default_server_vars = {
    'min_empty_channels': {
        'type': int,
        'value': 2,
        'help': 'Minimum amount of channels that should be present in the group, '
                'if there are more/less channels will be created/remove'
    },
    'channel_timeout': {
        'type': int,
        'value': 1,  # minutes
        'help': 'Amount of time in minutes since last activity before channel may be deleted'
    },
    'user_limit': {
        'type': int,
        'value': 0,
        'help': 'Default user_limit to set for new groups, currently does not work'
    }
}


def get_vars_list_for_help():
    var_lines = ['{0:20s} - {help}'.format(var_name, **var) for var_name, var in default_server_vars.items()]
    return 'Variables:\n' + ('\n'.join(var_lines))


class ChannelManager:
    def __init__(self, bot):
        logger.info('loading module')
        self.bot = bot  # type: discord.Client

        self.paused = False
        self.enabled = True

        self.update_period = 10

        self.config = None  # type: Config
        self.baseDataPath = "data/channel_manager"
        self.dataFilePath = os.path.join(self.baseDataPath, "config.json")

        self.channel_activity = {}  # type: Dict[Channel, datetime]

        defaults = {
            'min_empty_channels': default_server_vars['min_empty_channels']['value'],
            'channel_timeout': default_server_vars['channel_timeout']['value']
        }

        logger.debug("attempting to load settings from {0}".format(self.dataFilePath))
        if not os.path.exists(self.baseDataPath):
            logger.debug("settings directory at path {0} doesn't exist, creating it")
            os.mkdir(self.baseDataPath)
        if not os.path.isfile(self.dataFilePath):
            logger.debug("settings file doesn't exits, creating new file with default settings")
            self.config = Config(defaults=defaults)
            self.save_config()
        else:
            try:
                data = dataIO.load_json(self.dataFilePath)
            except CorruptedJSON:
                data = {}
            self.config = Config(data=data, defaults=defaults)

        logger.debug("loaded settings file with data: {0}".format(self.config))

    def save_config(self):
        self.config.save(self.dataFilePath)

    def get_server_var(self, server: discord.Server, key: str) -> Union[str, int, float]:
        return self.config.get_var(key, [server.id])

    def set_server_var(self, server, key, value):
        self.config.set_var(key, value, [server.id])
        self.save_config()

    def get_group_var(self, server: discord.Server, group_name: str, name: str):
        return self.config.get_var(name, [server.id, group_name])

    def set_group_var(self, server: discord.Server, group_name: str, name: str, value):
        self.config.set_var(name, value, [server.id, group_name])
        self.save_config()

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @commands.group(pass_context=True)
    @checks.mod_or_permissions()
    async def cm(self, ctx):
        """Automatic channel creation"""
        if ctx.invoked_subcommand is None:
            await self.send_cmd_help(ctx)

    @cm.command(help='Enables channel management')
    async def enable(self):
        # TODO: make this a per server setting
        self.enabled = True
        await self.bot.say("Channel management enabled.")

    @cm.command(help='Disables channel management')
    async def disable(self):
        self.enabled = False
        await self.bot.say("channel management disabled.")

    @cm.command(help='Check if channel management is enabled')
    async def is_enabled(self):
        await self.bot.say("Channel management is: {0}".format("enabled" if self.enable else "disabled"))

    @cm.group(pass_context=True, help='Debug functions, not for normal usage')
    async def debug(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.send_cmd_help(ctx)

    @debug.command(pass_context=True)
    @checks.is_owner()
    async def set_level(self, ctx, level: str):
        """Sets debug level to specified level. Level can be:
        'debug', 'info', 'warning', 'error', 'critical'
        """
        levels = {'debug', 'info', 'warning', 'error', 'critical'}
        if level.lower() in levels:
            logger.setLevel(logging.getLevelName(level.upper()))
            await self.bot.say('setting debug level to: {0}'.format(level))
        else:
            self.send_cmd_help(ctx)

    @debug.command(help='Prints current configuration')
    async def showdata(self):
        await self.bot.say(self.config)

    @debug.command(pass_context=True, no_pm=True)
    async def addchan(self, ctx, new_name: str, user_limit):
        server = ctx.message.server
        msg = "trying to create channel with name {new_name}, on server {server}".format(new_name=new_name,
                                                                                         server=server)
        await self.bot.say(msg)
        await self.create_channel(server=server, name=new_name, type=ChannelType.voice,
                                  user_limit=user_limit)

    @debug.command(pass_context=True)
    async def listchans(self, ctx):
        all_chans = ctx.message.server.channels
        voice_chans = [channel for channel in all_chans if channel.type == ChannelType.voice]
        voice_chans.sort(key=lambda channel: channel.position)
        message = create_message_from_list('Channels: \n',
                                           '{0.position:3d} - {0.name}', voice_chans)
        await self.bot.say(message)

    @debug.command(pass_context=True)
    async def move(self, ctx, name, position):
        chan = find_by_name(ctx.message.server.channels, name)
        if chan is not None:
            await self.bot.say("moving channel '{0}' to position '{1}'".format(chan, position))
            edited_chan = await self.bot.edit_channel(chan, position=position)
            await self.bot.say("edited chan '{0}'".format(edited_chan))

    @debug.command(name='pause', pass_context=True)
    async def pause_loop(self):
        self.paused = not self.paused
        await self.bot.say('paused is now: {0!r}'.format(self.paused))

    @debug.command(name='upd', pass_context=True)
    async def upd(self, ctx):
        await self.update_groups(ctx.message.server)

    @debug.command(name='movechans', pass_context=True)
    async def shuffle(self, ctx, method='sort'):
        logger.info('moving channels')
        server = ctx.message.server
        voice_channels = [channel for channel in server.channels if channel.type == ChannelType.voice]
        result = None
        if method == 'sort':
            logger.debug('sorting voice channels')
            result = sorted(voice_channels, key=lambda chan: chan.name)
        elif method == 'random':
            logger.debug('randomizing voice channels: {0!r}'.format(voice_channels))
            result = list(voice_channels)
            random.shuffle(result)
        else:
            await self.bot.say('Specified method {0!r} is not valid'.format(method))
            return
        # await self.move_chans(voice_channels, result)
        await self.move_channels(server, channels=result)

    @cm.command(name='addgroup', no_pm=True, pass_context=True, help='Add channel group to manage')
    async def _cm_add_group(self, ctx, group_name):
        await self.add_group(ctx.message.server, group_name)

    async def add_group(self, server: discord.Server, group_name: str):
        server_ids = self.config.get_var('server_ids')  # type: List[int]
        if not server_ids:
            server_ids = []
        if server.id not in server_ids:
            server_ids.append(server.id)
            self.config.set_var('server_name', server.name,[server.id])  # just for reference in config file
        self.config.set_var('server_ids', server_ids)

        channel_groups = self.config.get_var('channel_groups', [server.id])  # type: List[str]
        if channel_groups is None:
            channel_groups = []
        if group_name not in channel_groups:
            channel_groups.append(group_name)
        else:
            await self.bot.say('group {0!r} already exists'.format(group_name))
            return
        self.config.set_var('channel_groups', channel_groups, [server.id])
        self.save_config()

        logger.debug('added channel group {0!r}'.format(group_name))
        await self.bot.say('added channel group {0!r}'.format(group_name))

    @cm.command(name='removegroup', pass_context=True, no_pm=True,
                help='Remove channel group, deletes channels from that group unless delete is False')
    async def _cm_remove_group(self, ctx, group_name, delete=True):
        await self.remove_group(ctx.message.server, group_name, delete)

    async def remove_group(self, server: discord.Server, group_name: str, delete=False):
        channel_groups = self.config.get_var('channel_groups', [server.id])  # type: List[str]
        if channel_groups is None:
            channel_groups = []

        if group_name not in channel_groups:
            await self.bot.say('group {0!r} doesn\'t exist'.format(group_name))
        else:
            channel_groups.remove(group_name)
            self.config.set_var('channel_groups', channel_groups, [server.id])
            self.save_config()
            await self.bot.say('removing group {0!r}'.format(group_name))
            logger.debug('delete is: {0!r}'.format(delete))
            if delete:
                for channel in self.get_channels_for_group(server, group_name):
                    await self.delete_channel(server, channel)

    @cm.command(name='listgroups', pass_context=True, no_pm=True, help='Show currently managed channel groups')
    async def list_groups(self, ctx):
        channel_groups = self.config.get_var('channel_groups', [ctx.message.server.id])
        if channel_groups:
            message = create_message_from_list(prefix='Channel groups:\n', line_format='{0}',
                                               message_list=sorted(channel_groups))
            await self.bot.say(message)
        else:
            await self.bot.say('There are no channel groups.')

    @cm.command(name='get', pass_context=True, no_pm=True,
                help='Get value of server variable\n' + get_vars_list_for_help())
    async def _cm_get(self, ctx, var_name: str):
        if var_name is None:
            await self.bot.say('available variables are: {0!r}'.format(default_server_vars.keys()))
        else:
            value = self.config.get_var(var_name, [ctx.message.server.id])
            await self.bot.say('{0} = {1!r}'.format(var_name, value))

    @cm.command(name='getall', pass_context=True)
    async def _cm_get_all(self, ctx):
        list=((var_name, self.get_server_var(ctx.message.server,var_name)) for var_name in default_server_vars.keys())
        logger.debug('list: {0}'.format(list))
        message = create_message_from_list('Server variables:', '{0[0]:20s} = {0[1]!r}',list)
        await self.bot.say(message)

    @cm.command(name='set', pass_context=True, no_pm=True,
                help='Set value of server variable\n' + get_vars_list_for_help())
    async def _cm_set(self, ctx, var_name: str, value: str):
        server = ctx.message.server
        try:
            if value == 'None':
                self.config.delete_var([server.id], var_name)
            else:
                type_fun = default_server_vars[var_name]['type']  # type: Callable[[Any], None]
                parsed = type_fun(value)
                self.config.set_var(var_name, parsed, [server.id])
            await self.bot.say('setting {0} = {1}'.format(var_name, value))
            self.save_config()
        except ValueError as e:
            await self.bot.say(e)
        except KeyError:
            await self.bot.say('unknown variable {0!r}'.format(var_name))

    @staticmethod
    def get_channel_name_pattern(group_name):
        channel_name_pattern = re.compile(r'^' + re.escape(group_name) + r'\s+#(\d+)')
        return channel_name_pattern

    @staticmethod
    def create_channel_name(group_name, num):
        return '{group_name} #{num}'.format(group_name=group_name, num=num)

    @staticmethod
    def get_voice_channels(server):
        return [channel for channel in server.channels if channel.type == ChannelType.voice]

    def get_channel_number_in_group(self, group_name, channel):
        pattern = self.get_channel_name_pattern(group_name)
        match = pattern.match(channel.name)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

    def get_channels_for_group(self, server, group_name):
        pattern = self.get_channel_name_pattern(group_name)
        group_chans = [channel for channel in server.channels
                       if channel.type == ChannelType.voice
                       and pattern.match(channel.name)
                       ]
        return group_chans

    async def create_group_channel(self, server, group_name, num):
        chan_name = self.create_channel_name(group_name, num)
        logger.info('group {0!r} had no channels, creating new channel with name {1!r}'.format(group_name, chan_name))
        #user_limit = self.get_server_var(server, 'user_limit')
        # await self.create_channel(server=server, name=chan_name, type=ChannelType.voice, user_limit=user_limit)
        await self.bot.create_channel(server=server, name=chan_name, type=ChannelType.voice)

    async def update_scheduler(self):
        while self == self.bot.get_cog('ChannelManager'):
            if self.enabled and not self.paused:
                server_ids = self.config.get_var('server_ids')
                logger.debug('got server_ids: {0!r}'.format(server_ids))
                if server_ids is not None:
                    for server_id in server_ids:
                        server = self.bot.get_server(server_id)
                        logger.debug("attempting to get server with id {0}, result: {1}".format(server_id, server))
                        if server:
                            await self.update_groups(server)
            await asyncio.sleep(self.update_period)

    async def update_groups(self, server):
        if not self.enabled:
            return
        channel_groups = self.config.get_var('channel_groups', [server.id])
        for group_name in channel_groups:
            await self.update_group(server, group_name)
        await self.fix_channel_positions(server)

    async def update_group(self, server, group_name):
        pattern = self.get_channel_name_pattern(group_name)
        min_empty_channels = self.get_server_var(server, 'min_empty_channels')
        logger.debug('updating channel group {0!r}'.format(group_name))

        group_channels = self.get_channels_for_group(server, group_name)

        if not group_channels:
            # if there are no channels for this group - create one and exit
            await self.create_group_channel(server, group_name, 1)
            return
        # create channels if needed
        chan_to_numbers = {}
        chan_numbers = []
        empty_chans = []
        for channel in group_channels:
            if not channel.voice_members:
                empty_chans.append(channel)

            match = pattern.match(channel.name)
            if match:
                num = int(match.group(1))
                chan_to_numbers[channel] = num
                chan_numbers.append(num)
        n_channels_to_create = max(0, min_empty_channels - len(empty_chans))
        if n_channels_to_create > 0:
            logger.info('group {0!r} has {1!r} empty channels, min_empty is {min_empty}, '
                        'will create {n_channels_to_create!r} channels'
                        .format(group_name, len(empty_chans), min_empty=min_empty_channels,
                                n_channels_to_create=n_channels_to_create))
            free_nums = find_free_numbers(chan_numbers, n_channels_to_create)
            for i in range(0, n_channels_to_create):
                chan_name = self.create_channel_name(group_name, free_nums[i])
                await self.bot.create_channel(server=server, name=chan_name, type=ChannelType.voice)

        # check if we should and can remove some channels
        n_to_remove = len(empty_chans) - min_empty_channels
        if n_to_remove > 0:
            logger.info('group {group_name!r} has {n_empty!r} empty channels, '
                        'will attempt to remove {n_to_remove!r} channels'
                        .format(group_name=group_name, n_empty=len(empty_chans), n_to_remove=n_to_remove))
            # create a list of empty channels sorted by number, remove the highest numbered ones
            empty_channels_with_number = [{'channel': channel, 'num': chan_to_numbers[channel]} for channel in
                                          empty_chans]
            empty_channels_with_number.sort(key=itemgetter('num'))
            for idx, chan_dict in enumerate(empty_channels_with_number):
                if idx >= min_empty_channels:
                    channel = chan_dict['channel']
                    await self.delete_channel(server, channel)

    def channel_is_active(self, server, channel):
        last_activity = None
        if channel in self.channel_activity:
            last_activity = self.channel_activity[channel]
        timeout = timedelta(minutes=self.get_server_var(server, 'channel_timeout'))
        if last_activity is None or ((datetime.now() - timeout) > last_activity):
            return False
        else:
            return True

    async def delete_channel(self, server, channel, force=False):
        if force:
            await self.bot.delete_channel(channel=channel)

        if not self.channel_is_active(server, channel):
            logger.debug("removing channel {0.name}".format(channel))
            await self.bot.delete_channel(channel=channel)
        else:
            logger.debug("not removing channel {0.name!r} due to recent activity"
                         .format(channel))

    async def fix_channel_positions(self, server):
        if not self.enabled:
            return
        channel_groups = self.get_server_var(server, 'channel_groups')  # type: Set[str]
        if not channel_groups:
            logger.debug('channel_groups was empty or None: {0!r}'.format(channel_groups))
            return
        channels = self.get_voice_channels(server)  # type: List[discord.Channel]
        channels.sort(key=lambda ch: ch.position)
        channels_original = list(channels)
        logger.debug("initial channel positions: {0}".format([ch.name for ch in channels]))
        group_regexps = {group: self.get_channel_name_pattern(group) for group in channel_groups}
        channels_by_group = {group: [] for group in channel_groups}
        group_anchors = {}
        for idx, channel in enumerate(list(channels)):
            for group, regex in group_regexps.items():
                chan_num = self.get_channel_number_in_group(group_name=group, channel=channel)
                if chan_num is not None:
                    if chan_num == 1:
                        group_anchors[channel] = group
                    elif chan_num != 1:
                        channels.remove(channel)
                        channels_by_group[group].append({'num': chan_num, 'channel': channel})
        logger.debug('channels by group: {0!r}'.format(channels_by_group))
        result_channels = []
        for channel in channels:
            if channel not in group_anchors:
                # a channel that's not in any group (else it'd have been picked up in earlier processing)
                # leave it where it is
                result_channels.append(channel)
            if channel in group_anchors:
                result_channels.append(channel)
                # first channel in a group, append it where it was
                group = group_anchors[channel]
                # get all channels in that group and add them in order
                group_channels = channels_by_group[group]
                group_channels.sort(key=itemgetter('num'))
                user_limit = channel.user_limit
                for grp_channel in group_channels:
                    group_channel = grp_channel['channel']  # type: discord.Channel
                    if group_channel.user_limit != user_limit:
                        await self.bot.http.edit_channel(group_channel.id, user_limit=user_limit)
                    result_channels.append(group_channel)
        logger.debug('final channel positions: {0}'.format([channel.name for channel in result_channels]))
        changes = False
        for i, channel in enumerate(result_channels):
            if channel != channels_original[i]:
                changes = True
                break
        if changes:
            logger.debug("moving channels")
            await self.move_channels(server, result_channels)
        else:
            logger.debug('no changes in channel order')

    async def move_channels(self, server: discord.Server, channels: List[discord.Channel]):
        payload = [{'id': c.id, 'position': index} for index, c in enumerate(channels)]
        url = '{0}/{1.id}/channels'.format(endpoints.SERVERS, server)
        logger.debug('using url: {0}'.format(url))
        logger.debug('using payload: {0!r}'.format(payload))
        await self.bot.http.patch(url, json=payload, bucket="move_channel")

    async def create_channel(self, server: discord.Server, name: str, type: ChannelType, user_limit: int,
                             permission_overwrites=None):
        # doesn't work atm, reason unknown
        url = discord.http.HTTPClient.GUILDS + '/{0}/channels'.format(server.id)
        payload = {
            'name': name,
            'type': str(type),
            'permission_overwrites': []
        }
        # if user_limit is not None:
        #    payload['user_limit'] = user_limit

        if permission_overwrites is not None:
            payload['permission_overwrites'] = permission_overwrites

        logger.debug('url: {0}'.format(url))
        logger.debug('payload: {0}'.format(payload))
        return self.bot.http.post(url, json=payload, bucket="create_channel")


def create_message_from_list(prefix: str, line_format: str, message_list: Iterable[Any]):
    message_lines = ['```', prefix]
    lines = [line_format.format(line_args) for line_args in message_list]
    message_lines.extend(lines)
    message_lines.append('```')
    return "\n".join(message_lines)


def find_free_numbers(numbers: List[int], n_to_find: int):
    free_numbers = []
    max_num = max(numbers)
    for i in range(1, max_num):
        if i not in numbers:
            free_numbers.append(i)
    n_found = len(free_numbers)
    for i in range(0, n_to_find - n_found):
        free_numbers.append(max_num + i + 1)

    return free_numbers


def find_by_name(channels: List[Channel], name: str):
    for channel in channels:
        if channel.name == name:
            return channel


def install_dep(dep_name):
    try:
        import pip
        logger.debug('trying to install: ' + dep_name)
        pip.main(['install', dep_name])
    except Exception as e:
        logger.error(e)


def setup(bot):
    cm = ChannelManager(bot)
    bot.add_cog(cm)
    bot.loop.create_task(cm.update_scheduler())

    async def on_channel_create(channel):
        logger.info("on_channel_create, channel: {0}".format(channel))
        await cm.fix_channel_positions(channel.server)

    async def on_voice_state_update(before, after):
        chan_before = before.voice.voice_channel
        chan_after = after.voice.voice_channel
        if chan_before:
            cm.channel_activity[chan_before] = datetime.now()
        if chan_after:
            cm.channel_activity[chan_after] = datetime.now()
        logger.info(cm.channel_activity)
        await cm.update_groups(before.server)
        logger.info('on_voice_state_update, channel {chan_after},{chan_before}, before: {0}, after: {1}'
                    .format(before, after, chan_before=chan_before, chan_after=chan_after))

    bot.add_listener(on_channel_create, 'on_channel_create')
    # bot.add_listener(on_channel_update, 'on_channel_update')
    bot.add_listener(on_voice_state_update, 'on_voice_state_update')
