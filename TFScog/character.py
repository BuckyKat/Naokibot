import arrow
import re

import aiohttp
import discord
from babel.dates import format_timedelta
from bs4 import BeautifulSoup

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
    "correa": 0xBB0A1E,
    "usque": 0xD794DB,
}


# HELPER FUNCTIONS
async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


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


class Character:
    def __init__(self, profile, soup, number, discord_name=None):
        self.profile = profile
        self.soup = soup
        self.number = number
        self.discord_name = discord_name

    @classmethod
    async def from_num(cls, num, discord_name=None):
        recent_url = f"http://themistborneisles.boards.net/user/{num}/recent"
        
        # Headers to mimic a real browser
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                try:
                    html = await fetch(session, recent_url)
                except ClientError as e:
                    raise ValueError(f"Failed to fetch character page due to network error: {e}") from e

                if not html:
                    raise ValueError(f"Empty HTML response for character {num} at {recent_url}")

                try:
                    soup_object = BeautifulSoup(html, "html.parser")
                except Exception as e:
                    raise ValueError(f"Failed to parse HTML for character {num}") from e

                _profile = soup_object.find(class_="mini-profile")
                if not _profile:
                    raise ValueError(f"Could not find a mini-profile for character {num}")

                return cls(_profile, soup_object, num, discord_name)

        except Exception as e:
            raise ValueError(f"Unexpected error in from_num for character {num}: {e}")



    @property
    def embed(self):
        em = discord.Embed(
            title=self.username + " (" + str(self.number) + ")",
            url=self.profile_url,
            description=(
                "Last post: "
                + self.last_post_time_fancy
                + " in "
                + self.last_post_markdown
            ),
        )
        em.set_thumbnail(url=self.avatar)
        em.set_author(name=self.display_name, icon_url=self.gender_symbol)
        em.add_field(name="Discord ID:", value=self.discord_name, inline=False)
        em.add_field(name="Post Count:", value=self.posts, inline=True)
        em.add_field(name="Register Date:", value=self.register_date, inline=True)
        if self.age != "Not set":
            em.add_field(name="Age:", value=self.age, inline=True)
        if self.appearance != "Not set":
            em.add_field(
                name="Appearance:", value=truncate(self.appearance), inline=False
            )
        if self.equipment != "Not set":
            em.add_field(
                name="Equipment:", value=truncate(self.equipment), inline=False
            )
        if self.skills_and_abilities != "Not set":
            em.add_field(
                name="Skills and abilities:",
                value=truncate(self.skills_and_abilities),
                inline=False,
            )
        if self.biography != "Not set":
            em.add_field(
                name="Biography:", value=truncate(self.biography), inline=False
            )
        footer = self.rank + "  |  " + active_fancy(self.active)
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
        return str(button_class["href"]).split("/")[2]

    @property
    def last_post_link(self):
        _soup = self.soup
        thread_class = _soup.find(class_="thread-link")
        post_id = self.last_post_id
        output = (
            "http://themistborneisles.boards.net"
            + thread_class["href"]
            + "?page=9001&scrollTo="
            + post_id
        )
        return str(output)

    @property
    def last_post_time(self):
        _soup = self.soup
        date_class = _soup.find(class_="date")
        if date_class is None:
            return None
        else:
            unix_time = str(date_class.contents).split('"')[3]
            unix_time = float(unix_time[: (len(unix_time) - 3)])

            date_object = datetime.datetime.fromtimestamp(unix_time)
            return date_object

    @property
    def last_post_time_fancy(self):
        time_stamp = self.last_post_time
        if time_stamp:
            now = arrow.utcnow()
            time_diff = now - arrow.get(time_stamp)
            return format_timedelta(time_diff, locale="en_US") + " ago"
        else:
            return "Never"

    @property
    def last_post_markdown(self):
        return str("[" + self.last_post_thread + "](" + self.last_post_link + ")")

    @property
    def profile_url(self):
        return "http://themistborneisles.boards.net/user/" + str(self.number)

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
        return (
            register_constructor[0]
            + " "
            + register_constructor[1]
            + " "
            + register_constructor[2]
        )

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
            gender = self.profile.find(class_="info").img.attrs["title"]
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
                if re.search("[a-zA-Z0-9]", string) is not None:
                    attribute_list.append(repr(string).strip("'"))
            # attribute_name = attribute_list[0].partition(":")[0]
            attribute_content = attribute_list[0].partition(":")[2]
            if re.search("[a-zA-Z0-9]", attribute_content) is None:
                attribute_content = attribute_list.pop(1)
            attribute_continued = "\n".join(attribute_list[1:])
            return str(attribute_content + "\n" + attribute_continued + "\n")
