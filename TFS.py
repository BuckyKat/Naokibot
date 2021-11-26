import aiohttp
import asyncio
import discord
import re
from bs4 import BeautifulSoup
from redbot.core import commands, config, utils
from redbot.core.commands import Context
from typing import Any
from redbot.core import Config
import datetime
from babel.dates import format_timedelta

# CONSTANTS
factions = {
    "isra": 0x650D1B,
    "aozora": 0x60BAF3,
    "tawakoshi": 0x006442,
    "helmfirth": 0x670001,
    "dongshu": 0x010451,
    "tir la morr": 0x51607A,
    "black vale": 0x181816,
    "skaldur": 0x263955,
    "taingaard": 0xF0E37E,
    "audria": 0x2A2116,
    "velmerys": 0xA80000,
    "aridia": 0x9F8200,
    "naimon": 0x65458F,
    "vallon": 0xF11D08,
    "winterland": 0x7B8EB2,
    "tiller": 0x108042,
    "voruta": 0x5F0D1B,
    "fletcher": 0xFFFFFF,
    "edan": 0x38771C,
    "thios": 0xE4BA12,
    "toragana": 0x003471,
    "airli": 0x19477E,
    "tamorjin": 0xFFA280,
    "correa": 0xbb0a1e,
    "usque": 0xd794db,
}


# HELPER FUNCTIONS
async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


def _name(self, user, max_length):
    if user.name == user.display_name:
        return user.name
    else:
        return "{} ({})".format(user.name, self._truncate_text(user.display_name, max_length - len(user.name) - 3),
                                max_length)


def _remove(duplicate):
    final_list = []
    for num in duplicate:
        if num not in final_list:
            final_list.append(num)
    return final_list


def truncate(the_string: str, the_length: int = 500):
    if len(the_string) < the_length:
        return the_string
    else:
        return the_string[0:the_length] + "..."


def active_fancy(the_bool: bool):
    if the_bool:
        return "Active"
    else:
        return "Inactive"


# CHARACTER CLASS
class Character:
    def __init__(self, profile, soup, number):
        self.profile = profile
        self.soup = soup
        self.number = number

    @classmethod
    async def from_num(self, num):
        recent_url = "http://themistborneisles.boards.net/user/" + \
                     str(num) + "/recent"
        async with aiohttp.ClientSession() as session:
            html = await fetch(session, recent_url)
            soup_object = BeautifulSoup(html, "html.parser")
        _profile = soup_object.find(class_="mini-profile")
        if _profile:
            return Character(_profile, soup_object, num)

    @property
    def embed(self):
        em = discord.Embed(title=self.username +
                                 " (" + str(self.number) + ")", url=self.profile_url, description=("Last post: " + self.last_post_time_fancy + " in " + self.last_post_markdown))
        em.set_thumbnail(url=self.avatar)
        em.set_author(name=self.display_name, icon_url=self.gender_symbol)
        em.add_field(name="Post Count:", value=self.posts, inline=True)
        em.add_field(name="Register Date:",
                     value=self.register_date, inline=True)
        if self.age != "Not set":
            em.add_field(name="Age:", value=self.age, inline=True)
        if self.appearance != "Not set":
            em.add_field(name="Appearance:", value=truncate(
                self.appearance), inline=False)
        if self.equipment != "Not set":
            em.add_field(name="Equipment:", value=truncate(
                self.equipment), inline=False)
        if self.skills_and_abilities != "Not set":
            em.add_field(name="Skills and abilities:", value=truncate(
                self.skills_and_abilities), inline=False)
        if self.biography != "Not set":
            em.add_field(name="Biography:", value=truncate(
                self.biography), inline=False)
        footer = self.rank + "  |  " + \
                 active_fancy(self.active)
        em.set_footer(text=footer, icon_url=self.star)
        em.color = self.color
        return em

    @property
    def display_name(self):
        return str(self.profile.a.contents[0])

    @property
    def avatar(self):
        avatar_url = str(self.profile.div.img).split('"')[3]
        if avatar_url[0] == "/":
            return "https:" + avatar_url
        else:
            return avatar_url

    @property
    def username(self):
        return "@" + (str(self.profile.a).split("@")[1]).split('"')[0]

    @property
    def posts(self):
        posts = self.profile.find(class_="info").contents[0].split(" ")[2]
        return re.sub("[^0-9]+", "", posts)

    @property
    def color(self):
        for key, val in factions.items():
            if re.search(key, self.allegiance, re.IGNORECASE) is not None:
                return val
        return 0x36393F

    @property
    def last_post_thread(self):
        _soup = self.soup
        thread_class = _soup.find(class_="js-thread__title-link")
        return str(thread_class.contents[0])

    @property
    def last_post_id(self):
        _soup = self.soup
        button_class = _soup.find(class_="quote-button")
        return str(button_class['href']).split("/")[2]

    @property
    def last_post_link(self):
        _soup = self.soup
        thread_class = _soup.find(class_="thread-link")
        post_id = self.last_post_id
        output = "http://themistborneisles.boards.net" + \
                 thread_class['href'] + "?page=9001&scrollTo=" + post_id
        return str(output)

    @property
    def last_post_time(self):
        _soup = self.soup
        date_class = _soup.find(class_="date")
        if date_class is None:
            return None
        else:
            unix_time = str(date_class.contents).split('"')[3]
            unix_time = float(unix_time[:(len(unix_time) - 3)])

            date_object = datetime.datetime.fromtimestamp(unix_time)
            return date_object

    @property
    def last_post_time_fancy(self):
        time_stamp = self.last_post_time
        if time_stamp:
            now = datetime.datetime.now()
            time_diff = time_stamp - now
            return format_timedelta(time_diff, locale='en_US') + " ago"
        else:
            return "Never"

    @property
    def last_post_markdown(self):
        return str("[" + self.last_post_thread + "](" + self.last_post_link + ')')

    @property
    def profile_url(self):
        return "http://themistborneisles.boards.net/user/" + \
               str(self.number)

    @property
    def active(self):
        last_post = self.last_post_time
        if last_post is None:
            return False
        else:
            now = datetime.datetime.now()
            time_diff = last_post - now
            active_time = datetime.timedelta(days=-30)
            if (time_diff < active_time) is False:
                return True
            else:
                return False

    @property
    def register_date(self):
        register_date = self.profile.find(class_="o-timestamp time").string
        register_constructor = register_date.split(" ")
        return register_constructor[0] + " " + register_constructor[1] + " " + register_constructor[2]

    @property
    def rank(self):
        stripped_strings = []
        for child in self.profile.stripped_strings:
            stripped_strings.append(child)
        return stripped_strings[1]

    @property
    def star(self):
        return "https:/" + str(self.profile.contents[6]).partition("/")[2].rstrip('"/>')

    @property
    def gender(self):
        try:
            gender = self.profile.find(class_="info").img.attrs['title']
            return str(gender)
        except AttributeError:
            return "None"

    @property
    def gender_symbol(self):
        if self.gender == "Male":
            return "https://i.imgur.com/G0j21CT.png"
        elif self.gender == "Female":
            return "https://i.imgur.com/hDXZ9ES.png"
        else:
            return "https://i.imgur.com/dbHOlQf.png"

    @property
    def allegiance(self):
        return self.custom_field("allegiances")

    @property
    def age(self):
        return self.custom_field("age")

    @property
    def appearance(self):
        return self.custom_field("appearance")

    @property
    def equipment(self):
        return self.custom_field("equipment")

    @property
    def skills_and_abilities(self):
        return self.custom_field("skillsandabilities")

    @property
    def biography(self):
        return self.custom_field("biography")

    # TODO: fix this mess
    def custom_field(self, attribute):
        _profile = self.profile
        class_name = "custom-field-" + attribute
        attribute_list = []
        if _profile.find(class_=class_name) is None:
            return "Not set"
        else:
            for string in _profile.find(class_=class_name).stripped_strings:
                if re.search('[a-zA-Z0-9]', string) is not None:
                    attribute_list.append(repr(string).strip("'"))
            # attribute_name = attribute_list[0].partition(":")[0]
            attribute_content = attribute_list[0].partition(":")[2]
            if re.search('[a-zA-Z0-9]', attribute_content) is None:
                attribute_content = attribute_list.pop(1)
            attribute_continued = "\n".join(attribute_list[1:])
            return str(attribute_content + "\n" + attribute_continued + "\n")


class UserProfile:

    def __init__(self):
        self.data = Config.get_conf(self, identifier=867530999999)
        default_user = {
            "posts": 0,
            "main": None,
            "main_name": "",
            "characters": [],
            "registered": None,
            "last_post": None,
            "active": False,
            "updated": datetime.datetime.now(),
            "display_names": [],
        }

        self.data.register_user(**default_user)

    async def add_character(self, user, number: int):
        async with self.data.user(user).characters() as char_list:
            char_list.append(number)

    async def remove_character(self, user, number: int):
        async with self.data.user(user).characters() as char_list:
            try:
                char_list.remove(number)
            except ValueError:
                return

    async def sort_characters(self, user):
        async with self.data.user(user).characters() as char_list:
            char_list = [int(x) for x in char_list]
            char_list = _remove(char_list)
            char_list.sort()
            await self.data.user(user).characters.set(char_list)

    async def get_characters(self, user):
        return await self.data.user(user).characters()

    async def get_displaynames(self, user):
        return await self.data.user(user).display_names()

    async def get_main(self, user):
        return await self.data.user(user).main()

    async def get_posts(self, user):
        return await self.data.user(user).posts()

    async def get_active(self, user):
        return await self.data.user(user).active()

    async def get_updated(self, user):
        return await self.data.user(user).updated()

    async def register_user(self, user):
        data = await self.data.user(user).database()
        if data is None:
            await self.data.user(user).database.set([])
            await self.data.user(user).characters.set([])

    async def update_active(self, user):
        async with self.data.user(user).characters() as char_list:
            for num in char_list:
                this_character = await Character.from_num(num)
                if this_character:
                    active = this_character.active
                    if active:
                        await self.data.user(user).active.set(True)
                        break
                    else:
                        continue
                else:
                    continue
        return True

    async def update_names(self, user):
        name_list = []
        async with self.data.user(user).characters() as char_list:
            for num in char_list:
                this_character = await Character.from_num(num)
                if this_character:
                    name = this_character.display_name
                    name_list.append(name)
            await self.data.user(user).display_names.set(name_list)
        return True

    async def update_posts(self, user):
        post_count = 0
        async with self.data.user(user).characters() as char_list:
            for num in char_list:
                this_character = await Character.from_num(num)
                if this_character:
                    posts = this_character.posts
                    post_count += int(posts)
            await self.data.user(user).posts.set(post_count)
        return True


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
            now = datetime.datetime.now()
            time_diff = timest - now
            fancy_time = format_timedelta(time_diff, locale='en_US') + " ago"
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
    async def show(self, ctx, number):
        """Shows a profile embed for the given character"""
        this_character = await Character.from_num(number)
        async with ctx.typing():
            em = this_character.embed
            await ctx.send(embed=em)

    @commands.command()
    async def claim(self, ctx, *, arg):
        """Adds a list of characters to your user"""
        numbers = list(filter(None, re.sub("[^0-9]+", ",", arg).split(",")))
        await self.profiles.sort_characters(ctx.author)
        for num in numbers:
            await self.profiles.add_character(ctx.author, int(num))
        async with ctx.typing():
            await self.profiles.sort_characters(ctx.author)
            characters = await self.profiles.get_characters(ctx.author)
            await self.profiles.update_names(ctx.author)
            name_list = await self.profiles.get_displaynames(ctx.author)
        await ctx.send(":white_check_mark: Success. There are now " + str(
            len(characters)) + " characters registered to you: " + self._list_to_str(name_list))
        if len(characters) > len(name_list):
            await ctx.send(
                ":warning: At least one of your characters hasn't made any posts yet, which means that I can't see "
                "them. For any characters whose names aren't listed, post with them in any thread and then do the "
                "command `!update`.")
        else:
            await ctx.send("Use the command `!update` to update your profile.")

    @commands.command()
    async def unclaim(self, ctx, *, arg):
        """Removes a list of characters from your user"""
        numbers = list(filter(None, re.sub("[^0-9]+", ",", arg).split(",")))
        await self.profiles.sort_characters(ctx.author)
        for num in numbers:
            try:
                await self.profiles.remove_character(ctx.author, int(num))
                await ctx.send(":white_check_mark: Success. Character #" + num + " has been removed from your profile.")
            except ValueError:
                await ctx.send(
                    "Error: character # " + num + " cannot be unclaimed because they were not claimed to begin with.")
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
        em.set_thumbnail(url=user.avatar_url)
        em.set_author(name=user.name)

        em.add_field(name="Post Count:", value=posts, inline=True)
        em.add_field(name="Register Date:", value=user.created_at, inline=True)
        if characters:
            em.add_field(name="Character Numbers:",
                         value=self._list_to_str(characters), inline=False)
        if names:
            em.add_field(name="Characters:", value=self._list_to_str(names), inline=False)
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
        elif (active):
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
        await ctx.send("I'm going to try to update information for every user in the server. Hold on to your hat.")
        for member in members:
            await ctx.invoke(self.update, user=member)
        await ctx.send("I've finished updating information for all users. _Wew._")

    @commands.command()
    async def howtoclaimmany(self, ctx):
        """Gives information on how to claim many characters at once"""
        await ctx.send('Go to this link: https://www.proboards.com/account/forum (You have to be logged in.)'
                       + '\n > Right click, View Source\n> Ctrl+F: “forum_user_ids”\n> Copy the numbers in brackets '
                         'right next to that. '
                       + " (If you're on multiple proboards forums, make sure you're copying from the TMI section!)"
                       + '\n > It should look something like this: `["607","1186","1310","813"]`'
                       + "\n In #bot_stuff, use the command `!claim [paste your numbers]` Then you're done! Do this "
                         "for all your characters to keep your `!profile` up to date!")

    @commands.command()
    async def howtoclaim(self, ctx):
        """Gives information on how to claim characters"""
        await ctx.send("Visit your character's page by clicking on their name or clicking on 'CHARACTER' at the top "
                       "between 'HOME' and 'MESSAGING' "
                       + '\nLook at the URL for that page, and paste the number from the end of that URL as an '
                         'argument for the `!claim` command! '
                       + '\nYou can put in multiple numbers separated by commas to claim multiple characters at once, '
                         'and if you make a mistake, you can use the `!unclaim` command to remove characters.')

    async def _search_users_by_display_name(self, search_name, ctx, users):
        results = []
        for user, data in users.items():
            for display_name in data['display_names']:
                if display_name.lower() == search_name:
                    name = await ctx.bot.get_or_fetch_user(user)
                    results.append(str(name))
        return results

    async def _search_users_by_character_id(self, search_id, ctx, users):
        results = []
        for user, data in users.items():
            for id in data['characters']:
                print( id, search_id)
                if str(id) == str(search_id):
                    name = await ctx.bot.get_or_fetch_user(user)
                    results.append(str(name))
        return results

    @commands.command()
    async def find(self, ctx: Context, *, args):
        results = []

        users = await self.profiles.data.all_users()
        if args.split(' ')[0].isdigit():
            search = args.split(' ')
            for id in search:
                results += await self._search_users_by_character_id(id, ctx, users)
            search = ', '.join(search)
        else:
            search = args.lower()
            results = await self._search_users_by_display_name(search, ctx, users)
            
        if len(results) > 0:
            return_users = ', '.join(results)
            await ctx.send(f'The following users had the name {search} claimed: {return_users}')
        else:
            await ctx.send(f"No users with character name {search}.")

    def _list_to_str(self, list_to_convert: list) -> str:
        ret = ''
        for s in list_to_convert:
            ret += f'{s}, '
        
        ret.strip()
        return ret[:-2]

