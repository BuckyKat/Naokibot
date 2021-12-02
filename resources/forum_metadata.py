from redbot.core import Config
import aiohttp
from bs4 import BeautifulSoup
import discord

from .helper_functions import fetch
from .user_profile import UserProfile

from redbot.core.commands import Context


class Metadata:  # Metadata is probably not a good name
    def __init__(self):
        self.config: Config = Config.get_conf(self, identifier=867530999999)
        default_data = {
            "character_profiles": {"0": None},
            "unclaimed_characers": {"0": "no char"},
            "no_posts": [],
        }
        self.config.init_custom("metadata", 1)
        self.config.register_custom("metadata", **default_data)
        self.profiles = UserProfile()

    def get_profile(self, ctx, num):
        profile_dict = self.config.custom("metadata", ctx.guild.id).character_profiles()
        return discord.Embed.from_dict(profile_dict[num])

    async def _fetch_character_profile(self, ctx, num, discord_name="Unkown"):
        """takes an id and scrapes the forum for that character's profile.

        Args:
            num (int): The id of the character to search for.

        Returns:
            [str]: The name of the character, 'no posts' if there are no posts, or 'no char' if no character is found.
        """
        from .character import Character

        discord_name = await self._get_discord_id_by_character_id(ctx, num)
        recent_url = "http://themistborneisles.boards.net/user/" + str(num) + "/recent"
        async with aiohttp.ClientSession() as session:
            html = await fetch(session, recent_url)
            soup_object = BeautifulSoup(html, "html.parser")
        _profile = soup_object.find(class_="mini-profile")
        if _profile:
            return Character(_profile, soup_object, num, discord_name)

        if "No posts were found." in str(soup_object):
            return "no posts"
        elif "The user you are trying to access could not be found." in str(
            soup_object
        ):
            return "no char"

    async def get_character(self, ctx, character):
        char_id = await self.get_character_id(ctx, character)
        if char_id == None or not await self._character_exists(ctx, char_id):
            await self._update_characters(ctx)
        async with self.config.custom("metadata", ctx.guild.id).character_profiles() as profile_dict:
            if await self._character_exists(ctx, char_id):
                print(profile_dict[str(char_id)])
                return profile_dict[str(char_id)]
            

    async def get_character_id(self, ctx, character):
        if type(character) == str:
            if character.isdigit():
                return await self.get_character_id(ctx, int(character))
            else:
                char_id = await self._get_character_id_by_display_name(ctx, character)
                if char_id == None:
                    return None
                return await self.get_character_id(ctx, int(char_id))
        elif type(character) == int:
            if await self._character_exists(ctx, character):
                return character
        return None

    async def _update_characters(self, ctx: Context, timeout=0):
        """Finds the last character and searches the forum for characters after that.
        Characters that are found are updated in the config.
        """
        print('Updating')
        timed = True
        if timeout == 0:
            timed = False

        no_posts = []
        char_list = await self.config.custom("metadata", ctx.guild.id).character_profiles()
        keys = list(char_list.keys())
        keys.sort(key=lambda num: int(num))
        char_id = int(keys[-1])
        if char_id == 0:
            char_id = 1
        more_characters = True
        one_more = False
        while(more_characters):
            if one_more:
                more_characters = False
            if not await self._character_exists(ctx, char_id):
                char = await self._fetch_character_profile(ctx, char_id)
                if char == "no char":
                    one_more = True
                elif char == "no posts":
                    no_posts.append(char_id)
                    one_more = False
                else:
                    one_more = False
                    async with self.config.custom("metadata", ctx.guild.id).character_profiles() as profile_dict:
                        profile_dict.update({char_id: char.embed.to_dict()})
            
            char_id += 1
            if timed:
                timeout -= 1
                if timeout <= 0:
                    more_characters = False

        async with self.config.custom("metadata", ctx.guild.id).no_posts() as char_list:
            for char in no_posts:
                if char not in char_list:
                    char_list.append(char)

    async def _character_exists(self, ctx, character):
        char_list = await self.config.custom("metadata", ctx.guild.id).character_profiles()
        return str(character) in char_list.keys()

    async def _get_character_id_by_display_name(self, ctx, display_name):
        async with self.config.custom(
            "metadata", ctx.guild.id
        ).character_profiles() as char_list:
            for key, char in char_list.items():
                if char:
                    if char is not None and char['author']['name'].lower() == display_name.lower():
                        return key

    async def _get_discord_id_by_character_id(self, ctx, char_num):
        users = await self.profiles.data.all_users()
        results = []
        for user, data in users.items():
            for id in data["characters"]:
                if str(id) == str(char_num):
                    name = await ctx.bot.get_or_fetch_user(user)
                    results.append(str(name))
        return results[0] if len(results) else "Unknown"
