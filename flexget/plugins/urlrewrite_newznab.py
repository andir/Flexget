__author__ = 'deksan'

import logging
import feedparser
import urllib, urllib2, urlparse, httplib

from flexget import validator
from flexget.entry import Entry
from flexget.plugin import register_plugin, get_plugin_by_name, PluginWarning, DependencyError
import flexget.utils.qualities as quals

try:
    from flexget.plugins.filter.movie_queue import queue_get
except ImportError:
    raise DependencyError(issued_by='urlrewrite_newznab', missing='movie_queue')

log = logging.getLogger('newznab')


class Newznab(object):
    """
        Newznab urlrewriter
        Provide a url or your webiste + apikey
        

        movies:
          movie_queue: yes
          newznab:
            url: "http://website/api?apikey=xxxxxxxxxxxxxxxxxxxxxxxxxx&t=movie&extended=1"
            website: https://website
            apikey: xxxxxxxxxxxxxxxxxxxxxxxxxx
            category: movie
          
        Category is any of: movie, tvsearch, music, book
    """
    def validator(self):
        """Return config validator."""
        root = validator.factory('dict')
        root.accept('url', key='url', required=False)
        root.accept('url', key='website', required=False)
        root.accept('text', key='apikey', required=False)
        root.accept('choice', key='category', required=True).accept_choices(['movie', 'tvsearch', 'tv', 'music', 'book'])
        return root

    def build_config(self,config):
        if ( config['category'] == 'tv'):
            config['category'] = 'tvsearch'
        if ( 'url' not in config ):
            if ( 'apikey' in config and 'website' in config ):
                params = {
                    "t":config['category'],
                    "apikey": config['apikey'],
                    "extended": 1
                }
                config['url']=config['website']+'/api?'+urllib.urlencode(params)
        return config

    def on_task_input(self, task, config):
        config = self.build_config(config)
        if config["category"] == "movie":
            return self.on_task_input_movie(task, config)
        elif config["category"] == "tvsearch":
            return self.on_task_input_tvsearch(task, config)
        else:
            entries = []
            log.warning("Not done yet...")
            return entries

    def on_task_input_tvsearch(self, task, config):
        entries = []
        
        return entries

    def on_task_input_movie(self, task, config):
        entries = []
        quality_plugin = get_plugin_by_name('metainfo_quality')
        for queue_item in queue_get():
            if queue_item.imdb_id:
                imdb_id = queue_item.imdb_id.replace('tt', '')
                log.info('Searching for %s ( %s )' % (imdb_id, queue_item.quality ))
                url = config['url'] + "&imdbid=" + imdb_id
                log.debug(url)

                try:
                    data = urllib2.urlopen(url, timeout=20).read()
                except urllib2.URLError, e:
                    logger.warn('Error fetching data from newznab provider: %s' % e)
                    data = False

                if data:
                    rss = feedparser.parse(data)

                    if not len(rss.entries):
                        log.info("No results returned")
                    req = quals.Requirements(queue_item.quality)
                    for rss_entry in rss.entries:
                        entry = Entry()
                        for key in rss_entry.keys():
                            entry[key] = rss_entry[key]
                        entry["url"] = entry["link"]
                        entry.register_lazy_fields(['quality'], quality_plugin.instance.lazy_loader)
                        if req.allows(entry['quality']):
                            log.debug('{%s} {%s}' % (entry['quality'], entry['title']))
                            entries.append(entry)
                        else:
                            log.debug('refused quality {%s} {%s}' % (entry['quality'], queue_item.quality))
                        
                        # todo : add newznab attributes such as size

        return entries

   

register_plugin(Newznab, 'newznab', api_ver=2)
