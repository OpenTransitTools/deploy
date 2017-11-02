import os
import json
import logging
log = logging.getLogger(__file__)

from ott.utils.cache_base import CacheBase
from ott.loader.solr.solr_add import SolrAdd
from ott.loader.solr.solr_cache import SolrCache

from ott.gbfsdb.stations import Stations


class GbfsCache(CacheBase):
    """ cache GBFS .json files
        @see https://github.com/NABSA/gbfs
    """
    name = None
    feed_url = None
    type = 'bikeshare'

    def __init__(self):
        super(GbfsCache, self).__init__(section='gbfs')
        self.name = self.config.get('name')
        self.feed_url = self.config.get('feed_url')

    def check_feed(self, force_update=False):
        ret_val = True
        stations = Stations(self.feed_url)
        if ret_val:
            ret_val = self.to_solr(stations)
        return ret_val

    @classmethod
    def get_clean_id(cls, station, def_val=-111):
        ''' remove hub_ prefix crap from SOBI ids, etc...
            note that: https://app.socialbicycles.com/map?hub_id=1581 works, but hub_1581 not so much...
        '''
        id = station.get('station_id', def_val)
        if isinstance(id, (str, unicode)):
            id = id.replace('hub_', '')
        return str(id)

    def to_solr(self, stations):
        solr_add = SolrAdd(type=self.type, type_name=self.name)
        for i, s in enumerate(stations.active_stations()):
            #status = s.get('status')
            station = s.get('station')
            id = self.get_clean_id(station, i)
            solr_add.new_doc(id=id, name=station.get('name'))
            solr_add.add_field('address', station.get('address'))
            solr_add.add_lon_lat(station.get('lon'), station.get('lat'))

        #import pdb; pdb.set_trace()
        # doulbe cache the file ... once here, and once over in the SOLR loader
        solr_add.to_file(path=self.cache_dir)
        SolrCache.add_to_cache(solr_add)
        return solr_add
