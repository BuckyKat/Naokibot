import arrow

from redbot.core import Config

from .character import Character


# Helper finctions
def _remove(duplicate):
    final_list = []
    for num in duplicate:
        if num not in final_list:
            final_list.append(num)
    return final_list


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
            "updated": arrow.utcnow().isoformat(),  # store as string
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
                try:
                    this_character = await Character.from_num(num)
                    if this_character and this_character.active:
                        await self.data.user(user).active.set(True)
                        return True
                except Exception as e:
                    # Could log the error if needed
                    print(f"Error checking activity for character {num}: {e}")
                    continue  # Treat error as "not active"
            # If no characters were found active (or all errored), mark as inactive
            await self.data.user(user).active.set(False)
        return False


    async def update_names(self, user):
        name_list = []
        async with self.data.user(user).characters() as char_list:
            for num in char_list:
                try:
                    this_character = await Character.from_num(num)
                    if this_character:
                        name = this_character.display_name
                    else:
                        name = f"Unknown {num}"
                except Exception as e:
                    print(f"Error getting character {num}: {e}")
                    name = f"Unknown {num}"
                name_list.append(name)
            await self.data.user(user).display_names.set(name_list)
        return True

    async def update_posts(self, user):
        post_count = 0
        async with self.data.user(user).characters() as char_list:
            for num in char_list:
                try:
                    this_character = await Character.from_num(num)
                    if this_character:
                        posts = this_character.posts
                        post_count += int(posts)
                    else:
                        # Character not found or returned None — count as 0
                        continue
                except Exception as e:
                    # Log or print the error if needed
                    print(f"Error getting posts for character {num}: {e}")
                    # Treat error as 0 posts (no increment needed)
                    continue
            await self.data.user(user).posts.set(post_count)
        return True

