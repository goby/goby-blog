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
from fswrap import File, Folder

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
                target = f.parent.child_file('%s.%s' % (f.name_without_extension, 'html'))
                self.logger.info(target)
                self.logger.info(resource.relative_path)
                self.logger.info(resource.get_relative_deploy_path())
                self.logger.info(type(resource))
                #f.copy_to(target)

                #f.delete()
