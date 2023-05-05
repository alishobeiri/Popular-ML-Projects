import os
import re
import datetime
import requests
import pandas as pd
import shutil
from dotenv import load_dotenv

load_dotenv()

SCORE_FILTER = 25

# note that CLIENT_ID refers to 'personal use script' and SECRET_TOKEN to 'token'
auth = requests.auth.HTTPBasicAuth(os.environ.get("CLIENTID"), os.environ.get("SECRET"))

def copy_readme_with_date(src_dir, dest_dir):
    # Define the path to the source README.md file
    src_file = os.path.join(src_dir, 'README.md')

    # Check if the source file exists
    if not os.path.exists(src_file):
        print("Source file does not exist:", src_file)
        return

    # Get the current date and time
    current_datetime = datetime.datetime.now()

    # Calculate the date and time of yesterday
    yesterday_datetime = current_datetime - datetime.timedelta(days=1)

    # Format the date and time of yesterday
    formatted_datetime = yesterday_datetime.strftime('%Y-%m-%d_%H-%M-%S')

    # Create a unique name for the destination file using the date and time of yesterday
    dest_file = os.path.join(dest_dir, f'README_{formatted_datetime}.md')

    # Ensure that the destination directory exists
    os.makedirs(dest_dir, exist_ok=True)

    # Copy the file and preserve metadata (e.g., timestamps)
    shutil.copy2(src_file, dest_file)

    # Print a message to indicate success
    print(f'Copied README.md to {dest_file}')


# here we pass our login method (password), username, and password
data = {'grant_type': 'password',
        'username': os.environ.get("REDDIT_USERNAME"),
        'password': os.environ.get("PASSWORD")}

print(data)

# setup our header info, which gives reddit a brief description of our app
headers = {'User-Agent': 'MyBot/0.0.1'}

# send our request for an OAuth token
res = requests.post('https://www.reddit.com/api/v1/access_token',
                    auth=auth, data=data, headers=headers)

print(res)
print(res.json())

# convert response to JSON and pull access_token value
TOKEN = res.json()['access_token']

# add authorization to our headers dictionary
headers = {**headers, **{'Authorization': f"bearer {TOKEN}"}}

# while the token is valid (~2 hours) we just add headers=headers to our requests
requests.get('https://oauth.reddit.com/api/v1/me', headers=headers)


res = requests.get("https://oauth.reddit.com/r/machinelearning/hot?f=flair_name%3A%22Research%22",
                   headers=headers)

out = []
# loop through each post retrieved from GET request
for post in res.json()['data']['children']:
    _post = post['data']

    print(_post['selftext'])

    # search for the pattern in the string and extract the URL
    urls = re.findall(r'\((https?://arxiv\.org/\S+)\)', _post['selftext'])
    for url in urls:
        # append relevant data to dataframe
        if _post['score'] > SCORE_FILTER:
            out.append({
                    'Title': _post['title'],
                    'URL': url,
                    'Score': _post['score'],
                    'Date': datetime.datetime.utcfromtimestamp(_post['created_utc'])
            })

    # search for the pattern in the string and extract the URL
    github_urls = re.findall(r'\((https?://github\.com/\S+)\)', _post['selftext'])
    for url in github_urls:
        # append relevant data to dataframe
        if _post['score'] > SCORE_FILTER:
            out.append({
                    'Title': _post['title'],
                    'URL': url.strip(')').strip('(').strip('[').strip(']'),
                    'Score': _post['score'],
                    'Date': datetime.datetime.utcfromtimestamp(_post['created_utc'])
            })

df = pd.DataFrame(out)

df = df.drop_duplicates(subset='URL', keep='first')

df = df.groupby('Title').agg({
    'URL': '\n'.join,
    'Score': 'first',  # Keep the first score in each group
    'Date': 'first'    # Keep the first date in each group
}).reset_index()

df = df.sort_values(by='Score', ascending=False)

# Save markdown string to file
with open('README.md', 'w') as f:
    df.to_markdown(f, index=False)

df.to_csv('hottest_ml_papers.csv', index=False)

copy_readme_with_date('./', './previous_dates/')
