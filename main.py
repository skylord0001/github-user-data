from scraper import GitHubScraper

location_tag = "ogun" # change to ur location tag could have space etc or even ur coutry name its self e.g Nigeria

scraper = GitHubScraper(location_tag)

# scraper.get_data() 
# uncooment above line will get data (username, profile url, and primary link where primary link is most time email, website if no email or social account if no website or null if user have set)

# users = scraper.get_user_mails()
# uncomment above line will get u list of users with email from the db

# you maybe delete the db file github_user_data.db before puting urs