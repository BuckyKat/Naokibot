import aiohttp
import discord
from bs4 import BeautifulSoup
from redbot.core import Config
from redbot.core.commands import Context

from .helper_functions import fetch
from .user_profile import UserProfile


class Metadata:
    def __init__(self):
        """This class is used to save character profiles so that they can be accessed without scraping the forumn.
        This also makes it possible to get any character with posts by their display name.
        """
        self.config: Config = Config.get_conf(self, identifier=867530999999)
        default_data = {
            "character_profiles": {"0": None},
            "unclaimed_characers": {"0": ""},
            "no_posts": [],
        }
        self.config.init_custom("metadata", 1)
        self.config.register_custom("metadata", **default_data)
        self.profiles = UserProfile()

    def get_profile(self, ctx, num):
        """Gets a player profile from config as a discord embed object"""
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

        discord_name = await self.get_discord_id_by_character_id(ctx, num)
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
        """Gets a character profile by either dispay name or id.
        If the character does not exist all characters will be updated.
        """
        char_id = await self.get_character_id(ctx, character)
        if char_id == None or not await self._character_exists(ctx, char_id):
            await self._update_characters(ctx, character)
            char_id = await self.get_character_id(ctx, character)
        async with self.config.custom(
            "metadata", ctx.guild.id
        ).character_profiles() as profile_dict:
            if await self._character_exists(ctx, char_id):
                return profile_dict[str(char_id)]

    async def get_character_id(self, ctx, character):
        """This will take a character name or number and return the number of that charadcter."""
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

    async def _update_characters(self, ctx: Context, character=None, timeout=0):
        """Finds the last character and searches the forum for characters after that.
        Characters that are found are updated in the config.
        """
        print("Updating")
        await ctx.send("Give me a second to find that...")
        # if character is an int then just scrape it and return
        if type(character) == str and character.isdigit():
            character = int(character)

        if type(character) == int:
            char = await self._fetch_character_profile(ctx, character)
            async with self.config.custom(
                "metadata", ctx.guild.id
            ).character_profiles() as profile_dict:
                profile_dict.update({character: char.embed.to_dict()})
        else:
            # This is used to stop update after a certain number of runs. I used it for testing, it could be used to stop the bot in edge cases where multiple characters are deleted in a row.
            timed = True
            if timeout == 0:
                timed = False

            char_list = await self.config.custom(
                "metadata", ctx.guild.id
            ).character_profiles()  # get all the character profiles
            keys = list(char_list.keys())
            keys.sort(key=lambda num: int(num))

            char_id = 1

            more_characters = True
            one_more = False
            while (
                more_characters
            ):  # increments the characeter id by one and scrapes forum for characters w/ posts
                if one_more:
                    more_characters = False
                if not await self._character_exists(ctx, char_id):
                    char = await self._fetch_character_profile(ctx, char_id)
                    if char == "no char":
                        one_more = True
                    elif char == "no posts":
                        async with self.config.custom(
                            "metadata", ctx.guild.id
                        ).no_posts() as no_posts:
                            if char_id not in no_posts:
                                no_posts.append(char_id)
                        one_more = False
                    else:
                        more_characters = True
                        one_more = False
                        async with self.config.custom(
                            "metadata", ctx.guild.id
                        ).character_profiles() as profile_dict:
                            profile_dict.update({char_id: char.embed.to_dict()})
                            display_name = char.display_name
                            print(f"Character: {display_name} saved.")
                            if display_name.lower() == character.lower():
                                return
                char_id += 1
                if timed:
                    timeout -= 1
                    if timeout <= 0:
                        more_characters = False

    async def _character_exists(self, ctx, character):
        """Checks the config to see if the character exists already."""
        char_list = await self.config.custom(
            "metadata", ctx.guild.id
        ).character_profiles()
        return str(character) in char_list.keys()

    async def _get_character_id_by_display_name(self, ctx, display_name):
        """Takes a character id and returns the display name if that character exists"""
        async with self.config.custom(
            "metadata", ctx.guild.id
        ).character_profiles() as char_list:
            for key, char in char_list.items():
                if char:
                    if (
                        char is not None
                        and char["author"]["name"].lower() == display_name.lower()
                    ):
                        return key

    async def get_discord_id_by_character_id(self, ctx, char_num):
        """Takes a character id and returns the discord id of the user who claimed it."""
        users = await self.profiles.data.all_users()
        results = []
        for user, data in users.items():
            for id in data["characters"]:
                if str(id) == str(char_num):
                    name = await ctx.bot.get_or_fetch_user(user)
                    results.append(str(name))
        return results[0] if len(results) else "Unknown"
