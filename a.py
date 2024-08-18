from selenium import webdriver
import sqlite3, requests, time, re
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By

def regexp(pattern, value):
    if value is None:
        return False
    try:
        reg = re.compile(pattern)
        return reg.search(value) is not None
    except Exception as e:
        print("error in regex: ", e)
        return False

class GitHubScraper:
    def __init__(self, location):
        self.db_name = 'github_user_data.db'
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.location = location
        self.create_table()
        self.conn.create_function("REGEXP", 2, regexp)

    def create_table(self):
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.location} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                profile_url TEXT NOT NULL,
                primary_link TEXT
            )
        ''')
        self.conn.commit()

    def get_data(self):
        if not self.login():
            return 
        base_url = 'https://api.github.com/search/users'
        per_page = 100

        self.cursor.execute(f'SELECT COUNT(*) FROM {self.location}')
        current_count = self.cursor.fetchone()[0]

        url = f'{base_url}?q=location:{self.location}&per_page=1'
        response = requests.get(url)
        data = response.json()
        total_count = data.get('total_count', 0)

        if current_count >= total_count:
            print("No new data to fetch. Exiting...")
            return self.update_primary_link()

        start_page = (current_count // per_page)
        while True:
            url = f'{base_url}?q=location:{self.location}&per_page={per_page}&page={start_page}&s=joined&o=asc'
            response = requests.get(url)
            data = response.json()
            users = data.get('items', [])

            if not users:
                print("No more data to fetch. Exiting...")
                break

            print(f'Fetching page {start_page+1} of {total_count // per_page}')
            
            user_data = [(user['login'], user['html_url']) for user in users]
            
            # If we are on the start page and have a partial page's worth of data,
            # we should overwrite the first few rows
            if current_count % per_page != 0 and start_page == (current_count // per_page):
                # Calculate the number of rows to overwrite
                rows_to_overwrite = current_count % per_page
                self.cursor.executemany(
                    f'UPDATE {self.location} SET username = ?, profile_url = ? WHERE id = ?',
                    [(user['login'], user['html_url'], i) for i, user in enumerate(users[:rows_to_overwrite])]
                )
                self.conn.commit()

                # Insert the remaining new rows
                user_data = user_data[rows_to_overwrite:]
            
            self.cursor.executemany(f'INSERT INTO {self.location} (username, profile_url) VALUES (?, ?)', user_data)
            self.conn.commit()

            if len(users) < per_page or start_page * per_page >= total_count:
                break

            start_page += 1
        
        self.update_primary_link()

    def update_primary_link(self):
        self.cursor.execute(f'SELECT id, username, profile_url FROM {self.location} WHERE primary_link IS NULL')
        users = self.cursor.fetchall()

        go_time = 0
        
        for index, db_username, profile_url in users:
            primary_link = self.get_name_primary_link(profile_url)
            print(f'{index}. Username: {db_username}  primary_link: {primary_link}')
            if primary_link:
                go_time +=1
                self.cursor.execute(f'UPDATE {self.location} SET primary_link = ? WHERE username = ?', (primary_link, db_username))
                if go_time % 10 == 0:
                    self.conn.commit()
            if index % 100 == 0:
                print("100 requested, sleeping 5 secs to prevent 429")
                time.sleep(5)
        self.conn.commit()

    def get_user_mails(self):
        self.cursor.execute(f"SELECT username, primary_link FROM ogun WHERE TRIM(primary_link) REGEXP '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'")
        users_mails = self.cursor.fetchall()
        return users_mails

    def login(self):
        driver = webdriver.Edge()
        driver.get('https://github.com/login')
        wait_time = 0
        
        while True:
            time.sleep(2)
            wait_time += 1
            if driver.current_url == "https://github.com/":
                time.sleep(2)
                return True
            if wait_time % 5 == 0:
                print(f"waiting for user to finish login...{wait_time}")
            if wait_time == 150: # 5 mins
                print("time out........not logged in")
                return False

    def get_name_primary_link(self, profile_url):
        result = self.driver.execute_script(f"""
                async function getNamePrimaryLink(profileUrl) {{
                    try {{
                        const response = await fetch(profileUrl);
                        if (!response.ok) {{
                            console.error("response.status_code: ", response.status);
                            return null;
                        }}
                        const text = await response.text();
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(text, 'text/html');

                        let primaryLink = null;

                        const primaryLinkElement = doc.querySelector('.Link--primary');
                        if (primaryLinkElement) {{
                            primaryLink = primaryLinkElement.textContent.trim();
                        }}

                        return primaryLink;
                    }} catch (error) {{
                        console.error("Error fetching the profile URL:", error);
                        return null;
                    }}
                }}

                return getNamePrimaryLink('{profile_url}');
        """)
        # if result is None This user has no primary link
        primary_link = result

        return primary_link

    def close(self):
        if self.login:
            self.conn.close()
        time.sleep(2)
        self.driver.quit()



scraper = GitHubScraper('ogun')
# scraper.get_data()
scraper.get_user_mails()
