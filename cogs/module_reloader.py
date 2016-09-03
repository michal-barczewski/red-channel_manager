import asyncio
import glob
import logging
import os
import traceback

from discord.ext import commands

from cogs.owner import CogNotFoundError, NoSetupError, CogLoadError
from red import set_cog

logger = logging.getLogger("red.module_reloader")
logger.setLevel(logging.DEBUG)
class ModuleReloader:
    def __init__(self, bot):
        logger.debug('loading module')
        self.bot = bot
        self.update_period = 1
        self.prev = []

    async def reload_module(self, module):
        try:
            module = os.path.splitext(os.path.basename(module))[0]
        except:
            pass
        if "cogs." not in module:
            module = "cogs." + module
        owner_cog = self.bot.get_cog('Owner')
        logger.info("trying to reload module {0}".format(module))
        try:
            owner_cog._unload_cog(module, reloading=True)
        except:
            pass

        try:
            owner_cog._load_cog(module)
        except CogNotFoundError:
            logger.warn("module {0} cannot be found.".format(module))
        except NoSetupError:
            logger.warn("module {0} does not have a setup function.".format(module))
        except CogLoadError as e:
            logger.error("loading module {0} failed".format(module))
            logger.exception(e)
            #traceback.print_exc()
        else:
            set_cog(module, True)
            await owner_cog.disable_commands()

    def check_for_modifications(self):
        cogs = glob.glob('cogs/*.py')
        after = {f: os.stat(os.path.realpath(f)) for f in cogs}
        if not self.prev:
            self.prev = after
            return []
        modified = []
        for f, stat in after.items():
            if f in self.prev:
                prev_stat = self.prev[f]
                if stat.st_mtime != prev_stat.st_mtime:
                    modified.append(f)
        self.prev = after
        return modified

    async def reload_modules(self, modules):
        for f in modules:
            await self.reload_module(f)



    async def update_scheduler(self):
        while self == self.bot.get_cog('ModuleReloader'):
            logger.debug('checking for modified cogs')
            modified = self.check_for_modifications()
            if modified:
                logger.info('reloading modified cogs: {0}'.format(modified))
                await self.reload_modules(modified)
            await asyncio.sleep(self.update_period)

    @commands.command(name='listcogs', pass_context = True)
    async def _list_cogs(self):
        cogs = [os.path.realpath(f) for f in glob.glob("cogs/*.py")]
        for c in cogs:
            pass
        await self.bot.say('cogs: {0}'.format(cogs))
    @commands.command(name='checkmodified', pass_context = True)
    async def check_modified_cmd(self):
        modified = self.check_for_modifications()
        await self.reload_modules(modified)
        await self.bot.say('modified cogs: {0}'.format(modified))


    @commands.command(name='mrreload', pass_context = True)
    async def reload_cmd(self, ctx, module):
        await self.reload_module(module)

def setup(bot):
    mr = ModuleReloader(bot)
    bot.add_cog(mr)
    bot.loop.create_task(mr.update_scheduler())