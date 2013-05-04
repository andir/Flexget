import tvrage.api
import logging
from flexget.utils.database import with_session


log = logging.getLogger('api_tvrage')


@with_session
def lookup_series(name=None, session=None):
    show = tvrage.api.Show(name)
    return show


@with_session
def lookup_season(name=None, seasonnum=None, session=None):
    show = lookup_series(name=name, session=session)
    return show.season(seasonnum)


@with_session
def lookup_episode(name=None, seasonnum=None, episodenum=None, session=None):
    season = lookup_season(name=name, seasonnum=seasonnum, session=session)
    return season.episode(episodenum)


