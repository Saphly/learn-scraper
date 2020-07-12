import grequests
import logging
import os
import pickle
import re
import requests
import urllib.parse

from bs4 import BeautifulSoup

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
        self.learn_url = "https://www.learn.ed.ac.uk"
        self.ease_url = "https://www.ease.ed.ac.uk"
        self.content_infos = set()
        self.folder_infos = set()

    def _send_request(
        self, url, method="GET", raise_on_error=True, is_soup=True, **kwargs
    ):
        """Wrapper for requests HTTP methods with error handling and optional bs4 conversion.

        Args:
            url (str): URL to send HTTP request to.
            method (str, optional): HTTP request method. Defaults to "GET".
            raise_on_error (bool, optional): logs a warning to console instead of raising if False. Defaults to True.
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
            if raise_on_error:
                logger.exception("%s when trying to access %s.", e, url)
            else:
                logger.warning("%s when trying to access %s - skipping...", e, url)
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
            f"{self.learn_url}/auth-saml/saml/login", params={"apId": "_175_1"}
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
        res = self._send_request(f"{self.ease_url}{rel_url}", method="POST", data=data)

        rel_url = res.find("form", class_="clearfix").get("action")
        data = {"password": password}
        for key in ["login", "ref", "service", "submit"]:
            data[key] = res.find(id=key).get("value")
        res = self._send_request(f"{self.ease_url}{rel_url}", method="POST", data=data)

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
            f"{self.learn_url}/webapps/portal/execute/tabs/tabAction",
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
            url (str): course page url.
        """
        logger.debug("Visiting %s", url)

        r = self._send_request(url, is_soup=False, raise_on_error=False)
        res_url, res = r.url, BeautifulSoup(r.text, "lxml")

        breadcrumbs = (
            res.find(id="breadcrumbs")
            .find("ol", class_="clearfix")
            .find_all("span", id=re.compile(r"crumb_\d+"))
        )
        breadcrumbs = tuple(b.string.strip() for b in breadcrumbs)
        logger.debug("Currently in %s", "/".join(breadcrumbs))

        # keep track of links + paths that we have visited
        self.folder_infos.add((breadcrumbs, res_url))

        for folder in res.find_all("a", href=config.FOLDER_REGEX):
            # all hrefs are supposed to be relative, but some aren't ¯\_(ツ)_/¯
            href = folder.get("href").replace(self.learn_url, "")
            rel_url = config.FOLDER_REGEX.match(href).group(0)
            abs_url = f"{self.learn_url}{rel_url}"

            contents = res.find_all("a", href=config.CONTENT_REGEX)
            if contents:
                dir_path = f"{config.DOWNLOAD_DIR}/contents/{'/'.join(breadcrumbs)}"
                os.makedirs(dir_path, exist_ok=True)
                # all hrefs are supposed to be relative, but some aren't ¯\_(ツ)_/¯
                self.content_infos.update(
                    (dir_path, content.get("href").replace(self.learn_url, ""))
                    for content in contents
                )

            if any(abs_url in info for info in self.folder_infos):
                continue
            else:
                self.get_content_infos(abs_url)

    def download_one(self, dir_path, rel_url):
        """Downloads a specified file and saves it to the specified directory.

        Args:
            dir_path (str): directory to save the downloaded file to.
            rel_url (str): relative URL where the file can be downloaded from.
        """
        content_url = f"{self.learn_url}{rel_url}"
        if r := self._send_request(content_url, is_soup=False, raise_on_error=False):
            fname = urllib.parse.unquote(r.url.split("/")[-1])
            with open(f"{dir_path}/{fname}", "wb") as handler:
                handler.write(r.content)

    def download_all(self):
        """Download all files found in `self.content_infos` in a multi-threaded fashion.
        """
        exception_handler = lambda r, e: logger.warning(
            "%s when trying to access %s - skipping...", e, r.url
        )
        content_infos = {
            f"{self.learn_url}{rel_url}": dir_path
            for dir_path, rel_url in self.content_infos
        }
        reqs = [grequests.get(url) for url in content_infos]

        rs = [r for r in grequests.imap(reqs, exception_handler=exception_handler) if r]
        for r in rs:
            req_url = r.history[0].url if r.history else r.url
            fname = urllib.parse.unquote(r.url.split("/")[-1])
            dir_path = content_infos[req_url]
            with open(f"{dir_path}/{fname}", "wb") as handler:
                handler.write(r.content)

    def save(self):
        """Saves file url and directory path metadata to a cache.
        """
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        logger.info("Saving content_infos...")
        with open(f"{config.CACHE_DIR}/content_infos.pickle", "wb") as handle:
            pickle.dump(self.content_infos, handle, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("Saved content_infos.")

    def load(self):
        """Loads file url and directory path from cache.
        """
        logger.info("Loading content_infos...")
        with open(f"{config.CACHE_DIR}/content_infos.pickle", "rb") as handle:
            self.content_infos = pickle.load(handle)
        logger.info("Loaded content_infos.")


def main():
    logger.info("Initialising learn-scraper...")

    ls = LearnScraper()
    res = ls.login(config.USERNAME, config.PASSWORD)

    if config.USE_CACHE and os.path.exists(f"{config.CACHE_DIR}/content_infos.pickle"):
        ls.load()
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
            len(ls.folder_infos),
            len(course_urls),
        )
        if config.USE_CACHE:
            ls.save()

    for idx, (dir_path, rel_url) in enumerate(ls.content_infos, 1):
        if not idx % 50:
            logger.info("Progress: %s/%s", idx, len(ls.content_infos))
        ls.download_one(dir_path, rel_url)


if __name__ == "__main__":
    main()
