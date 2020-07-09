# -*- coding: utf-8 -*-

import config
import logging
import os
import re
import requests
import sys
import time

from bs4 import BeautifulSoup
from pprint import pprint as pp

# globals
CONTENT_INFOS = set()
COURSE_INFOS = set()
FOLDER_INFOS = set()
EASE_URL = "https://www.ease.ed.ac.uk/cosign.cgi"
LEARN_URL = "https://www.learn.ed.ac.uk"
CONTENT_REGEX = re.compile("\/bbcswebdav\/.*")
COURSE_REGEX = re.compile(
    "\/webapps\/blackboard\/execute\/launcher" + "\?type=Course&id=([^&]*)&url=([^&]*)"
)
FOLDER_REGEX = re.compile(
    "\/webapps\/blackboard\/content\/listContent\.jsp"
    + "\?course_id=([^&]*)&content_id=([^&]*)"
)

# add logging to console
logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger()
logger.setLevel(config.log_level)


def get_folder_infos(page_link, s):
    logger.debug("Visiting %s", page_link)
    response = send_request(s, page_link, raise_on_error=False)
    soup = BeautifulSoup(response.text, "lxml")

    breadcrumbs = (
        soup.find("div", id="breadcrumbs")
        .find("ol")
        .find_all("span", id=re.compile("crumb_\d+"))
    )
    breadcrumbs = tuple(b.string.strip() for b in breadcrumbs)
    logger.debug("In %s", "/".join(breadcrumbs))

    # keep track of links + path that we have visited
    FOLDER_INFOS.add((breadcrumbs, response.url))

    for folder_html in soup.find_all("a", href=FOLDER_REGEX):
        # all hrefs are supposed to be relative, but some aren't ¯\_(ツ)_/¯
        href = folder_html.get("href").replace(LEARN_URL, "")
        url = LEARN_URL + FOLDER_REGEX.match(href).group(0)

        links = soup.find_all("a", href=CONTENT_REGEX)
        if links:
            dir_path = "contents/" + "/".join(breadcrumbs)
            os.makedirs(dir_path, exist_ok=True)
            CONTENT_INFOS.update((dir_path, link) for link in links)

        # do not visit links that we have already visited
        if any(url in info for info in FOLDER_INFOS):
            continue
        else:
            get_folder_infos(url, s)


def login(s, user, password):
    response = send_request(
        s, LEARN_URL + "/auth-saml/saml/login", params={"apId": "_175_1"}
    )
    soup = BeautifulSoup(response.text, "lxml")

    response = send_request(
        s,
        soup.find("form").get("action"),
        method="POST",
        data={"SAMLRequest": soup.find("input").get("value")},
    )
    soup = BeautifulSoup(response.text, "lxml")

    login_form = soup.find("form", attrs={"method": "post"})
    loginfo = {"login": user, "password": password}
    for key in ["submit", "ref", "service"]:
        loginfo[key] = login_form.findChild("input", attrs={"name": key}).get("value")
    response = send_request(
        s, EASE_URL + login_form.get("action"), method="POST", data=loginfo
    )
    soup = BeautifulSoup(response.text, "lxml")

    response = send_request(
        s,
        soup.find("form").get("action"),
        method="POST",
        data={"SAMLResponse": soup.find("input").get("value")},
    )

    # Load course module tabs, which is populated dynamically.
    data = {
        "action": "refreshAjaxModule",
        "modId": "_4_1",
        "tabId": "_1_1",
        "tab_tab_group_id": "_171_1",
    }
    response = send_request(
        s,
        LEARN_URL + "/webapps/portal/execute/tabs/tabAction",
        method="POST",
        data=data,
    )

    return BeautifulSoup(response.text, "lxml")


def send_request(s, url, method="GET", raise_on_error=True, **kwargs):
    try:
        if method == "GET":
            r = s.get(url, **kwargs)
        elif method == "POST":
            r = s.post(url, **kwargs)
        else:
            raise NotImplementedError("Invalid method: {}".format(method))
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        if raise_on_error:
            raise
        logger.error("%s when trying to access %s - skipping...", e, url)
        return None

    return r


def scrape():
    s = requests.Session()

    start = time.time()

    # logging in to Learn via EASE
    soup = login(s, config.login, config.password)

    logger.info("Successfully logged in to Learn in %ss", time.time() - start)

    start = time.time()

    # find all courses where we are a student
    headers = soup.find_all("h4", string=re.compile("Courses where you are: Student"))
    for header in headers:
        ul = header.find_next_sibling("ul")
        COURSE_INFOS.update(ul.find_all("a", href=COURSE_REGEX))

    logger.info(
        "Found %s courses where you are a student in %ss",
        len(COURSE_INFOS),
        time.time() - start,
    )

    start = time.time()

    for course in COURSE_INFOS:
        url = LEARN_URL + course.get("href").strip()
        get_folder_infos(url, s)

    logger.info(
        "Found %s files by visiting %s paths from %s courses in %ss",
        len(CONTENT_INFOS),
        len(FOLDER_INFOS),
        len(COURSE_INFOS),
        time.time() - start,
    )

    start = time.time()

    for idx, (path, link) in enumerate(CONTENT_INFOS, 1):
        if idx and not idx % 50:
            logger.info("Progress: %s/%s", idx, len(CONTENT_INFOS))
        response = None
        while not response:
            response = send_request(
                s,
                LEARN_URL + link.get("href").replace(LEARN_URL, ""),
                raise_on_error=False,
                timeout=5,
            )
        content_name = response.url.split("/")[-1]
        with open(path + "/" + content_name, "wb") as f:
            f.write(response.content)

    logger.info("Downloaded %s files in %ss", len(CONTENT_INFOS), time.time() - start)

    s.close()
