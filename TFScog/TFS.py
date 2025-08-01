import arrow
import re
from typing import Any

import discord
from babel.dates import format_timedelta
from redbot.core import Config, commands
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import box, pagify

from .character import Character
from .user_profile import UserProfile


# HELPER FUNCTIONS
def _name(self, user, max_length):
    if user.name == user.display_name:
        return user.name
    else:
        return "{} ({})".format(
            user.name,
            self._truncate_text(user.display_name, max_length - len(user.name) - 3),
            max_length,
        )


def active_fancy(the_bool: bool):
    if the_bool:
        return "Active"
    else:
        return "Inactive"


class TFS(commands.Cog):
    """TFS related utilities"""

    def __init__(self):
        self.config = Config.get_conf(self, identifier=867530999999)
        self.profiles = UserProfile()

    @commands.command()
    async def name(self, ctx, number):
        """Returns a character's name"""
        this_character = await Character.from_num(number)
        name = this_character.display_name
        await ctx.send("Name: " + name)

    @commands.command()
    async def pic(self, ctx, number):
        """Returns a character's avatar"""
        this_character = await Character.from_num(number)
        url = this_character.avatar
        await ctx.send(url)

    @commands.command()
    async def username(self, ctx, number):
        """Returns a character's username"""
        this_character = await Character.from_num(number)
        username = this_character.username
        await ctx.send(username)

    @commands.command()
    async def posts(self, ctx, number):
        """Returns a character's posts"""
        this_character = await Character.from_num(number)
        posts = this_character.posts
        await ctx.send(posts)

    @commands.command()
    async def custom(self, ctx, attribute, number):
        """Returns a custom attribute for a character"""
        this_character = await Character.from_num(number)
        content = this_character.custom_field(attribute)
        if content is None:
            await ctx.send("None!")
        else:
            await ctx.send(content)

    @commands.command()
    async def lastpost(self, ctx, number):
        """Returns the date of a character's last post"""
        this_character = await Character.from_num(number)
        timest = this_character.last_post_time
        await ctx.send(str(timest))
        if timest:
            now = arrow.utcnow()
            # Parse timest to Arrow if needed:
            if not isinstance(timest, arrow.Arrow):
                timest = arrow.get(timest)
            time_diff = now - timest  # arrow durations are timedelta compatible
            fancy_time = format_timedelta(time_diff, locale="en_US") + " ago"
            await ctx.send(fancy_time)
        await ctx.send(this_character.last_post_id)
        await ctx.send(this_character.last_post_thread)
        await ctx.send(this_character.last_post_link)

    @commands.command()
    async def register_date(self, ctx, number):
        """Returns the date a given character was created on"""
        this_character = await Character.from_num(number)
        date = this_character.register_date
        await ctx.send(date)

    @commands.command()
    async def gender(self, ctx, number):
        """Returns a character's listed gender"""
        this_character = await Character.from_num(number)
        gender = this_character.gender
        await ctx.send(gender)

    @commands.command()
    async def show(self, ctx, *, args):
        """Shows a profile embed for the given character"""
        users = await self.profiles.data.all_users()

        if not args.split(" ")[0].isdigit():
            name = await self._search_users_by_display_name(args.lower(), ctx, users)
            name = self._list_to_str(name)
            number = self._find_character_number_by_name(args.lower(), users)
        else:
            number = args
            name = await self._search_users_by_character_id(number, ctx, users)
            name = self._list_to_str(name)
        try:
            this_character = await Character.from_num(number, name)
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
            return
        async with ctx.typing():
            em = this_character.embed
            await ctx.send(embed=em)

    @commands.command()
    async def claim(self, ctx, *, arg):
        """Adds a list of characters to your user"""
        numbers = list(filter(None, re.sub("[^0-9]+", ",", arg).split(",")))
        await self.profiles.sort_characters(ctx.author)
        failed = []
        for num in numbers:
            try:
                await self.profiles.add_character(ctx.author, int(num))
            except ValueError as e:
                failed.append(f"{num} ({str(e)})")
        async with ctx.typing():
            await self.profiles.sort_characters(ctx.author)
            characters = await self.profiles.get_characters(ctx.author)
            await self.profiles.update_names(ctx.author)
            name_list = await self.profiles.get_displaynames(ctx.author)

        await ctx.send(
            ":white_check_mark: Success. There are now "
            + str(len(characters))
            + " characters registered to you: "
            + self._list_to_str(name_list)
        )
        if failed:
            await ctx.send(
                ":warning: Some characters couldn't be claimed:\n" + "\n".join(failed)
            )
        if len(characters) > len(name_list):
            await ctx.send(
                ":warning: At least one of your characters hasn't made any posts yet, which means that I can't see "
                "them. For any characters whose names aren't listed, post with them in any thread and then do the "
                "command "
                + f"`{ctx.prefix}update`."
            )
        else:
            await ctx.send(f"Use the command `{ctx.prefix}update` to update your profile.")


    @commands.command()
    async def unclaim(self, ctx, *, arg):
        """Removes a list of characters from your user"""
        numbers = list(filter(None, re.sub("[^0-9]+", ",", arg).split(",")))
        await self.profiles.sort_characters(ctx.author)
        for num in numbers:
            try:
                await self.profiles.remove_character(ctx.author, int(num))
                await ctx.send(
                    ":white_check_mark: Success. Character #"
                    + num
                    + " has been removed from your profile."
                )
            except ValueError:
                await ctx.send(
                    "Error: character # "
                    + num
                    + " cannot be unclaimed because they were not claimed to begin with."
                )
                continue
        await self.profiles.sort_characters(ctx.author)

    @commands.command()
    async def profile(self, ctx, *, user: discord.Member = None):
        """Displays a given user's profile, defaults to you"""
        if user is None:
            user = ctx.message.author

        characters = await self.profiles.get_characters(user)
        names = await self.profiles.get_displaynames(user)
        main = await self.profiles.get_main(user)
        posts = await self.profiles.get_posts(user)
        active = await self.profiles.get_active(user)

        em = discord.Embed(title=user.nick)
        em.set_thumbnail(url=user.display_avatar.url)
        em.set_author(name=user.name)

        em.add_field(name="Post Count:", value=posts, inline=True)
        em.add_field(name="Register Date:", value=user.created_at, inline=True)
        if characters:
            em.add_field(
                name="Character Numbers:",
                value=self._list_to_str(characters),
                inline=False,
            )
        if names:
            em.add_field(
                name="Characters:", value=self._list_to_str(names), inline=False
            )
        if main:
            em.add_field(name="Main:", value=main, inline=False)

        footer = str(user.top_role) + "  |  " + active_fancy(active)
        em.set_footer(text=footer)
        em.color = user.color

        await ctx.send(embed=em)

    @commands.command()
    async def update(self, ctx, *, user: discord.Member = None):
        """Updates a given user's profile, defaults to you"""
        if user is None:
            user = ctx.message.author
        if user.bot:
            await ctx.send(user.name + " is a bot, so I won't update them. :robot:")
            return
        async with ctx.typing():
            await self.profiles.update_names(user)
            await ctx.send("Display names updated for " + user.name + ".")
        async with ctx.typing():
            await self.profiles.update_posts(user)
            await ctx.send("Post count updated for " + user.name + ".")
        async with ctx.typing():
            await self.profiles.update_active(user)
            await ctx.send("Active status updated for " + user.name + ".")

        members = discord.utils.get(ctx.guild.roles, name="Member")
        inactive = discord.utils.get(ctx.guild.roles, name="Member (Inactive)")
        guests = discord.utils.get(ctx.guild.roles, name="Guest")
        active = await self.profiles.get_active(user)
        characters = await self.profiles.get_characters(user)
        if len(characters) == 0:
            await user.remove_roles(inactive, members)
            await user.add_roles(guests)
            await ctx.send("Updated role to Guest for " + user.name + ".")
        elif active:
            await user.remove_roles(inactive, guests)
            await user.add_roles(members)
            await ctx.send("Updated role to Member for " + user.name + ".")
        else:
            await user.remove_roles(members, guests)
            await user.add_roles(inactive)
            await ctx.send("Updated role to Member (Inactive) for " + user.name + ".")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.command()
    async def update_all(self, ctx):
        server = ctx.message.guild
        members = server.members
        await ctx.send(
            "I'm going to try to update information for every user in the server. Hold on to your hat."
        )
        for member in members:
            await ctx.invoke(self.update, user=member)
        await ctx.send("I've finished updating information for all users. _Wew._")

    @commands.command()
    async def howtoclaimmany(self, ctx):
        """Gives information on how to claim many characters at once"""
        await ctx.send(
            "Go to this link: https://www.proboards.com/account/forum (You have to be logged in.)"
            + "\n > Right click, View Source\n> Ctrl+F: “forum_user_ids”\n> Copy the numbers in brackets "
            "right next to that. "
            + " (If you're on multiple proboards forums, make sure you're copying from the TMI section!)"
            + '\n > It should look something like this: `["607","1186","1310","813"]`'
            + f"\n In #bot_stuff, use the command `{ctx.prefix}claim [paste your numbers]` Then you're done! Do this "
            + f"for all your characters to keep your `{ctx.prefix}profile` up to date!"
        )



    @commands.command()
    async def howtoclaim(self, ctx):
        """Gives information on how to claim characters"""
        await ctx.send(
            "Visit your character's page by clicking on their name or clicking on 'CHARACTER' at the top "
            "between 'HOME' and 'MESSAGING' "
            + f"\nLook at the URL for that page, and paste the number from the end of that URL as an "
            + f"argument for the `{ctx.prefix}claim` command! "
            + f"\nYou can put in multiple numbers separated by commas to claim multiple characters at once, "
            + f"and if you make a mistake, you can use the `{ctx.prefix}unclaim` command to remove characters."
        )


    @commands.command(aliases=['pl'])
    async def postleaderboard(self, ctx, top: int = 10):
        """Prints out the posts leaderboard.
        Defaults to top 10. Use negative numbers to reverse the leaderboard.
        """
        reverse = True
        if top == 0:
            top = 10
        elif top < 0:
            reverse = False
            top = -top
        server = ctx.message.guild
        members = server.members
        member_post_dict = {}
        for member in members:
            posts = await self.profiles.get_posts(member)
            member_post_dict[member.name] = posts
        members_sorted = sorted(
            member_post_dict, key=member_post_dict.__getitem__, reverse=reverse
        )

        if len(members_sorted) < top:
            top = len(members_sorted)
        topten = members_sorted[:top]
        highscore = ""
        place = 1
        for member in topten:
            highscore += str(place).ljust(len(str(top)) + 1)
            highscore += "{} | ".format(member).ljust(18 - len(str(member_post_dict[member])))
            highscore += str(member_post_dict[member]) + "\n"
            place += 1
        if highscore != "":
            for page in pagify(highscore, shorten_by=12):
                await ctx.send(box(page, lang="py"))
        else:
            await ctx.send("No one has any posts 🙁")

    async def _search_users_by_display_name(self, search_name, ctx, users):
        results = []
        for user, data in users.items():
            for display_name in data["display_names"]:
                if display_name.lower() == search_name:
                    name = await ctx.bot.get_or_fetch_user(user)
                    results.append(str(name))
        return results

    async def _search_users_by_character_id(self, search_id, ctx, users):
        results = []
        for user, data in users.items():
            for id in data["characters"]:
                if str(id) == str(search_id):
                    name = await ctx.bot.get_or_fetch_user(user)
                    results.append(str(name))
        return results

    def _list_to_str(self, list_to_convert: list) -> str:
        ret = ""
        for s in list_to_convert:
            ret += f"{s}, "

        ret.strip()
        return ret[:-2]

    def _find_character_number_by_name(self, name, users):
        for user, data in users.items():
            position = 0
            for display_name in data["display_names"]:
                if display_name.lower() == name.lower():
                    return data["characters"][position]
                position += 1
        return None