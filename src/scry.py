import os
import openai
import json
import datetime

openai.api_key = os.getenv('OPENAI_API_KEY')

MAX_TOKENS = 500

async def scry(path, results=[]):
    tree = []
    async def helper():
        for filename in os.listdir(path):
            if 'posts' not in filename and '.' not in filename:
                return await scry(path+'/'+filename, results)
            else:
                results.append(filename)
    helper()

    return results

def chat_with_chatgpt(prompt, model="gpt-3.5-turbo"):
    completion = openai.ChatCompletion.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a fantasy author with a vivid and diverse imagination."},
        {"role": "user", "content": f"{prompt}"}
    ]
    )

    return completion.choices[0].message['content']

def get_all_file_paths(root_dir):
    # List to store the paths of all files in the directory and subdirectories
    file_paths = []

    # Recursive function to populate the file_paths list
    def recurse_dir(current_dir):
        # Check the entries present in the current directory
        with os.scandir(current_dir) as it:
            for entry in it:
                # Construct the path to the entry
                path = os.path.join(current_dir, entry.name)

                if entry.is_dir(follow_symlinks=False):
                    # If entry is a directory, recurse into it
                    recurse_dir(path)
                elif entry.is_file():
                    # If entry is a file, append the path to file_paths
                    file_paths.append(path)

    # Start the recursion from the root directory
    if os.path.exists(root_dir) and os.path.isdir(root_dir):
        recurse_dir(root_dir)
    else:
        raise ValueError(f"Path not found: {root_dir}")

    return file_paths

def extract_user_messages(file_path):
    """
    Extracts user and message data from a JSON file and returns it keyed to the timestamp.

    :param file_path: Path to the input JSON file.
    :return: A dictionary containing the user, message, and timestamp.
    """
    # The dictionary to store the extracted data
    messages_dict = {}

    try:
        # Open the file and load the JSON
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

            # Iterate through the posts in the JSON data
            for post_id, post_info in data.items():
                # Extract the relevant information
                user = post_info.get("user")
                message = post_info.get("message")
                timestamp = post_info.get("timestamp")

                if user and message and timestamp:
                    # Add the information to our dictionary
                    messages_dict[timestamp] = {
                        'user': user,
                        'message': message
                    }
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
    except json.JSONDecodeError:
        print("There was an error decoding the JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return messages_dict

def print_messages_in_order(messages):
    # Convert the string keys into integers and sort the items based on these keys
    sorted_messages = sorted(messages.items(), key=lambda x: int(x[0]))

    for timestamp, message_details in sorted_messages:
        user = message_details['user']
        message = message_details['message']
        
        # Convert the timestamp to a more readable format (optional)
        timestamp_readable = datetime.datetime.fromtimestamp(int(timestamp) / 1000.0)  # assuming the timestamp is in milliseconds

        print(f'[{timestamp_readable}] {user}: {message}')

def find_user_messages(data, username):
    """
    Find all messages for a specific user.

    Parameters:
    data (str): The JSON string with all the post data.
    username (str): The username to search for.

    Returns:
    dict: A dictionary with timestamps as keys and messages as values.
    """
    
    # Load the JSON data into a Python dictionary
    # If the data is already a dictionary, you can skip this step
    if isinstance(data, str):
        all_posts = json.loads(data)
    else:
        all_posts = data

    # Initialize an empty dictionary to hold the results
    user_messages = {}

    # Go through all posts in the data
    for post_id, post_info in all_posts.items():
        if post_info['user'] == username:
            timestamp = post_info['timestamp']
            message = post_info['message']
            user_messages[timestamp] = message

    return user_messages

data = '''
user	:	Takhana Veil
message	:	Thanks to the housing graciously provided to the employees of The Midnight Sun, Takhana Veil was able to acquire this delightful home on a peaceful street in Isra. Two stories with a small garden courtyard and a small attached stable, it consists of a first floor living room, kitchen, and dining area, with a single bedroom and bathing room on the second floor, and third floor comprised of a home office. The half-Drow dwells here alone, unless one counts the mare who resides in the stable and the cat that keeps her company inside. Due to her employment with the renowned organization, the home has been very securely warded against intrusion, violence, and magical attacks by the mages of The Midnight Sun.(OOC: Permission to enter must be gained via PM.)FoyerLiving AreaKitchenDining AreaOfficeBathing RoomBedroom
'''

if __name__ == '__main__':
    paths = get_all_file_paths('src/data/tfs/forum/overworld/')
    file_info = extract_user_messages(paths[1])
    user_messages = {}
    username = 'Empress Naoki'
    for path in paths:
        if '.DS_Store' not in path:
            with open(path, 'r') as file:
                data = json.load(file)
                messages = find_user_messages(data, username)
                user_messages.update(messages)

    with open(f'{username}.json', 'w') as file:
        json.dump(user_messages, file)