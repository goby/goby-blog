# -*- coding: utf-8 -*-
"""
Change file type from markdown to html plugin.

"""
import time

import os
from functools import wraps
from urllib import quote

from hyde.plugin import Plugin
from hyde.site import Site
from hyde.fs import FS, File, Folder

MD_KINK = ['md', 'markdown', 'mkdn', 'mdwn', 'mkd', 'mdown']

class Md2HtmlPlugin(Plugin):
    def __init__(self, site):
        super(Md2HtmlPlugin, self).__init__(site)
        self.deploy_root = self.site.config.deploy_root
        
    def generation_complete(self):
        for node in self.site.content.walk():
            for resource in node.resources:
                f = File(resource)
                if f.kind not in MD_KINK:
                    continue
                self.logger.info(f)
                self.logger.info(resource.full_url)
                    

