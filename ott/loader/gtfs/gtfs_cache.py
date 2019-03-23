import os

from ott.utils import gtfs_utils
from ott.utils import file_utils
from ott.utils import object_utils
from ott.utils import web_utils
from ott.utils.cache_base import CacheBase

from ott.loader.gtfs.gtfs_info import GtfsInfo
from ott.loader.gtfs.diff import Diff

import logging
logging.basicConfig()
log = logging.getLogger(__file__)


class GtfsCache(CacheBase):
    """
    Does a 'smart' cache of a gtfs file
         1. it will look to see if a gtfs.zip file is in the cache, and download it and put it in the cache if not
         2. once cached, it will check to see that the file in the cache is the most up to date data...
    """
    feeds = []

    def __init__(self):
        super(GtfsCache, self).__init__(section='gtfs')
        self.feeds = gtfs_utils.get_feeds_from_config(self.config)

    def check_cached_feeds(self, force_update=False):
        """
        will check all feeds from an .ini file
        :return: array of feed names that were updated
        """
        updated_gtfs_names = []
        for f in self.feeds:
            url, name = GtfsCache.get_url_filename(f)
            update = self.check_feed(url, name, force_update)
            if update:
                updated_gtfs_names.append(name)
        return updated_gtfs_names

    def check_feed(self, url, file_name, force_update=False):
        """
        download feed from url, and check it against the cache
        if newer, then replace cached feed .zip file with new version
        """
        # step 1: file name
        file_name = file_name
        file_path = os.path.join(self.cache_dir, file_name)

        # step 2: download new gtfs file
        url = url
        tmp_path = os.path.join(self.tmp_dir, file_name)

        # step 2b: don't keep downloading a file ... make sure the tmp file is at least 2 hours
        if os.path.exists(tmp_path) is False or file_utils.file_age_seconds(tmp_path) > 7200:
            web_utils.wget(url, tmp_path)

        # step 3: check the cache whether we should update or not
        update = force_update
        if not force_update:
            if self.is_fresh_in_cache(file_path):
                log.info("diff {} against cached {}".format(tmp_path, file_path))
                diff = Diff(file_path, tmp_path)
                if diff.is_different():
                    update = True
            else:
                update = True

        # step 4: test new .zip for validity and also
        if update:
            # step 4a: make sure this new .zip feed has a trips.txt, routes.txt and stops.txt file ... if not no update
            if GtfsInfo.feed_looks_valid(tmp_path):
                # step 4b: mv old file to backup then mv new file in tmp dir to cache
                log.info("cp {} to cache {}".format(tmp_path, file_path))
                file_utils.bkup(file_path)
                file_utils.cp(tmp_path, file_path)
            else:
                log.warning("something *WRONG* with file: {}".format(tmp_path))
                update = False

        return update

    def cmp_file_to_cached(self, gtfs_zip_name, cmp_dir):
        """
        returns a Diff object with cache/gtfs_zip_name & cmp_dir/gtfs_zip_name
        """
        cache_path = os.path.join(self.cache_dir, gtfs_zip_name)
        other_path = os.path.join(cmp_dir, gtfs_zip_name)
        diff = Diff(cache_path, other_path)
        return diff

    @classmethod
    def _get_info(cls, gtfs_zip_name, file_prefix=''):
        """
        :return an info object for this cached gtfs feed
        """
        cache_path = os.path.join(cls.get_cache_dir(), gtfs_zip_name)
        ret_val = GtfsInfo(cache_path, file_prefix)
        return ret_val

    @classmethod
    def compare_feed_against_cache(cls, gtfs_feed, app_dir, force_update=False):
        """
        check the ott.loader.gtfs cache for any feed updates
        """
        update_cache = force_update
        try:
            cache = GtfsCache()
            url, name = cache.get_url_filename(gtfs_feed)

            # if we aren't forcing an update, then compare for difference before updating the cache
            if not force_update:
                diff = cache.cmp_file_to_cached(name, app_dir)
                if diff.is_different():
                    update_cache = True

            # update the local cache
            if update_cache:
                cache.cp_cached_file(name, app_dir)
        except Exception as e:
            log.warn(e)
        return update_cache

    @classmethod
    def check_feeds_against_cache(cls, gtfs_feeds, app_dir, force_update=False, filter=None):
        """
        check the ott.loader.gtfs cache for any feed updates
        """
        update_cache = False
        for feed in gtfs_feeds:
            if filter and feed.get('name', 'XXX') not in filter:
                continue
            if GtfsCache.compare_feed_against_cache(feed, app_dir, force_update):
                update_cache = True
        return update_cache

    @classmethod
    def get_url_filename(cls, gtfs_struct):
        url  = gtfs_struct.get('url')
        name = gtfs_struct.get('name', None)
        if name is None:
            name = file_utils.get_file_name_from_url(url)
        return url, name


def main():
    # import pdb; pdb.set_trace()
    cache = GtfsCache()
    cache.check_cached_feeds(force_update=object_utils.is_force_update())


if __name__ == '__main__':
    main()
