from selenium import webdriver
import sqlite3, requests, time, re, os, pickle, json
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

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
    def __init__(self):
        self.db_name = 'github_user_data.db'
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.conn.create_function("REGEXP", 2, regexp)
        options = Options()
        options.add_argument("user-data-dir=C:\\Users\\devfe\\AppData\\Local\\Microsoft\\Edge\\User Data")
        options.add_argument("profile-directory=Personal")

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

    def export_to_json(self, json_file_path, location):
        self.cursor.execute(f"SELECT * FROM {location}")
        rows = self.cursor.fetchall()
        column_names = [description[0] for description in self.cursor.description]
        data = [dict(zip(column_names, row)) for row in rows]
        with open(json_file_path, "a") as json_file:
            json_file.write("\n")
            json.dump({location: data}, json_file, indent=4)

    def export_all_to_json(self, json_file_path):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in self.cursor.fetchall()]

        all_data = {}
        for table in tables:
            self.cursor.execute(f"SELECT * FROM {table}")
            rows = self.cursor.fetchall()
            column_names = [description[0] for description in self.cursor.description]
            all_data[table] = [dict(zip(column_names, row)) for row in rows]

        with open(json_file_path, "a") as json_file:
            json_file.write("\n")
            json.dump(all_data, json_file, indent=4)

    def get_data(self, location):
        self.location = location
        self.create_table()
        if not self.login():
            return 
        base_url = 'https://api.github.com/search/users'
        per_page = 100

        self.cursor.execute(f'SELECT COUNT(*) FROM {self.location}')
        url = f'{base_url}?q=location:{self.location}&per_page=1'
        response = requests.get(url)
        data = response.json()
        total_count = data.get('total_count', 0)
        print(data)
        if data.get('message') and "API rate limit exceeded" in data['message']:
            print("Sleeping.....")
            time.sleep(18)
            return self.get_data(location)
        for i in range(10):
            url = f'{base_url}?q=location:{self.location}&per_page=100&page={i+1}&sort=joined'
            response = requests.get(url)
            data = response.json()
            users = data.get('items', [])
            if not users:
                if data.get('message') and "API rate limit exceeded" in data['message']:
                    print("Sleeping.....")
                    time.sleep(18)
                    url = f'{base_url}?q=location:{self.location}&per_page=100&page={i+1}&sort=joined'
                    response = requests.get(url)
                    data = response.json()
                    users = data.get('items', [])
                    if not users:
                        print(users)
                        print("No more data to fetch. Exiting...")
                        break
            print(f'Fetching page {i+1} of {total_count // per_page}')
            user_data = [(user['login'], user['html_url']) for user in users]
            self.cursor.executemany(f'INSERT INTO {self.location} (username, profile_url) VALUES (?, ?)', user_data)
            self.conn.commit()
        
        # self.update_primary_link()

    def update_primary_link(self, location):
        if not self.login():
            return 
        self.location = location
        self.cursor.execute(f'SELECT id, profile_url FROM {self.location} WHERE primary_link IS NULL')
        users = self.cursor.fetchall()

        go_time = 0

        for id, profile_url in users:
            primary_link, username = self.get_name_primary_link(profile_url)
            if primary_link and bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", primary_link)):
                print(f'{id}. Username: {username}  primary_link: {primary_link}')
                go_time +=1
                self.cursor.execute(f'UPDATE {self.location} SET primary_link = ? WHERE id = ?', (primary_link, id))
                if username:
                    self.cursor.execute(f'UPDATE {self.location} SET username = ? WHERE id = ?', (username, id))
                if go_time % 10 == 0:
                    self.conn.commit()
            else:
                self.cursor.execute(f'DELETE FROM {self.location} WHERE id = ?', (id,))
        self.conn.commit()

    def get_user_mails(self):
        self.cursor.execute(f"SELECT username, primary_link FROM ogun WHERE TRIM(primary_link) REGEXP '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'")
        users_mails = self.cursor.fetchall()
        return users_mails

    def login(self):
        if not self.driver:
            self.driver = webdriver.Edge()
        if False and os.path.exists("cookies.pkl"):
            with open("cookies.pkl", "rb") as file:
                cookies = pickle.load(file)
            self.driver.get('https://github.com/toheebcodes')
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            if self.driver.current_url == "https://github.com/toheebcodes":
                return True
        
        self.driver.get('https://github.com/login')
        wait_time = 0
        
        while True:
            time.sleep(2)
            wait_time += 1
            if self.driver.current_url == "https://github.com/":
                # with open("cookies.pkl", "wb") as file:
                #    pickle.dump(self.driver.get_cookies(), file)
                time.sleep(2)
                return True
            if wait_time % 5 == 0:
                print(f"waiting for user to finish login...{wait_time}")
            if wait_time == 150: # 5 mins
                print("time out........not logged in")
                return False

    def get_name_primary_link(self, profile_url):
        response = self.driver.execute_script(f"""
                async function getNamePrimaryLink(profileUrl) {{
                    try {{
                        const response = await fetch(profileUrl);
                        if (!response.ok) {{
                            console.error("response.status_code: ", response.status);
                            return [null, null];
                        }}
                        const text = await response.text();
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(text, 'text/html');

                        let primaryLink = null;
                        let username = null;

                        const primaryLinkElement = doc.querySelector('.Link--primary');
                        const usernameElement = doc.querySelector('.vcard-fullname');
                        if (primaryLinkElement) {{
                            primaryLink = primaryLinkElement.textContent.trim();
                        }}
                        if (usernameElement) {{
                            username = usernameElement.textContent.trim();
                        }}

                        return [primaryLink, username];
                    }} catch (error) {{
                        console.error("Error fetching the profile URL:", error);
                        return [null, null];
                    }}
                }}

                return getNamePrimaryLink('{profile_url}');
        """)
        print(response)
        primary_link, username = response[0], response[1]
        return primary_link, username

    def close(self):
        if self.login:
            self.conn.close()
        time.sleep(2)
        self.driver.quit()

