from scraper import GitHubScraper

# your locations
location_tag = ["Lagos", "Ogun", "Osun", "Oyo"]

scraper = GitHubScraper()

scraper.export_all_to_json('data.json', )
