from .TFS import TFS

async def setup(bot):
    await bot.add_cog(TFS())