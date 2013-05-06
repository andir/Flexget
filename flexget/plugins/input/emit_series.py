from __future__ import unicode_literals, division, absolute_import
import logging
from flexget.entry import Entry
from flexget.plugin import register_plugin, DependencyError
from flexget.plugins.api_tvrage import lookup_series
from datetime import datetime

log = logging.getLogger('emit_series')
try:
    from flexget.plugins.filter.series import Series, SeriesDatabase
except ImportError as e:
    log.error(e.message)
    raise DependencyError(issued_by='emit_series', missing='series')


class EmitSeries(SeriesDatabase):
    """
    Emit next episode number from all known series.

    Supports only series enumerated by season, episode.
    """

    def validator(self):
        from flexget import validator
        root = validator.factory()
        root.accept('boolean')
        advanced = root.accept('dict')
        advanced.accept('boolean', key='only_aired')
        return root

    def prepare_config(self, config):
        if isinstance(config, bool):
            config = {'only_aired': True}
        return config

    def on_task_input(self, task, config):
        if not config:
            return
        config = self.prepare_config(config)

        entries = []
        for serie in task.session.query(Series).all():
            latest_dlded = self.get_latest_info(serie)
            if latest_dlded is None:
                log.info("Never been downloaded, starting at the begining")
                latest_dlded = {}
                latest_dlded['season'] = 1
                latest_dlded['episode'] = 0    # we ll add one after because we skip the latest downloaded... not elegant :(

            log.info('title %s' % (serie.name))
            serie_info = lookup_series(name=serie.name)
            latest_episode_info = serie_info.latest_episode

            # check if we have seen the latest aired first
            if config['only_aired']:
                if latest_episode_info.number == latest_dlded['episode'] and latest_episode_info.season == latest_dlded['season']:
                    log.info("We have the last aired episode (%s) please be patient." % latest_episode_info)
                    continue
            wanted_episodenum = latest_dlded['episode']+1
            wanted_seasonnum = latest_dlded['season']

            # finished that season let's skip to next one
            if len(serie_info.season(latest_dlded['season']).keys()) < wanted_episodenum:
                wanted_seasonnum += 1
                wanted_episodenum = 1

            wanted_episode_info = serie_info.season(wanted_seasonnum).episode(wanted_episodenum)

            # Check if the episode has aired
            add = True
            if config['only_aired']:
                now = datetime.now()
                if now.date() < wanted_episode_info.airdate:
                    add = False
            if add:
                title = '%s S%02dE%02d' % (serie.name, wanted_seasonnum, wanted_episodenum)
                entries.append(Entry(title=title, url='', serie_rageid=serie_info.showid, serie_name=serie.name, serie_season=wanted_seasonnum, serie_epnumber=wanted_episodenum))
        return entries


register_plugin(EmitSeries, 'emit_series', api_ver=2)
