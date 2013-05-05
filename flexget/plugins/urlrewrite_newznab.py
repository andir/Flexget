__author__ = 'deksan'

import logging
import feedparser
import urllib

from time import sleep
from flexget import validator
from flexget.entry import Entry
from flexget.plugin import register_plugin

log = logging.getLogger('newznab')


class Newznab(object):
    """
        Newznab urlrewriter
        Provide a url or your webiste + apikey and a category

        movies:
          movie_queue: yes
          newznab:
            url: "http://website/api?apikey=xxxxxxxxxxxxxxxxxxxxxxxxxx&t=movie&extended=1"
            website: https://website
            apikey: xxxxxxxxxxxxxxxxxxxxxxxxxx
            category: movie
            wait: 30
        Category is any of: movie, tvsearch, music, book
        wait is time between two api request in seconds (if you don't want to get banned)


        Example how to use for tv series :
        --------------------------------------------------------------------------------
              tvsearch:
                series:
                  720p+:
                    - Your lovely show 1
                    - Your lovely show 2
                discover:
                  what:
                    - emit_series: yes
                  from:
                    - newznab:
                        website: "http://www.xxxxxx.com/"
                        apikey: "xxxxxxxxxxxxxxxxxxxxxxxxxx"
                        category: tv
                        wait: 3
                make_rss:
                  file: /tmp/output.xml

        Example how to use for movies (queue is set with imdb plugins for example) :
        --------------------------------------------------------------------------------
              moviessearch:
                movie_queue: yes
                discover:
                  what:
                    - emit_movie_queue: yes
                  from:
                    - newznab:
                        website: "http://www.xxxxxx.com/"
                        apikey: "xxxxxxxxxxxxxxxxxxxxxxxxxx"
                        category: movie
                        wait: 3
                make_rss:
                  file: /tmp/output.xml
    """
    def validator(self):
        """Return config validator."""
        root = validator.factory('dict')
        root.accept('url', key='url', required=False)
        root.accept('integer', key='wait', required=False)
        root.accept('url', key='website', required=False)
        root.accept('text', key='apikey', required=False)
        root.accept('choice', key='category', required=True).accept_choices(['movie', 'tvsearch', 'tv', 'music', 'book'])
        return root

    def build_config(self, config):
        if config['category'] == 'tv':
            config['category'] = 'tvsearch'
        log.debug(config['category'])
        if 'wait' not in config:
            config['wait'] = 30
        if 'url' not in config:
            if 'apikey' in config and 'website' in config:
                params = {
                    "t": config['category'],
                    "apikey": config['apikey'],
                    "extended": 1
                }
                config['url'] = config['website']+'/api?'+urllib.urlencode(params)
        log.debug(config['url'])

        return config

    def fill_entries_for_url(self, url, config):
        entries = []
        log.info("Sleeping %s sec before making our request to %s " % (config['wait'], url))
        sleep(config["wait"])

        rss = feedparser.parse(url)
        status = rss.get('status', False)
        if status != 200:
            raise log.error('Search result not 200 (OK), received %s' % status)

        if not len(rss.entries):
            log.info("No results returned")

        for rss_entry in rss.entries:
            new_entry = Entry()
            for key in rss_entry.keys():
                new_entry[key] = rss_entry[key]
            new_entry["url"] = new_entry["link"]
            entries.append(new_entry)
        return entries

    def search(self, entry, comparator, config=None):
        config = self.build_config(config)
        if config["category"] == "movie":
            return self.do_search_movie(entry, comparator, config)
        elif config["category"] == "tvsearch":
            return self.do_search_tvsearch(entry, comparator, config)
        else:
            entries = []
            log.warning("Not done yet...")
            return entries

    def do_search_tvsearch(self, arg_entry, comparator, config=None):
        log.info("Searching for %s" % (arg_entry["title"]))
        # normally this should be used with emit_series who has provided season and episodenumber
        if 'serie_rageid' not in arg_entry or 'serie_name' not in arg_entry or 'serie_season' not in arg_entry or 'serie_epnumber' not in arg_entry:
            return []

        url = config['url'] + "&rid=" + str(arg_entry['serie_rageid']) + "&season=" + str(arg_entry['serie_season']) + "&ep=" + str(arg_entry['serie_epnumber'])
        return self.fill_entries_for_url(url, config)

    def do_search_movie(self, arg_entry, comparator, config=None):
        entries = []
        log.info("Searching for %s (imdbid:%s) " % (arg_entry["title"], arg_entry["imdb_id"]))
        # normally this should be used with emit_movie_queue who has imdbid (i guess)
        if 'imdb_id' not in arg_entry:
            return entries

        imdb_id = arg_entry["imdb_id"].replace('tt', '')
        url = config['url'] + "&imdbid=" + imdb_id
        return self.fill_entries_for_url(url, config)

register_plugin(Newznab, 'newznab', api_ver=2, groups=['search'])
