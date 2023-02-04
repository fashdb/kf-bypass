import logging
import re
from hashlib import sha256
from http.cookiejar import CookieJar, Cookie
from random import random
from dateutil.parser import parse

import requests


def solve(salt, diff, position):
    # Assume that diff is a multiple of 4...
    prefix = "0" * (diff // 4)

    while True:
        h = sha256((salt + str(position)).encode()).hexdigest()

        if h.startswith(prefix):
            return position

        position += 1


def cookie_from_string(text: str, domain: str) -> Cookie:
    parts = [t.strip() for t in text.split(";")]

    name, value = parts[0].split("=")

    path = None
    expires = None

    for tok in parts[1:]:
        k, v = tok.split("=")
        if k == "path":
            path = v
        if k == "expires":
            expires = parse(v).timestamp()

    return Cookie(
        version=0,
        name=name, value=value,
        port=None, port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=False,
        path=path, path_specified=path is not None,
        secure=False,
        expires=expires,
        comment=None,
        comment_url=None,
        rfc2109=False
    )


class Scraper:

    def __init__(self, headers=None, proxies=None, logger=None):
        self._session = requests.session()
        self._session.cookies = CookieJar()
        self.logger = logger

        if headers:
            self._session.headers = headers
        if proxies:
            self._session.proxies = proxies

    def _get(self, url, **kwargs):
        return self._session.get(url, **kwargs)

    def get(self, url, **kwargs):
        r = self._get(url, **kwargs)

        if Scraper._is_challenge_page(r):
            challenge_params = Scraper._get_params(r)
            if self.logger:
                self.logger.debug(f"challenge params: {challenge_params}")

            challenge_response = solve(**challenge_params)
            if self.logger:
                self.logger.debug(f"challenge response: {challenge_response}")

            r2 = self._get(
                f"https://kiwifarms.net/.sssg/api/{challenge_params['salt']}?{challenge_response}"
            )
            if r2.json()["auth"]:

                clearance = r2.json()["auth"]

                if self.logger:
                    self.logger.info(f"Solve challenge, clearance cookie: {clearance}")

            else:
                self.logger.error(f"Could not solve challenge: {r2.text}")

            return self.get(url, **kwargs)

        return r

    @staticmethod
    def _is_challenge_page(r):
        if "Checking your browser before accessing kiwifarms.net" in r.text \
                and r.text.startswith('<!DOCTYPE html>\r\n<html class="no-js">\r\n\r\n<head>\r\n    <title>Just a moment...</title>\r\n'):
            return True
        return False

    @staticmethod
    def _get_params(r):
        param_str = re.search(r"window\.sssg_challenge\(([^)]*)\);", r.text).group(1)

        salt, diff, patience = param_str.split(",")
        salt = salt.strip("\" ")
        diff = int(diff)

        return {
            "salt": salt,
            "diff": diff,
            "position": 4503599627370496 * random()
        }
