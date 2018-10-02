import discord
from discord.ext import commands
from discord.utils import find
from .utils.chat_formatting import pagify
from .utils import checks
from __main__ import send_cmd_help
from babel.dates import format_timedelta
import platform
import asyncio
import string
import operator
import os
import re
import aiohttp
import json
import logging

from .utils.dataIO import fileIO

try:
    import pymongo
    from pymongo import MongoClient
except:
    raise RuntimeError("Can't load pymongo. Do 'pip3 install pymongo'.")

import datetime

try:
    from bs4 import BeautifulSoup
    soupAvailable = True
except:
    soupAvailable = False

log = logging.getLogger('red.buckycog')
user_directory = "data/buckycog/users"

try:
    client = MongoClient()
    db = client['buckycog']
except:
    print("Can't load database. Follow instructions on Git/online to install MongoDB.")

attributes = ["age", "physicaldescription", "clothesandequipment",
              "skillsandabilities", "personalityother", "allegiances"]

factions = {
    "isra": 0x650D1B,
    "aozora": 0x60BAF3,
    "tawakoshi": 0xFE0000,
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
}


def Remove(duplicate):
    final_list = []
    for num in duplicate:
        if num not in final_list:
            final_list.append(num)
    return final_list

#--------------------Embed functions--------------------


async def characterEmbed(server, ctx, characterNumber: str):
    soupObject = await GETrecentfromNumber(characterNumber)
    profile = soupObject.find(class_="mini-profile")

    if profile is None:
        return("It seems like that character doesn't exist, has been deleted, or hasn't made any posts.\nWhatever the case may be, I can't find their profile. ¯\\_(ツ)_/¯")
    else:
        stripped_strings = []
        profileURL = "http://thefantasysandbox.boards.net/user/" + \
            str(characterNumber)
        owner = await searchOwner(characterNumber, server)

        for child in profile.stripped_strings:
            stripped_strings.append(child)

        em = discord.Embed(title=GETusername(profile) + " (" + str(characterNumber) + ")",
                           description=CONSTRUCTinfo(profile), colour=GETcolor(profile), url=profileURL)
        em.set_author(name=GETdisplayName(profile),
                      icon_url=GETgenderSymbol(profile))
        em.set_thumbnail(url=GETavatar(profile))
        em.add_field(name="Post Count:", value=GETposts(profile))
        em.add_field(name="Registered On:",
                     value=GETregisterDate(profile))
        em.set_footer(text=GETrank(stripped_strings),
                      icon_url=GETstar(profile))
        if owner is not None:
            em.add_field(name="Owner:",
                         value=owner)
        return em


async def characterPostsEmbed(user, userinfo, profiles_list):
    namesBody = []
    displayNames = []
    postsBody = []
    total = 0
    output = "error lol"
    for profile in profiles_list:
        namesBody.append(GETdisplayName(profile))
        posts = (GETposts(profile))
        postsBody.append(posts)

    for posts in postsBody:
        total += (float(re.sub("[^0-9]+", "", (posts))))

    postsBody = ' '.join(postsBody).split()

    postsBody.append("__**" + str(int(total)) + "**__")
    namesBody.append("__**Total:**__")

    namesBody = "\n".join(namesBody)
    postsBody = "\n".join(postsBody)

    em = discord.Embed(description=str(
        ', '.join(displayNames)), colour=user.colour)
    em.add_field(name="Characters:", value=namesBody)
    em.add_field(name="Posts:", value=postsBody)
    em.set_author(name="Posts Overview for {}".format(
        user.name), url=user.avatar_url)
    em.set_thumbnail(url=user.avatar_url)

    return em


async def lastPostsEmbed(user, userinfo, profiles_list):
    namesBody = []
    displayNames = []
    lastPostsBody = []
    total = 0
    output = "error lol"
    for characterNumber in userinfo["registered_characters"]:
        #   threadLink = await GETlastpostThreadLink(characterNumber)
        dateObject = await GETlastpostTime(characterNumber)
        if dateObject == "Never":
            lastPostsBody.append(dateObject)
        else:
            formattedTime = dateObject.strftime(
                "%a, %b, %d, %Y at %I:%M %p")
            now = datetime.datetime.now()
            timeDiff = dateObject - now
            fancyTime = format_timedelta(timeDiff, locale='en_US') + " ago"
            lastPostsBody.append(fancyTime)

    for profile in profiles_list:
        namesBody.append(GETdisplayName(profile))

    namesBody = "\n".join(namesBody)
    lastPostsBody = "\n".join(lastPostsBody)

    em = discord.Embed(description=str(
        ', '.join(displayNames)), colour=user.colour)
    em.add_field(name="Characters:", value=namesBody)
    em.add_field(name="Last Post:", value=lastPostsBody)
    em.set_author(name="Last Posts Overview for {}".format(
        user.name), url=user.avatar_url)
    em.set_thumbnail(url=user.avatar_url)

    return em


async def attributeEmbed(user, userinfo, profiles_list, attribute):
    attributeList = []
    namesList = []

    for profile in profiles_list:
        namesList.append(GETdisplayName(profile))
        attributeString = await GETattributeForProfile(profile, attribute)
        attributeList.append(attributeString)

    attributeList = ' '.join(attributeList).split()

    namesBody = "\n".join(namesList)
    attributeBody = "\n".join(attributeList)

    em = discord.Embed(description="", colour=user.colour)
    em.add_field(name="Character:", value=namesBody)
    em.add_field(name="attribute:", value=attributeBody)
    em.set_author(name=str(attribute) + " Overview for {}".format(
        user.name), url=user.avatar_url)
    em.set_thumbnail(url=user.avatar_url)

    output = em

    return output


async def profileEmbed(user, userinfo):
    def test_empty(text):
        if text == '':
            return "None"
        else:
            return text
    avatarURL = user.avatar_url
    isActive = userinfo["active"]
    role = userinfo["role"]
    total_posts = userinfo["total_posts"]
    displayNames = userinfo["character_names"]

    em = discord.Embed(description=str(
        ', '.join(displayNames)), colour=user.colour)
    em.add_field(name="Characters:", value=len(
        userinfo["registered_characters"]))
    em.add_field(name="Total Posts:", value=total_posts)
    em.add_field(name="Active:", value=isActive)
    em.add_field(name="Role:", value=role)
    em.set_author(name="Profile for {}".format(user.name), url=avatarURL)
    em.set_thumbnail(url=avatarURL)
    return em


class buckycog:
    """TFS utilities"""

    def __init__(self, bot):
        self.bot = bot

        dbs = client.database_names()
        if 'buckycog' not in dbs:
            self.pop_database()

    def pop_database(self):
        if os.path.exists(user_directory):
            for userid in os.listdir(user_directory):
                userinfo = fileIO(
                    "data/buckycog/users/{}/info.json".format(userid), "load")
                userinfo['user_id'] = userid
                db.users.insert_one(userinfo)

    def create_global(self):

        userinfo = fileIO(
            "data/buckycog/users/{}/info.json".format(userid), "load")
        userinfo['user_id'] = userid
        db.users.insert_one(userinfo)

    @commands.group(pass_context=True, name='tfs', case_insensitive=True)
    async def buckycog(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @buckycog.command(name='update_all', pass_context=True, no_pm=True)
    async def update_all(self, ctx):
        """Updates every user on the server"""
        server = ctx.message.server
        members = server.members
        await self.bot.say("I'm going to try to update information for every user in the server. Hold on to your hat.")
        for member in members:
            await update(self, ctx, member)
        await self.bot.say("I've finished updating information for all users. _Wew._")

    @buckycog.command(name='update', pass_context=True, no_pm=True)
    async def update(self, ctx, *, user: discord.Member=None):
        """Updates database information and role for a given user"""
        if user is None:
            user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        await self.bot.say("Updating information for " + user.name + ".\nThis might take a while.")
        await self.bot.send_typing(ctx.message.channel)
        if "character_names" not in userinfo:
            db.users.update_one({'user_id': user.id}, {'$set': {
                "character_names": await GETdisplayNamesforUser(user),
            }}, upsert=True)
        await updateRole(user)
        await GETtotalPostsforUser(user)
        await GETdisplayNamesforUser(user)
        server = ctx.message.server
        await setRole(self, user, server)
        await self.bot.say("Finished updating information for " + user.name + ". Check with `n!tfs profile`")

    async def _create_user(self, user):
        try:
            userinfo = db.users.find_one({'user_id': user.id})
            if not userinfo:
                new_account = {
                    "user_id": user.id,
                    "username": user.name,
                    "registered_characters": "",
                    "character_names": [],
                    "total_posts": 0,
                    "role": "Guests",
                    "active": False,
                }
                db.users.insert_one(new_account)

            userinfo = db.users.find_one({'user_id': user.id})

            if "username" not in userinfo or userinfo["username"] != user.name:
                db.users.update_one({'user_id': user.id}, {'$set': {
                    "username": user.name,
                }}, upsert=True)
        except AttributeError as e:
            pass

    @commands.group(pass_context=True, name='character', aliases=["char"], case_insensitive=True)
    async def character(self, ctx):
        try:
            characterNumber = int(ctx.subcommand_passed)
            server = ctx.message.server
            channel = ctx.message.channel
            em = await characterEmbed(server, ctx, characterNumber)
            await self.bot.send_message(channel, "", embed=em)
        except:
            if ctx.invoked_subcommand is None:
                await self.bot.send_cmd_help(ctx)

    @character.command(name='lastpost', aliases=["lp"])
    async def lastpost(self, ctx):
        """Fetches and displays a given character's last post"""
        characterNumber = ctx
        dateObject = await GETlastpostTime(characterNumber)
        profile = await GETprofileforNumber(characterNumber)
        name = GETdisplayName(profile)
        thread = await GETlastpostThread(characterNumber)
        threadLink = await GETlastpostThreadLink(characterNumber)
        postContent = await GETlastpostContent(characterNumber)
        formattedTime = dateObject.strftime("%a, %b, %d, %Y at %I:%M %p")
        now = datetime.datetime.now()
        timeDiff = dateObject - now
        fancyTime = format_timedelta(timeDiff, locale='en_US')
        em = discord.Embed(title="in " + thread, description=postContent,
                           colour=GETcolor(profile), url=threadLink)
        em.set_author(name=name + "'s last post was " + fancyTime + " ago",
                      icon_url=GETavatar(profile))
        em.set_footer(text=formattedTime)

        await self.bot.say(embed=em)

    @character.command(name="claim", pass_context=True, no_pm=True)
    async def claim(self, ctx, *, arg):
        """Adds a character to user's registered users"""

        user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        numbers = list(filter(None, re.sub("[^0-9]+", ",", (arg)).split(",")))
        characters = userinfo["registered_characters"]
        new = Remove(characters + numbers)
        new.sort()

        db.users.update_one({'user_id': user.id}, {'$set': {
            "registered_characters": new,
        }})
        await self.bot.say("Success. " + ('There are now {} characters registered to you. {}\n Use `n!tfs update` to update your profile.'.format(len(new), ', '.join(new))))

    #@character.command(name='assign', aliases=["lp"])
#-------------------User commands-----------------------
    @commands.group(pass_context=True, case_insensitive=True)
    async def user(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @user.command(name="profile", pass_context=True, no_pm=True)
    async def profile(self, ctx, *, user: discord.Member=None):
        """Displays a given user's profile"""
        if user is None:
            user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        await self.bot.send_typing(ctx.message.channel)

        em = await profileEmbed(user, userinfo)
        await self.bot.say(embed=em)

    @user.command(name="registerchars", pass_context=True, no_pm=True)
    async def registerchars(self, ctx, *, arg):
        """Registers characters to the command's user. Character numbers should be seperated by spaces."""
        user = ctx.message.author
        await self._create_user(user)

        numbers = list(filter(None, re.sub("[^0-9]+", ",", (arg)).split(",")))

        db.users.update_one({'user_id': user.id}, {'$set': {
            "registered_characters": numbers,
        }})
        await self.bot.say("Registered " + ('{} Characters: {} Use `n!tfs update` to update your profile.'.format(len(numbers), ', '.join(numbers))))

    @checks.admin_or_permissions(manage_roles=True)
    @user.command(name="assignchars", pass_context=True, no_pm=True)
    async def assignchars(self, ctx, user: discord.Member=None, *, arg):
        """Assigns characters to a user. Character numbers should be seperated by spaces."""
        if user is None:
            await self.bot.say("You need to specify a user.")
        await self._create_user(user)

        numbers = list(filter(None, re.sub("[^0-9]+", ",", (arg)).split(",")))

        db.users.update_one({'user_id': user.id}, {'$set': {
            "registered_characters": numbers,
        }})
        await self.bot.say("Registered " + ('{} Characters to {}: {}'.format(len(numbers), user.name, ', '.join(numbers))))

    @user.command(name="display_characters", pass_context=True, no_pm=True)
    async def display_characters(self, ctx, *, user: discord.Member=None):
        """Display names and character numbers of a given user"""
        if user is None:
            user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        await self.bot.send_typing(ctx.message.channel)
        displayNames = []
        characterNumbers = []

        for characterNumber in userinfo["registered_characters"]:
            profile = await GETprofileforNumber(characterNumber)
            displayNames.append((GETdisplayName(profile)))
            characterNumbers.append(characterNumber)
        await self.bot.say(characterNumbers)
        await self.bot.say(str(' '.join(displayNames)))

    @user.command(name="totalposts", pass_context=True, no_pm=True)
    async def display_total_posts(self, ctx, *, user: discord.Member=None):
        """Total number of posts across a given user's registered characters"""
        if user is None:
            user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        await self.bot.send_typing(ctx.message.channel)
        posts_list = []
        profiles_list = []

        for characterNumber in userinfo["registered_characters"]:
            profile = await GETprofileforNumber(characterNumber)
            profiles_list.append(profile)
            posts_list.append(
                float(re.sub("[^0-9]+", "", (GETposts(profile)))))
        total_posts = int(sum(posts_list))
        await self.bot.say(total_posts)

    @user.command(name='posts', pass_context=True, no_pm=True)
    async def posts(self, ctx, *, user: discord.Member=None):
        """A posts overview for a given user"""
        if user is None:
            user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        await self.bot.send_typing(ctx.message.channel)
        channel = ctx.message.channel
        posts_list = []
        profiles_list = []

        for characterNumber in userinfo["registered_characters"]:
            profile = await GETprofileforNumber(characterNumber)
            profiles_list.append(profile)

        em = await characterPostsEmbed(user, userinfo, profiles_list)
        await self.bot.send_message(channel, "", embed=em)

    @user.command(name='lastposts', pass_context=True, no_pm=True)
    async def lastPosts(self, ctx, *, user: discord.Member=None):
        """Displays an embed showing the last posts for a given user's registered characters"""
        if user is None:
            user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        await self.bot.send_typing(ctx.message.channel)
        channel = ctx.message.channel
        posts_list = []
        profiles_list = []

        for characterNumber in userinfo["registered_characters"]:
            profile = await GETprofileforNumber(characterNumber)
            profiles_list.append(profile)

        em = await lastPostsEmbed(user, userinfo, profiles_list)
        await self.bot.send_message(channel, "", embed=em)

    @user.command(name='attribute', pass_context=True, no_pm=True)
    async def attribute(self, ctx, attribute: str, user: discord.Member=None):
        """Displays an embed showing a given attribute for a given user's registered characters"""
        if user is None:
            user = ctx.message.author
        await self._create_user(user)
        userinfo = db.users.find_one({'user_id': user.id})
        await self.bot.send_typing(ctx.message.channel)
        channel = ctx.message.channel
        attributes_list = []
        profiles_list = []

        for characterNumber in userinfo["registered_characters"]:
            profile = await GETprofileforNumber(characterNumber)
            profiles_list.append(profile)

        em = await attributeEmbed(user, userinfo, profiles_list, attribute)
        await self.bot.send_message(channel, "", embed=em)


#--------------------Other functions--------------------


async def update(self, ctx, user):
    await self._create_user(user)
    userinfo = db.users.find_one({'user_id': user.id})
    await self.bot.send_typing(ctx.message.channel)
    if "character_names" not in userinfo:
        db.users.update_one({'user_id': user.id}, {'$set': {
            "character_names": await GETdisplayNamesforUser(user),
        }}, upsert=True)
    await updateRole(user)
    await GETtotalPostsforUser(user)
    await GETdisplayNamesforUser(user)
    server = ctx.message.server
    await setRole(self, user, server)
    await self.bot.say("Updated information for " + user.name + ".")


async def updateRole(user):
    userinfo = db.users.find_one({'user_id': user.id})
    isActive = await checkActive(user)

    db.users.update_one({'user_id': user.id}, {'$set': {"active": isActive, }})

    if isActive is True:
        db.users.update_one({'user_id': user.id}, {
                            '$set': {"role": "Members", }})
    elif isActive is False:
        for characterNumber in userinfo["registered_characters"]:
            try:
                characterNumber = int(characterNumber)
            except ValueError:
                pass
            db.users.update_one({'user_id': user.id}, {
                                '$set': {"role": "Members (Inactive)", }})
            return


async def setRole(self, user, server):
    userinfo = db.users.find_one({'user_id': user.id})
    userRoles = user.roles
    members = discord.utils.get(server.roles, name="Members")
    inactive = discord.utils.get(server.roles, name="Members (Inactive)")
    guests = discord.utils.get(server.roles, name="Guests")

    if userinfo["role"] == "Members":
        await self.bot.remove_roles(user, inactive, guests)
        await self.bot.add_roles(user, members)
    if userinfo["role"] == "Members (Inactive)":
        await self.bot.remove_roles(user, members, guests)
        await self.bot.add_roles(user, inactive)
    if userinfo["role"] == "Guests":
        await self.bot.remove_roles(user, inactive, members)
        await self.bot.add_roles(user, guests)


async def checkActive(user):
    lastpost = await GETusersLastPostAgo(user)
    activeTime = datetime.timedelta(days=-30)
    if lastpost is None:
        return False
    elif (lastpost < activeTime) is False:
        return True
    else:
        return False


async def searchOwner(characterNumber, server):
    for user in server.members:
        userinfo = db.users.find_one({'user_id': user.id})
        try:
            for ownedCharacter in userinfo["registered_characters"]:
                if ownedCharacter == characterNumber:
                    return user.name
        except:
            pass
    else:
        return None

#----------------GET functions-----------------


async def GETdisplayNamesforUser(user):
    userinfo = db.users.find_one({'user_id': user.id})
    displayNames = []
    for characterNumber in userinfo["registered_characters"]:
        profile = await GETprofileforNumber(characterNumber)
        displayNames.append(str(GETdisplayName(profile)))
    db.users.update_one({'user_id': user.id}, {
                        '$set': {"character_names": displayNames, }})
    return displayNames


async def GETtotalPostsforUser(user):
    userinfo = db.users.find_one({'user_id': user.id})
    posts_list = []
    for characterNumber in userinfo["registered_characters"]:
        profile = await GETprofileforNumber(characterNumber)
        posts_list.append(float(re.sub("[^0-9]+", "", (GETposts(profile)))))
    total_posts = int(sum(posts_list))
    db.users.update_one({'user_id': user.id}, {
                        '$set': {"total_posts": total_posts, }})
    return total_posts


async def GETusersLastPostAgo(user):
    userinfo = db.users.find_one({'user_id': user.id})
    dateslist = []
    for characterNumber in userinfo["registered_characters"]:
        lastpostdate = await GETlastpostTime(characterNumber)
        if lastpostdate != "Never":
            now = datetime.datetime.now()
            timeDiff = lastpostdate - now
            dateslist.append(timeDiff)
    dateslist.sort(reverse=True)
    if dateslist:
        return dateslist[0]
    else:
        return None


async def GETprofileforNumber(characterNumber):
    recentURL = "http://thefantasysandbox.boards.net/user/" + \
        str(characterNumber) + "/recent"
    async with aiohttp.get(recentURL) as response:
        soupObject = BeautifulSoup(await response.text(), "html.parser")
    profile = soupObject.find(class_="mini-profile")
    return profile


async def GETrecentfromNumber(characterNumber):
    recentURL = "http://thefantasysandbox.boards.net/user/" + \
        str(characterNumber) + "/recent"
    async with aiohttp.get(recentURL) as response:
        soupObject = BeautifulSoup(await response.text(), "html.parser")
    return soupObject


async def GETattributeForProfile(profile, attribute):
    output = []
    if attribute == "posts":
        return GETposts(profile)
    elif attribute == "username":
        return GETusername(profile)
    elif attribute == "registerDate":
        return GETregisterDate(profile)
    elif attribute == "gender":
        return GETgender(profile)
    elif attribute == "allegiance":
        return GETcustomAttribute(profile, "allegiances")
    else:
        return "Error, invalid attribute"


def GETdisplayName(profile):
    if profile is None:
        return "Error obtaining display_name"
    else:
        return profile.a.contents[0]


def GETstar(profile):
    return "https:/" + str(profile.contents[6]).partition("/")[2].rstrip('"/>')


def GETrank(stripped_strings):
    return stripped_strings[1]


def GETregisterDate(profile):
    registerDate = profile.find(class_="o-timestamp time").string
    registerConstructor = registerDate.split(" ")
    return registerConstructor[0] + " " + registerConstructor[1] + " " + registerConstructor[2]


def GETcolor(profile):
    allegiance = GETcustomAttribute(profile, "allegiances")
    for key, val in factions.items():
        if re.search(key, allegiance, re.IGNORECASE) is not None:
            return val
    return 0x36393F  # gray


def GETavatar(profile):
    avatar = str(profile.div.img).split('"')[3]
    if avatar[0] is "/":
        return "https:" + avatar
    else:
        return avatar


def GETusername(profile):
    return "@" + (str(profile.a).split("@")[1]).split('"')[0]


def GETposts(profile):
    if profile is None:
        return "0"
    else:
        return profile.find(class_="info").contents[0].split(" ")[2]


def GETgender(profile):
    contentList = []
    gender = ""
    if profile is None:
        return "Unknown"
    for child in profile.children:
        contentList.append(child)
        if re.search("[female]{6,}", str(child)):
            return "Female"
        elif re.search("[male]{4,}", str(child)):
            return "Male"
    try:
        gender = (str(contentList[16]).split('"')[5])
    finally:
        if gender == "Female" or gender == "Male":
            return str(gender)
        else:
            return "Other"


def GETgenderSymbol(profile):
    gender = GETgender(profile)
    if gender == "Male":
        return "https://i.imgur.com/G0j21CT.png"
    elif gender == "Female":
        return "https://i.imgur.com/hDXZ9ES.png"
    else:
        return "https://i.imgur.com/dbHOlQf.png"


def GETcustomAttribute(profile, attribute):
    className = "custom-field-" + attribute
    attributeList = []
    if profile.find(class_=className) is None:
        return ""
    else:
        for string in profile.find(class_=className).stripped_strings:
            if re.search('[a-zA-Z0-9]', string) is not None:
                attributeList.append(repr(string).strip("'"))
        attributeName = attributeList[0].partition(":")[0]
        attributeContent = attributeList[0].partition(":")[2]
        if re.search('[a-zA-Z0-9]', attributeContent) is None:
            attributeContent = attributeList.pop(1)
        attributeContinued = "\n".join(attributeList[1:])
        return str("**" + attributeName + ":** " + attributeContent + "\n" + attributeContinued + "\n")


async def GETlastpostTime(characterNumber):
    soupObject = await GETrecentfromNumber(characterNumber)
    dateClass = soupObject.find(class_="date")
    if dateClass is None:
        return "Never"
    else:
        unixTime = str(dateClass.contents).split('"')[3]
        unixTime = float(unixTime[:(len(unixTime) - 3)])

        dateObject = datetime.datetime.fromtimestamp(unixTime)
        return dateObject


async def GETlastpostThread(characterNumber):
    soupObject = await GETrecentfromNumber(characterNumber)
    threadClass = soupObject.find(class_="js-thread__title-link")

    output = str(threadClass.contents[0])
    return output


async def GETlastpostThreadLink(characterNumber):
    soupObject = await GETrecentfromNumber(characterNumber)
    threadClass = soupObject.find(class_="thread-link")
    postID = await GETlastpostID(characterNumber)
    output = "http://thefantasysandbox.boards.net" + \
        threadClass['href'] + "?page=9001&scrollTo=" + postID

    return str(output)


async def GETlastpostContent(characterNumber):
    soupObject = await GETrecentfromNumber(characterNumber)
    threadClass = soupObject.find(class_="message")
    output = str(threadClass.contents[0])[0:1900]
    return output


async def GETlastpostID(characterNumber):
    soupObject = await GETrecentfromNumber(characterNumber)
    buttonClass = soupObject.find(class_="quote-button")
    output = str(buttonClass['href']).split("/")[2]
    return output


def CONSTRUCTinfo(profile):
    outputList = []
    for attribute in attributes:
        outputList.append(GETcustomAttribute(profile, attribute))
    output = "".join(outputList)
    return str(output)[0:1990]


def _name(self, user, max_length):
    if user.name == user.display_name:
        return user.name
    else:
        return "{} ({})".format(user.name, self._truncate_text(user.display_name, max_length - len(user.name) - 3), max_length)


#--------Setup---------
def check_folders():
    if not os.path.exists("data/buckycog"):
        print("Creating data/buckycog folder...")
        os.makedirs("data/buckycog")

    if not os.path.exists("data/buckycog/temp"):
        print("Creating data/buckycog/temp folder...")
        os.makedirs("data/buckycog/temp")

    if not os.path.exists("data/buckycog/users"):
        print("Creating data/buckycog/users folder...")
        os.makedirs("data/buckycog/users")


def transfer_info():
    try:
        users = fileIO("data/buckycog/users.json", "load")
        for user_id in users:
            os.makedirs("data/buckycog/users/{}".format(user_id))
            # create info.json
            f = "data/buckycog/users/{}/info.json".format(user_id)
            if not fileIO(f, "check"):
                fileIO(f, "save", users[user_id])
    except:
        pass


def setup(bot):
    check_folders()
    n = buckycog(bot)
    bot.add_cog(n)
