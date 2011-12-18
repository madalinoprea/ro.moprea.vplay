__author__ = 'madalinoprea'

import unittest
import urllib2
import random
import json
from cookielib import CookieJar

from vplay.urls import VplayUrls
from vplay.regex import VplayRegex

try:
    from vplay.local_settings import *
except:
    print '''Please create vplay/local_settings.py with this format:
    USERNAME = 'YOUR_VPLAY_USERNAME'
    PASSWORD = 'YOUR_VPLAY_PASSWORD'
    '''
    exit(1)

SEARCH_RESULTS_PER_PAGE = 16
TV_SHOWS_PER_PAGE = 15

class Test(unittest.TestCase):
    def setUp(self):
        self.cookie_jar = CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
        self.u = VplayUrls()
        self.r = VplayRegex()

        # login
        self.opener.open(self.u.get_login_url(), self.u.get_login_params(USERNAME, PASSWORD))

    def test_base_url(self):
        response = self.opener.open(self.u.get_base_url())
        username = self.r.get_username(response.read())
        self.assertEqual(username, USERNAME)

    def test_tv_show_pagination(self):
        page = random.randint(2, 100) # I assume there are more than 100 pages
        response = self.opener.open(self.u.get_tv_shows_url(page))
        print 'TEST SHOW PAGE %s' % page
        data = response.read()
        username = self.r.get_username(data)
        self.assertEqual(username, USERNAME)
        tv_shows = list(self.r.get_tv_shows(data))

        self.assertTrue(tv_shows)
        for tv_show in tv_shows:
            print '%s' % tv_show
        self.assertEqual(len(tv_shows), TV_SHOWS_PER_PAGE) # Pagination currently is set to 15

    def test_tv_show_search(self):
        print 'TEST TV SHOW SEARCH'
        page = random.randint(2, 10)
        query = 'Seinfeld'
        response = self.opener.open(self.u.get_tv_shows_url(page, query))
        data = response.read()
        username = self.r.get_username(data)
        self.assertEqual(username, USERNAME)
        tv_shows = list(self.r.get_tv_shows(data))

        self.assertTrue(tv_shows)
        for tv_show in tv_shows:
            print '%s' % tv_show

    def test_tv_shows(self):
        # choose a random tv show page
        response = self.opener.open(self.u.get_tv_shows_url(random.randint(1, 100)))
        data = response.read()
        tv_shows = list(self.r.get_tv_shows(data))
        self.assertTrue(tv_shows)

        # choose a random tv show
        tv_show = tv_shows[random.randint(0, len(tv_shows)-1)]
        print 'TV Show: %s' % tv_show
        self.assertIn('path', tv_show)
        self.assertIn('title', tv_show)
        self.assertIn('image', tv_show)

        response = self.opener.open(self.u.get_tv_seasons_url(tv_show['path']))
        data = response.read()
        tv_seasons = list(self.r.get_tv_seasons(data))
        self.assertTrue(tv_seasons)

        # Select a random season
        tv_season = tv_seasons[random.randint(0, len(tv_seasons)-1)]
        print 'Random TV Season: %s' % tv_season
        self.assertIn('path', tv_season)
        self.assertIn('title', tv_season)

        response = self.opener.open(self.u.get_tv_seasons_url(tv_season['path']))
        data = response.read()
        tv_episodes = list(self.r.get_tv_episodes(data))
        self.assertTrue(tv_episodes)

        # Select a random episode
        tv_episode = tv_episodes[random.randint(0, len(tv_episodes)-1)]
        print 'Random TV Episode: %s' % tv_episode
        self.assertIn('path', tv_episode)
        self.assertIn('full_title', tv_episode)
        self.assertIn('image', tv_episode)
        self.assertIn('title', tv_episode)
        self.assertIn('watched', tv_episode)

        episode_url = self.u.get_tv_episode_url(tv_episode['path'])
        episode_key = self.r.get_tv_episode_key(episode_url)
        self.assertTrue(episode_key)

        response = self.opener.open(self.u.get_dino_url(), self.u.get_dino_params(episode_key))
        data = response.read()
        self.assertTrue(data, 'Empty response from dino')

        dino = self.r.get_dino(data)
        self.assertIn('url', dino)
        self.assertIn('thumb', dino)
        self.assertIn('subs', dino)

        # Test subtitles if present
        if dino['subs']:
            languages = json.loads(dino['subs'])
            selected_lang = languages[0]
            print 'Subtitle in %s' % selected_lang
            response = self.opener.open(self.u.get_subs_url(), self.u.get_subs_params(episode_key, selected_lang))
            data = response.read()
            sub_data = self.r.get_sub(data)
            self.assertTrue(sub_data)
            # Check if data can be decoded
            sub_json = json.loads(sub_data)

    def test_hdvideos(self):
        page = random.randint(1, 50)
        response = self.opener.open(self.u.get_hdvideos_url(page))
        data = response.read()
        videos = list(self.r.get_videos(data))
        self.assertTrue(videos)

        # select random video
        video = videos[random.randint(0, len(videos)-1)]
        print 'Video: %s' % video
        self.assertIn('path', video)
        self.assertIn('duration', video)
        self.assertIn('image', video)
        self.assertIn('title', video)

    def test_video_search(self):
        page = random.randint(1, 10)
        query = 'funny'
        response = self.opener.open(self.u.get_search_url(query, page))
        data = response.read()

        videos = list(self.r.get_videos(data))
        print 'Videos: %s' % ('\n'.join(['%s' % v for v in videos]))
        self.assertTrue(videos)
        print 'Searching for .. found %d videos on page %d' % (len(videos), page)
        self.assertEqual(len(videos), SEARCH_RESULTS_PER_PAGE)

        # Select random video
        video = videos[random.randint(0, len(videos)-1)]
        print 'Video: %s' % video
        self.assertIn('path', video)
        self.assertIn('duration', video)
        self.assertIn('image', video)
        self.assertIn('title', video)

    def test_top50_videos(self):
        response = self.opener.open(self.u.get_top50_url())
        data = response.read()
        videos = list(self.r.get_top50_videos(data))
        print 'Videos: %s' % ('\n'.join(['%s' % v for v in videos]))
        self.assertTrue(videos)
        self.assertEqual(len(videos), 50)

        # Choose random video
        video = videos[random.randint(0, len(videos)-1)]
        self.assertIn('path', video)
        self.assertIn('image', video)
        self.assertIn('title', video)

if __name__ == '__main__':
    unittest.main()