#!/usr/bin/env python
# coding:utf-8

import sys
import time
import uuid
import codecs

NEW_TEMPLATE='''---
title: {TITLE}
keywords: {KEYWORDS}
uuid: {UUID}
created: {CREATED}
tags:
 - {TAGS}
---

{# main content #}

{# Local Variables: #}
{# mode: markdown   #}
{# End:             #}
'''

def usage():
    print """ blog.py COMMAND [OPTION]
    COMMAND:
        new -- create new blog
        """
    
    sys.exit(1)
    
def new_blog(config):
    if not hasattr(config, 'date'): config['date'] = time.strftime('%Y-%m-%dT%H:%M:%S+0800')
    if not hasattr(config, 'keywords'): config['keywords'] = ''
    if not hasattr(config, 'uuid'): config['uuid'] = str(uuid.uuid4())
    if not hasattr(config, 'tags'): config['tags'] = ''
    content = NEW_TEMPLATE
    content = content.replace('{TITLE}', config['title'])
    content = content.replace('{KEYWORDS}', config['keywords'])
    content = content.replace('{UUID}', config['uuid'])
    content = content.replace('{TAGS}', config['tags'])
    content = content.replace('{CREATED}', config['date'])
    year = time.strptime(config['date'], '%Y-%m-%dT%H:%M:%S+0800').tm_year
    filename =  'content/cn/%d-%s.html' % (year, config['title'].replace(' ', '-'))
    with codecs.open(filename, 'wc', 'utf-8') as f:
        print >> f, content
    
def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'new':
        title = ' '.join(sys.argv[2:])
        new_blog({'title': title})
    else:
        usage()
    
if __name__ == '__main__':
    main()