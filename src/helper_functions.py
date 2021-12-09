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
