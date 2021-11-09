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

logger = logging.getLogger('douban')


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
        'type': 'object',
        'properties': {
            'cookie': {'type': 'string'},
            'user_agent': {'type': 'string'},
            'ptgen': {'type': 'string'},
            'score': {'type': 'number'},
            'director': one_or_more({'type': 'string'}),
            'cast': one_or_more({'type': 'string'}),
            'writer': one_or_more({'type': 'string'}),
            'genre': one_or_more({'type': 'string'}),
            'language': one_or_more({'type': 'string'}),
            'region': one_or_more({'type': 'string'}),
            'tags': one_or_more({'type': 'string'}),
        },
        'required': ['ptgen']
    }

    def prepare_config(self, config):
        config.setdefault('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36')
        config.setdefault('cookie', None)
        config.setdefault('score', None)
        config.setdefault('director', [])
        config.setdefault('cast', [])
        config.setdefault('writer', [])
        config.setdefault('genre', [])
        config.setdefault('language', [])
        config.setdefault('region', [])
        config.setdefault('tags', [])
        self.config = config


    def on_task_filter(self, task, config):
        self.prepare_config(config)

        adapter = HTTPAdapter(max_retries=5)
        task.requests.mount('http://', adapter)
        task.requests.mount('https://', adapter)
        headers = {'user-agaen': config['user_agent']}
        if config['cookie']:
            headers['cookie'] = config['cookie']
        task.requests.headers.update(headers)

        # futures = []  # 线程任务
        # with concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        #     for entry in task.accepted + task.undecided:
        #         futures.append(executor.submit(self.consider_accept, self, task, entry))
        #         time.sleep(0.5)

        # for f in concurrent.futures.as_completed(futures):
        #     exception = f.exception()
        #     if isinstance(exception, plugin.PluginError):
        #         logger.error(exception)
        for entry in task.accepted + task.undecided:
            self.consider_accept(task, entry)

    def consider_accept(self, task, entry):
        link = entry.get('link')
        if not link:
            raise plugin.PluginError("The rss plugin require 'other_fields' which contain 'link'. "
                                     "For example: other_fields: - link")
        detail_page = task.requests.get(link, timeout=10)
        detail_page.encoding = 'utf-8'

        if 'login' in detail_page.url or 'portal.php' in detail_page.url:
            raise plugin.PluginError("Can't access the site. Your cookie may be wrong!")

        m = re.search(r'(http.*?douban\.com\/subject\/\d+)', detail_page.text)
        if not m:
            logger.warning("Failed to find douban url for entry: {}".format(entry.get('title')))
            return
        
        params = {'url': m.group()}
        ptgen = task.requests.get(self.config['ptgen'], params=params)
        if not ptgen.ok or not ptgen.json().get("success"):
            logger.warning("Failed to get ptgen for entry: {}".format(entry.get('title')))
            return
        douban = ptgen.json()

        if self.config['score']:
            if not ptgen.json().get('douban_rating_average'):
                logger.warning("Douban rating not found for entry: {}".format(entry.get('title')))
                return
            if Decimal(douban.get('douban_rating_average')) < Decimal(self.config['score']):
                entry.reject('Douban rating is lower than {}'.format(self.config['score']), remember=True)
        
        for criteria in ['director', 'cast', 'writer', 'genre', 'language', 'region', 'tags']:
            if self.config.get(criteria):
                if not all(any(c.lower() in str(d).lower() for d in douban.get(criteria)) for c in self.config.get(criteria)):
                    entry.reject('{} not desired'.format(criteria), remember=True)
        
        entry.accept()


@event('plugin.register')
def register_plugin():
    plugin.register(Douban, 'douban', api_ver=2)