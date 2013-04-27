__author__ = 'deksan'

import logging
import feedparser

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

    def validator(self):
        """Return config validator."""
        root = validator.factory('dict')
        root.accept('url', key='url', allow_replacement=True)
        root.accept('choice', key='category').accept_choices(['all', 'movies', 'tv', 'music', 'books', 'xxx', 'other'])
        return root

    def on_task_input(self, task, config):
        if config["category"] == "movies":
            return self.on_task_input_movies(task, config)
        else:
            entries = []
            log.warning("Not done yet...")
            return entries

    def on_task_input_movies(self, task, config):
        entries = []
        quality_plugin = get_plugin_by_name('metainfo_quality')
        for queue_item in queue_get():
            if queue_item.imdb_id:
                imdb_id = queue_item.imdb_id.replace('tt', '')
                log.info('Searching for %s ( %s )' % (imdb_id, queue_item.quality ))
                url = config['url'] + "&imdbid=" + imdb_id
                log.info(url)
                rss = feedparser.parse(url)
                status = rss.get('status', False)
                if status != 200:
                    raise PluginWarning('Search result not 200 (OK), received %s' % status)

                req = quals.Requirements(queue_item.quality)
                for rss_entry in rss.entries:
                    entry = Entry()
                    for key in rss_entry.keys():
                        entry[key] = rss_entry[key]
                    entry["url"] = entry["link"]
                    entry.register_lazy_fields(['quality'], quality_plugin.instance.lazy_loader)
                    if req.allows(entry['quality']):
                        log.info('{%s} {%s}' % (entry['quality'], entry['title']))
                        entries.append(entry)
                    # todo : add newznab attributes such as size

        return entries

    def search(self, query, comparator, config=None):
        comparator.set_seq1(query)
        log.info("Helloooooo")
        log.info(config['url'])
        log.info(config['category'])
        log.info("Looping")
        log.info(query)

register_plugin(Newznab, 'newznab', api_ver=2)
