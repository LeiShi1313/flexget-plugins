# coding=utf-8
from __future__ import unicode_literals, division, absolute_import


import re
import logging
import hashlib

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

    def on_task_filter(self, task, config):
        self.prepare_config(config)

        for entry in task.accepted + task.undecided:
            self.consider_accept(task, entry)

    def consider_accept(self, task, entry):
        field = entry.get(self.config["field"])
        if not field:
            raise plugin.PluginError(
                "Field {} not found in entry, available fields are {}".format(
                    self.config["field"], entry.keys()
                ))

        num = int(hashlib.md5(bytes(field, 'utf-8')).hexdigest(), 16) % self.config['divisor']
        if any(num == n for n in self.config['accept']):
            entry.accept()


@event("plugin.register")
def register_plugin():
    plugin.register(LoadBalancer, "loadbalancer", api_ver=2)
