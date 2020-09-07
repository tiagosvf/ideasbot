import yaml
import requests
from bs4 import BeautifulSoup

with open("settings.yaml") as file:
    settings = yaml.load(file, Loader=yaml.FullLoader)
    token = settings["discord"]["token"]
    refresh_frequency = settings["bot"]["refresh_frequency"]

URL = 'https://ideasai.net/'
page = requests.get(URL)
soup = BeautifulSoup(page.content, 'html.parser')

elem = soup.find("h2", limit=1)[0]

while True:
    elem = elem.next_sibling

    if elem.name == "table":
        idea = elem.find(class_="idea")
        text = idea.text.strip()
        print(text)
    elif elem.name == "h2":
        break
