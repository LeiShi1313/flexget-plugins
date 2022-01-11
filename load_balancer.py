# coding=utf-8
from __future__ import unicode_literals, division, absolute_import


import re
import logging
import hashlib
from decimal import Decimal

from builtins import *


from flexget import plugin
from flexget.event import event
from flexget.config_schema import one_or_more

logger = logging.getLogger("load_balancer")


class LoadBalancer(object):
    """
    配置示例
    task1:
        rss:
            url: https://www.example.com/rss.xml
            other_fields:
                - link
        loadbalancer:
            field: link
            divisor: 2
            accept: [0]
    task2:
        rss:
            url: https://www.example.com/rss.xml
            other_fields:
                - link
        loadbalancer:
            field: link
            divisor: 2
            accept: [1]
    """

    schema = {
        "type": "object",
        "properties": {
            "field": {"type": "string"},
            "divisor": {"type": "number"},
            "accept": one_or_more({"type": "number"}),
        },
        "required": ["accept"],
    }

    def prepare_config(self, config):
        config.setdefault("field", "title",)
        config.setdefault("divisor", 2)
        config.setdefault("accept", [])
        self.config = config

    @plugin.priority(999)
    def on_task_filter(self, task, config):
        self.prepare_config(config)

        for entry in task.accepted + task.undecided:
            field = entry.get(self.config["field"])
            if field:
                self.process_entry(task, entry)

    @plugin.priority(120)
    def on_task_modify(self, task, config):
        for entry in task.accepted:
            field = entry.get(self.config["field"])
            if field:
                self.process_entry(task, entry, modify=True)

    def process_entry(self, task, entry, modify=False):
        field = entry.get(self.config["field"])
        if not field:
            logger.debug(
                "Field {} not found in entry, available fields are {}".format(
                    self.config["field"], entry.keys()
                ))
            if not modify:
                return
            field = entry['title']
        if isinstance(field, int) or isinstance(field, float):
            num = int(Decimal(field)) % self.config['divisor']
        else:
            num = int(hashlib.md5(bytes(field, 'utf-8')).hexdigest(), 16) % self.config['divisor']
        if any(num == n for n in self.config['accept']):
            entry.accept()
        else:
            entry.reject()


@event("plugin.register")
def register_plugin():
    plugin.register(LoadBalancer, "loadbalancer", api_ver=2)
