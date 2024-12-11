### Hence: I'm using windows and i love edge so if you're a chrome or different os user and want to use this tools u can open issue i will update to support that

#### Sample usage

- install requirements

- create new file main.py or edit the main.py to

```python
from scraper import GitHubScraper

# your locations
location_tag = ["Lagos", "Ogun", "Osun", "Oyo"]

scraper = GitHubScraper()

# fetch data for each location provided max is 100*10
for location in location_tag:
    scraper.get_data(location.replace(' ',''))

# update user name and email address
for location in location_tag:
    scraper.update_primary_link(location.replace(' ',''))

# export specific state(table) to json
scraper.export_to_json('Abia.json', 'Abia')

# export all db to json file
scraper.export_all_to_json('data.json', )

```

- when prompt login ur account (safe) and minimize window (make sure window is keep alive) window will close automatically when done

- file github_user_data.db include all data of location set


#### note: just decide to build this when trying to spam a website and i need active email and names lol.
