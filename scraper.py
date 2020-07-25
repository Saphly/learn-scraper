import grequests
import logging
import os
import pickle
import re
import requests
import urllib.parse

from bs4 import BeautifulSoup
from pathlib import Path

import config

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(config.LOG_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(config.LOG_LEVEL)


class LearnScraper:
    def __init__(self):
        self.session = requests.Session()
        self.cache_name = config.CACHE_DIR / "content_infos.pickle"
        self.learn_url = "https://www.learn.ed.ac.uk"
        self.ease_url = "https://www.ease.ed.ac.uk"
        self.content_infos = dict()
        self.folder_urls = set()
        self.downloaded = 0

    def _callback_factory(self, req_url):
        def _callback(r, **kwargs):
            if r.status_code != 200:
                return

            # save downloaded file
            fname = urllib.parse.unquote(r.url.split("/")[-1])
            fname = self._get_windows_compatible(fname)
            rel_dir_path = Path(self.content_infos[req_url]) / fname
            abs_dir_path = Path(config.DOWNLOAD_DIR) / rel_dir_path

            logger.debug(f"Downloading {rel_dir_path}")
            with open(abs_dir_path, "wb") as handler:
                handler.write(r.content)

            self.downloaded += 1
            if not self.downloaded % 10 or self.downloaded == len(self.content_infos):
                logger.info("Progress: %s/%s", self.downloaded, len(self.content_infos))

        return _callback

    def _exception_handler(self, r, exception):
        logger.warning("%s when trying to access %s - skipping...", exception, r.url)

    def _get_windows_compatible(self, word):
        """Sanitise input to make it compatible with Windows naming system,
           i.e. where the characters (\ / : * ? " < > |) are not allowed.

        Args:
            word (str): word to be sanitised.

        Returns:
            str: windows compatible word.
        """
        if os.name == "nt":
            return "".join(c for c in word if c not in r'\/:*?"<>|')

        return word

    def _send_request(self, url, method="GET", silent=False, is_soup=True, **kwargs):
        """Wrapper for requests HTTP methods with error handling and optional bs4 conversion.

        Args:
            url (str): URL to send HTTP request to.
            method (str, optional): HTTP request method. Defaults to "GET".
            silent (bool, optional): logs a warning to console instead of raising if True. Defaults to False.
            is_soup (bool, optional): whether to soupify the HTTP response text. Defaults to True.

        Raises:
            NotImplementedError: currently supported methods are "GET" and "POST".

        Returns:
            requests.models.Response or bs4.BeautifulSoup: returns souped response text if `is_soup` is True. Otherwise returns the Response object itself.
        """
        try:
            if method == "GET":
                r = self.session.get(url, **kwargs)
            elif method == "POST":
                r = self.session.post(url, **kwargs)
            else:
                raise NotImplementedError(f"Invalid method: {method}")
        except requests.exceptions.RequestException as e:
            if silent:
                logger.warning("%s when trying to access %s - skipping...", e, url)
            else:
                logger.exception("%s when trying to access %s.", e, url)
            return None

        if is_soup:
            return BeautifulSoup(r.text, "lxml")

        return r

    def login(self, username, password):
        """Logs a user in to learn and get course module tab data.

        Args:
            username (str): EASE username.
            password (str): EASE password.

        Returns:
            bs4.BeautifulSoup : course module tab XML data.
        """
        res = self._send_request(
            urllib.parse.urljoin(self.learn_url, "/auth-saml/saml/login"),
            params={"apId": "_175_1"},
        )
        redir_url = res.find("form").get("action")
        saml_token = res.find("input").get("value")
        res = self._send_request(
            redir_url, method="POST", data={"SAMLRequest": saml_token}
        )

        rel_url = res.find("form", class_="clearfix").get("action")
        data = {"login": username}
        for key in ["ref", "service", "submit"]:
            data[key] = res.find(id=key).get("value")
        res = self._send_request(
            urllib.parse.urljoin(self.ease_url, rel_url), method="POST", data=data
        )

        rel_url = res.find("form", class_="clearfix").get("action")
        data = {"password": password}
        for key in ["login", "ref", "service", "submit"]:
            data[key] = res.find(id=key).get("value")
        res = self._send_request(
            urllib.parse.urljoin(self.ease_url, rel_url), method="POST", data=data
        )

        redir_url = res.find("form").get("action")
        saml_token = res.find("input").get("value")
        res = self._send_request(
            redir_url, method="POST", data={"SAMLResponse": saml_token}
        )

        # Load course module tabs, which is populated dynamically.
        data = {
            "action": "refreshAjaxModule",
            "modId": "_4_1",
            "tabId": "_1_1",
            "tab_tab_group_id": "_171_1",
        }
        res = self._send_request(
            urllib.parse.urljoin(
                self.learn_url, "/webapps/portal/execute/tabs/tabAction"
            ),
            method="POST",
            data=data,
        )
        logger.info("Successfully logged in.")
        return res

    def get_course_urls(self, res):
        """Filters course module tab XML data to courses where user is enrolled as a student.

        Args:
            res (bs4.BeautifulSoup): course module tab XML data.

        Returns:
            set: all course urls where user is enrolled as a student.
        """
        course_urls = set()
        headers = res.find_all(
            "h4", string=re.compile("Courses where you are: Student")
        )

        for header in headers:
            ul = header.find_next_sibling("ul")
            courses = [
                f"{self.learn_url}{c.get('href').strip()}"
                for c in ul.find_all("a", href=config.COURSE_REGEX)
            ]
            course_urls.update(courses)

        logger.info("Found %s courses where you are a student.", len(course_urls))

        return course_urls

    def get_content_infos(self, url):
        """Recursively traverse through the given url to find all file urls and keeps track of the path taken to said file.

        Args:
            url (str): course page / folder url.
        """
        logger.debug("Visiting %s", url)

        r = self._send_request(url, is_soup=False, silent=True)
        res_url, res = r.url, BeautifulSoup(r.text, "lxml")

        # keep track of urls that we have visited
        self.folder_urls.add(res_url)

        breadcrumbs = (
            res.find(id="breadcrumbs")
            .find("ol", class_="clearfix")
            .find_all("span", id=re.compile(r"crumb_\d+"))
        )
        rel_dir_path = "/".join(
            self._get_windows_compatible(b.string.strip()) for b in breadcrumbs
        )
        logger.info("Currently in %s", rel_dir_path)

        if contents := res.find_all("a", href=config.CONTENT_REGEX):
            os.makedirs(config.DOWNLOAD_DIR / rel_dir_path, exist_ok=True)

        for content in contents:
            rel_content_url = content.get("href")
            abs_content_url = urllib.parse.urljoin(self.learn_url, rel_content_url)
            self.content_infos[abs_content_url] = rel_dir_path

        for folder in res.find_all("a", href=config.FOLDER_REGEX):
            # all hrefs are supposed to be relative, but some aren't ¯\_(ツ)_/¯
            href = folder.get("href").replace(self.learn_url, "")
            rel_folder_url = config.FOLDER_REGEX.match(href).group(0)
            abs_folder_url = urllib.parse.urljoin(self.learn_url, rel_folder_url)

            if abs_folder_url in self.folder_urls:
                continue

            self.get_content_infos(abs_folder_url)

    def download_one(self, dir_path, rel_url):
        """Downloads a specified file and saves it to the specified directory.

        Args:
            dir_path (str): directory to save the downloaded file to.
            rel_url (str): relative URL where the file can be downloaded from.
        """
        content_url = urllib.parse.urljoin(self.learn_url, rel_url)
        if r := self._send_request(content_url, is_soup=False, silent=True):
            fname = urllib.parse.unquote(r.url.split("/")[-1])
            with open(Path(dir_path) / fname, "wb") as handler:
                handler.write(r.content)

    def download_all(self):
        """Download all files found in `self.content_infos` in a multi-threaded fashion.
        """
        reqs = [
            grequests.get(
                url,
                session=self.session,
                timeout=config.TIMEOUT,
                callback=self._callback_factory(url),
            )
            for url in self.content_infos
        ]

        list(grequests.imap(reqs, exception_handler=self._exception_handler, size=8))

    def save_cache(self):
        """Saves file url and directory path metadata to a cache.
        """
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        logger.info("Saving content_infos...")
        with open(self.cache_name, "wb") as handle:
            pickle.dump(self.content_infos, handle, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("Saved content_infos.")

    def load_cache(self):
        """Loads file url and directory path from cache.
        """
        logger.info("Loading content_infos...")
        with open(self.cache_name, "rb") as handle:
            self.content_infos = pickle.load(handle)
        logger.info("Loaded content_infos.")


def main():
    logger.info("Initialising learn-scraper...")

    ls = LearnScraper()
    res = ls.login(config.USERNAME, config.PASSWORD)

    if config.USE_CACHE and os.path.exists(ls.cache_name):
        ls.load_cache()
        logger.info(
            "Found %s files to download from cache.", len(ls.content_infos),
        )
    else:
        course_urls = ls.get_course_urls(res)
        for url in course_urls:
            ls.get_content_infos(url)
        logger.info(
            "Found %s files by visiting %s folders from %s courses.",
            len(ls.content_infos),
            len(ls.folder_urls),
            len(course_urls),
        )

    if config.USE_CACHE and not os.path.exists(ls.cache_name):
        ls.save_cache()

    ls.download_all()


if __name__ == "__main__":
    main()
