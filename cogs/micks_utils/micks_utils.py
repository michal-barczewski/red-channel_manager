from typing import Iterable, Any

from discord import Server, User
from discord.ext.commands import Bot
from discord.ext.commands.core import command
from discord.role import Role

from cogs.utils import checks


class MicksUtils:
    def __init__(self, bot: Bot):
        self.bot = bot

    @command(name='listrole', pass_context=True)
    @checks.mod_or_permissions(administrator=True, moderator=True)
    async def _list_role(self, ctx, rolename: str):
        """List all members for a given role"""
        server = ctx.message.server  # type: Server
        #role = discord.utils.get(server.roles, name=rolename.lower())  # type: Role
        role = get_role_by_name(server.roles, rolename) # cause we want to be case insensitive
        if role is None:
            roles = sorted(server.roles, key=lambda role: role.name.lower())
            await self.bot.say(create_message_from_list('Couldn\'t find role {role}, available roles are:\n'
                                                        .format(role=rolename),
                                                        '- {0.name}', roles))
        else:
            users = sorted(get_users_for_role(server.members, role.name),
                           key=lambda user: user.name.lower())
            await self.bot.say(create_message_from_list('Users for role {role}:\n'.format(role=rolename),
                                                        '- {0.name}', users))


def get_role_by_name(roles: Iterable[Role], rolename: str):
    for role in roles:
        if role.name.lower() == rolename.lower():
            return role


def get_users_for_role(users: Iterable[User], rolename: str):
    users_with_role = []
    for user in users:
        if rolename in (role.name for role in user.roles):
            users_with_role.append(user)
    return users_with_role


def create_message_from_list(prefix: str, line_format: str, message_list: Iterable[Any]):
    message_lines = ['```', prefix]
    lines = [line_format.format(line_args) for line_args in message_list]
    message_lines.extend(lines)
    message_lines.append('```')
    return "\n".join(message_lines)


def setup(bot: Bot):
    s = MicksUtils(bot)
    bot.add_cog(s)
