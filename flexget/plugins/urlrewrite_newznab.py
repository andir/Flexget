__author__ = 'deksan'

import logging
import feedparser
import urllib

from time import sleep
from datetime import datetime
from flexget import validator
from flexget.entry import Entry
from flexget.plugin import register_plugin, get_plugin_by_name, DependencyError
from flexget.plugins.api_tvrage import lookup_series
from flexget.utils import qualities

log = logging.getLogger('newznab')

try:
    from flexget.plugins.filter.movie_queue import queue_get
except ImportError as e:
    log.error(e.message)
    raise DependencyError(issued_by='urlrewrite_newznab', missing='movie_queue')

try:
    from flexget.plugins.filter.series import Episode
    from flexget.plugins.filter.series import Series
    from flexget.plugins.filter.series import SeriesDatabase
except ImportError as e:
    log.error(e.message)
    raise DependencyError(issued_by='emit_series', missing='series')


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
            wait: 30
        Category is any of: movie, tvsearch, music, book
        wait is time between two api request in seconds (if you don't want to get banned)
        TV Series requires that you inject them with the command inject :
        ./bin/flexget --inject "XXXXXXX.S02E02.mkv" --learn --task tvseries
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

    def on_task_input(self, task, config):
        config = self.build_config(config)
        if config["category"] == "movie":
            return self.get_entries_movie(task, config)
        elif config["category"] == "tvsearch":
            return self.get_entries_tvsearch(task, config)
        else:
            entries = []
            log.warning("Not done yet...")
            return entries

    def get_entries_tvsearch(self, task, config):
        entries = []
        sdb = SeriesDatabase()
        for serie in task.session.query(Series).all():
            log.info("Handling %s" % serie.name)
            latest = sdb.get_latest_download(serie)
            if latest is None:
                log.info("Never been downloaded, starting at the begining")
                latest = Episode()
                latest.season = 1
                latest.number = 0   # we ll add one after because we skip the latest found... not elegant :(
            serie_info = lookup_series(name=serie.name)
            latest_episode_info = serie_info.latest_episode

            #check if we have seen the latest aired first
            if latest_episode_info.number == latest.number and latest_episode_info.season == latest.season:
                log.info("We have the last aired episode (%s) please be patient." % latest_episode_info)
                continue
            wanted_episodenum = latest.number+1
            wanted_seasonnum = latest.season
            log.debug("%s %s" % (len(serie_info.season(latest.season).keys()), wanted_episodenum))
            if len(serie_info.season(latest.season).keys()) < wanted_episodenum:
                wanted_seasonnum += 1
                wanted_episodenum = 1

            wanted_episode_info = serie_info.season(wanted_seasonnum).episode(wanted_episodenum)
            now = datetime.now()
            if (now.date() >= wanted_episode_info.airdate):
                log.info('Searching for %s ' % wanted_episode_info)
                url = config['url'] + "&rid=" + str(serie_info.showid) + "&season=" + str(wanted_episode_info.season) + "&ep=" + str(wanted_episode_info.number)
                log.info("Sleeping %s sec before making our request to %s " % (config['wait'], url))
                sleep(config["wait"])
                rss = feedparser.parse(url)
                status = rss.get('status', False)
                if status != 200:
                    raise log.error('Search result not 200 (OK), received %s' % status)

                if not len(rss.entries):
                    log.info("No results returned")
                for rss_entry in rss.entries:
                    entry = Entry()
                    for key in rss_entry.keys():
                        entry[key] = rss_entry[key]
                    entry["url"] = entry["link"]
                    entries.append(entry)
            #https://www.nmatrix.co.za/api?t=tvsearch&q=game%20of%20thrones&season=2&ep=5
        return entries

    def get_entries_movie(self, task, config):
        entries = []
        quality_plugin = get_plugin_by_name('metainfo_quality')
        for queue_item in queue_get():
            if queue_item.imdb_id:
                imdb_id = queue_item.imdb_id.replace('tt', '')
                log.info('Searching for %s ( %s )' % (imdb_id, queue_item.quality))
                url = config['url'] + "&imdbid=" + imdb_id
                log.info("Sleeping %s sec before making our request to %s " % (config['wait'], url))
                sleep(config["wait"])

                rss = feedparser.parse(url)
                status = rss.get('status', False)
                if status != 200:
                    raise log.error('Search result not 200 (OK), received %s' % status)

                if not len(rss.entries):
                    log.info("No results returned")
                req = qualities.Requirements(queue_item.quality)
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
