#!/usr/bin/env python
# coding:utf-8

""" Blog helper
"""

import sys
import time
import uuid
import codecs
import argparse

NEW_TEMPLATE = '''---
title: {TITLE}
keywords: {KEYWORDS}
uuid: {UUID}
tags:
 - {TAGS}
---

{# main content #}

{# Local Variables:      #}
{# mode: markdown        #}
{# indent-tabs-mode: nil #}
{# End:                  #}
'''

def _usage():
    print """ blog.py COMMAND [OPTION]
    COMMAND:
        new -- create new blog
        """
    sys.exit(1)

def _new_blog(config):
    if not config.date:
        config.date = time.strftime('%Y-%m-%dT%H:%M:%S+0800')
    config.keyword = ' '.join(config.keyword)
    config.tag = ' '.join(config.tag)
    config.uuid = str(uuid.uuid4())
    content = NEW_TEMPLATE
    content = content.replace('{TITLE}', config.title)
    content = content.replace('{KEYWORDS}', config.keyword)
    content = content.replace('{UUID}', config.uuid)
    content = content.replace('{TAGS}', config.tag)
    content = content.replace('{CREATED}', config.date)
    year = time.strptime(config.date, '%Y-%m-%dT%H:%M:%S+0800').tm_year
    filename = 'content/cn/%d-%s.html' % (year, config.head.replace(' ', '-'))
    with codecs.open(filename, 'wc', 'utf-8') as blogfile:
        blogfile.write(content.encode('utf-8'))

    print filename

def _main():
    parser = argparse.ArgumentParser(prog='blog.py')
    subparse = parser.add_subparsers(title='command',
                                     description='sub commands',
                                     help='')
    # New Blog Sub Command
    new_cmd = subparse.add_parser('new', help='create new command')
    new_cmd.add_argument('title', help='set the article title')
    new_cmd.add_argument('head', help='set the file name')
    new_cmd.add_argument('-d', '--date')
    new_cmd.add_argument('-k', '--keyword', default=[], nargs='+', help='set keywords')
    new_cmd.add_argument('-t', '--tag', default=['tech'], nargs='+', help='set tags')
    new_cmd.set_defaults(func=_new_blog)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    _main()
