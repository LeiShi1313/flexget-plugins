# coding=utf-8
from __future__ import unicode_literals, division, absolute_import


import re
import time
import logging
import multiprocessing
import concurrent.futures
from datetime import datetime
from decimal import Decimal

from builtins import *

from requests.adapters import HTTPAdapter

from flexget import plugin
from flexget.event import event
from flexget.utils.soup import get_soup
from flexget.config_schema import one_or_more
from flexget.utils.tools import parse_timedelta

logger = logging.getLogger("douban")


class Douban(object):
    """
    配置示例
    task_name:
        rss:
            url: https://www.example.com/rss.xml
            other_fields:
                - link
        douban:
            ptgen: https://ptgen.lgto.workers.dev/
            user_agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36
            cookie: 'my_cookie'
            score: 7
            director:
              - Cary Fukunaga
            cast:
              - Daniel Craig
            writer:
              - Neal Purvis
            genre:
              - 动作
              - 爱情
            language:
              - 英语
              - 法语
            region:
              - 美国
              - 英国
            tags:
              - 动作
              - 犯罪
              - 系列
    """

    schema = {
        "type": "object",
        "properties": {
            "cookie": {"type": "string"},
            "user_agent": {"type": "string"},
            "ptgen": {"type": "string"},
            "score": {"type": "number"},
            "director": one_or_more({"type": "string"}),
            "cast": one_or_more({"type": "string"}),
            "writer": one_or_more({"type": "string"}),
            "genre": one_or_more({"type": "string"}),
            "language": one_or_more({"type": "string"}),
            "region": one_or_more({"type": "string"}),
            "tags": one_or_more({"type": "string"}),
            "director_one_of": one_or_more({"type": "string"}),
            "cast_one_of": one_or_more({"type": "string"}),
            "writer_one_of": one_or_more({"type": "string"}),
            "genre_one_of": one_or_more({"type": "string"}),
            "language_one_of": one_or_more({"type": "string"}),
            "region_one_of": one_or_more({"type": "string"}),
            "tags_one_of": one_or_more({"type": "string"}),
        }
    }

    score_regex = re.compile(r"豆瓣\s*评分\s+([\d\.]+)\/10[\s\w]+\<br \/>")
    director_regex = re.compile(r"导\s*演\s(.*?)\<br \/>\n((?:\s{5,}.*?(?:<br \/>\n))*)")
    cast_regex = re.compile(r"(?:主\s*演|演\s*员)\s(.*?)\<br \/>\n((?:\s{5,}.*?(?:<br \/>\n))*)")
    writer_regex = re.compile(r"编\s*剧\s(.*?)\<br \/>\n((?:\s{5,}.*?(?:<br \/>\n))*)")
    genre_regex = re.compile(r"类\s*别\s+([\w\/ ]+)\<br \/>")
    language_regex = re.compile(r"语\s*言\s+([\w\/ ]+)\<br \/>")
    region_regex = re.compile(r"产\s*地\s+([\w\/ ]+)\<br \/>")
    tags_regex = re.compile(r"标\s*签\s+(.*?)\<br \/>")

    def prepare_config(self, config):
        config.setdefault(
            "user_agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        )
        config.setdefault("cookie", None)
        config.setdefault("ptgen", None)
        config.setdefault("score", None)
        config.setdefault("director", [])
        config.setdefault("cast", [])
        config.setdefault("writer", [])
        config.setdefault("genre", [])
        config.setdefault("language", [])
        config.setdefault("region", [])
        config.setdefault("tags", [])
        config.setdefault("director_one_of", [])
        config.setdefault("cast_one_of", [])
        config.setdefault("writer_one_of", [])
        config.setdefault("genre_one_of", [])
        config.setdefault("language_one_of", [])
        config.setdefault("region_one_of", [])
        config.setdefault("tags_one_of", [])
        self.config = config

    def on_task_filter(self, task, config):
        self.prepare_config(config)

        # if no filter condition, earily return
        if not any(
            [
                c in self.config
                for c in [
                    "score",
                    "direcotr",
                    "cast",
                    "writer",
                    "genre",
                    "language",
                    "region",
                    "tags",
                    "direcotr_one_of",
                    "cast_one_of",
                    "writer_one_of",
                    "genre_one_of",
                    "language_one_of",
                    "region_one_of",
                    "tags_one_of",
                ]
            ]
        ):
            return

        adapter = HTTPAdapter(max_retries=5)
        task.requests.mount("http://", adapter)
        task.requests.mount("https://", adapter)
        headers = {"user-agaen": config["user_agent"]}
        task.requests.headers.update(headers)

        for entry in task.accepted + task.undecided:
            self.consider_accept(task, entry)

    def consider_accept(self, task, entry):
        douban = self.parse_detail_page(entry.get("description", ''))

        if not douban and self.config["ptgen"]:
            douban = self.get_ptgen(entry, entry.get("description", ''))

        if not douban and self.config["cookie"] and entry.get("link"):
            headers = {"cookie": self.config["cookie"]}
            task.requests.headers.update(headers)
            detail_page = task.requests.get(entry["link"], timeout=10)
            detail_page.encoding = "utf-8"

            douban = self.parse_detail_page(detail_page.text)

            if not douban and self.config["ptgen"]:
                douban = self.get_ptgen(entry, detail_page.text)
            
        if douban:
            return self.filter_douban(entry, douban)
        

    def filter_douban(self, entry, douban):
        if self.config["score"]:
            if not douban.get("douban_rating_average"):
                logger.warning(
                    "Douban rating not found for entry: {}".format(entry.get("title"))
                )
                return
            if Decimal(douban.get("douban_rating_average")) < Decimal(
                self.config["score"]
            ):
                entry.reject(
                    "Douban rating is lower than {}".format(self.config["score"]),
                    remember=True,
                )

        for criteria in [
            "director",
            "cast",
            "writer",
            "genre",
            "language",
            "region",
            "tags",
            "director_one_of",
            "cast_one_of",
            "writer_one_of",
            "genre_one_of",
            "language_one_of",
            "region_one_of",
            "tags_one_of",
        ]:
            if self.config.get(criteria):
                if criteria.endswith('_one_of'):
                    if not any(
                        any(c.lower() in str(d).lower() for d in douban.get(criteria[:-7], []))
                        for c in self.config.get(criteria)
                    ):
                        entry.reject("{} not desired".format(criteria), remember=True)
                else:
                    if not all(
                        any(c.lower() in str(d).lower() for d in douban.get(criteria, []))
                        for c in self.config.get(criteria)
                    ):
                        entry.reject("{} not desired".format(criteria), remember=True)

        entry.accept()

    def parse_detail_page(self, page):
        page = page.replace("\u3000", " ").replace("\r", "").replace("&nbsp;", " ")
        result = {}
        # parse score
        m = self.score_regex.search(page)
        if m:
            result["douban_rating_average"] = m.groups()[0]

        # parse directors
        m = self.director_regex.search(page)
        if m:
            directors = [m.groups()[0].strip()]
            if len(m.groups()) > 1:
                directors.extend(
                    [d.strip() for d in m.groups()[1].split("<br />\n") if d]
                )
            result["director"] = directors

        # parse cast
        m = self.cast_regex.search(page)
        if m:
            cast = [m.groups()[0].strip()]
            if len(m.groups()) > 1:
                cast.extend([c.strip() for c in m.groups()[1].split("<br />\n") if c])
            result["cast"] = cast

        # parse writer
        m = self.writer_regex.search(page)
        if m:
            writers = [m.groups()[0].strip()]
            if len(m.groups()) > 1:
                writers.extend(
                    [w.strip() for w in m.groups()[1].split("<br />\n") if w]
                )
            result["writer"] = writers

        # parse genre
        m = self.genre_regex.search(page)
        if m:
            result["genre"] = [g.strip() for g in m.groups()[0].split("/")]

        # parse language
        m = self.language_regex.search(page)
        if m:
            result["language"] = [l.strip() for l in m.groups()[0].split("/")]

        # parse region
        m = self.region_regex.search(page)
        if m:
            result["region"] = [r.strip() for r in m.groups()[0].split("/")]

        # parse tags
        m = self.tags_regex.search(page)
        if m:
            result["tags"] = [t.strip() for t in m.groups()[0].split("|")]

        return result

    def get_ptgen(self, entry, page):
        m = re.search(r"(http.*?douban\.com\/subject\/\d+)", page)
        if not m:
            logger.warning(
                "Failed to find douban url for entry: {}".format(entry.get("title"))
            )
            return None

        params = {"url": m.group()}
        ptgen = task.requests.get(self.config["ptgen"], params=params)
        if not ptgen.ok or not ptgen.json().get("success"):
            logger.warning(
                "Failed to get ptgen for entry: {}".format(entry.get("title"))
            )
            return None
        return ptgen.json()


@event("plugin.register")
def register_plugin():
    plugin.register(Douban, "douban", api_ver=2)
