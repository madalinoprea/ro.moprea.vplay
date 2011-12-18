__author__ = 'madalinoprea'

class VplayUrls(object):
    def __init__(self):
        self._base_url = 'http://vplay.ro'

    def get_base_url(self):
        return self._base_url

    def get_login_url(self):
        return '%s/in' % self.get_base_url()

    def get_login_params(self, username, password):
        return 'usr_vplay=%s&pwd=%s&rbm=%s' % (username, password, 1)

    def get_tv_shows_url(self, page=1, search=None):
        url = '%s/coll/%d?' % (self.get_base_url(), page)

        if search:
            url = '%s&s=%s' % (url, search)
        return url

    def _build_abs_url(self, path):
        return '%s%s' % (self.get_base_url(), path)

    def get_tv_seasons_url(self, season_path):
        return self._build_abs_url(season_path)

    def get_tv_episode_url(self, video_path):
        return self._build_abs_url(video_path)

    def get_subs_url(self):
        return '%s/play/subs.do' % self.get_base_url()

    def get_subs_params(self, episode_key, language):
        return 'key=%s&lang=%s' % (episode_key, language)

    def get_dino_url(self):
        return '%s/play/dinosaur.do' % self.get_base_url()

    def get_dino_params(self, episode_key):
        return 'key=%s' % episode_key

    def get_search_url(self, query, page=1):
        return '%s/cat/all/%s/%d' % (self.get_base_url(), query, page)

    def get_hdvideos_url(self, page=1):
        return  '%s/cat/all/%d' % (self.get_base_url(), page)

    def get_top50_url(self):
        return '%s/top50' % self.get_base_url()

if __name__ == '__main__':
    u = VplayUrls()
    print 'Base Url: %s' % u.get_base_url()
    print 'Login Url: %s' % u.get_login_url()
    print 'Login Params: %s' % u.get_login_params('user', 'password')

    print 'TV Shows Url: %s' % u.get_tv_shows_url()
    print 'TV Shows Search: %s' % u.get_tv_shows_url(search='Seinfeld')
    print 'TV Shows Next page: %s' % u.get_tv_shows_url(page=3)
    print 'Sub urls: %s' % u.get_subs_url()
    print 'Sub params: %s' % u.get_subs_params('episode_key', 'RO')
    print 'Dino url: %s' % u.get_dino_url()
    print 'Dino params: %s' % u.get_dino_params('episode_key')

    print 'Search url: %s' % u.get_search_url('bucuresti', 3)
    print 'HD Videos url: %s' % u.get_hdvideos_url(3)
    print 'Top50 url: %s' % u.get_top50_url()




