# coding=utf-8
from __future__ import unicode_literals, division, absolute_import


import logging
import traceback
from builtins import *


from flexget import plugin
from flexget.event import event
from flexget.config_schema import one_or_more

from autoremovetorrents.task import Task
from autoremovetorrents.logger import Logger

logger = logging.getLogger("auto_remove_torrents")

def register(name):
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.setLevel(logging.INFO)
    return logger
Logger.register = register
Logger.file_handler = logging.NullHandler()
Logger.console_handler = logging.NullHandler()


class AutoRemoveTorrents(object):
    """
    配置示例
    task1:
      auto_remove_torrents:
        client: qbittorrent
        host: http://127.0.0.1:9091
        username: admin
        password: adminadmin
        strategies:
          strategy1:    # Part I: Strategy Name
            categories:
              - IPT
            ratio: 1
            seeding_time: 1209600
          strategy2:
            all_categories: true
            excluded_categories:
              - IPT
            seeding_time: 259200
        delete_data: true
    """

    schema = {
        "type": "object",
        "properties": {
            "client": {"type": "string"},
            "host": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "strategies": one_or_more({"type": "object"}),
            "delete_data": {"type": "boolean"}
        },
        "required": ["client", "host", "username", "password"],
    }

    def prepare_config(self, config):
        config.setdefault("delete_data", False)
        self.config = config

    def on_task_input(self, task, config):
        self.prepare_config(config)

        Logger.file_handler = logging.NullHandler()
        Logger.console_handler = logging.NullHandler()
        Logger.register(__name__)
        Task(task.name, self.config, True).execute()
        return []


@event("plugin.register")
def register_plugin():
    plugin.register(AutoRemoveTorrents, "auto_remove_torrents", api_ver=2)
