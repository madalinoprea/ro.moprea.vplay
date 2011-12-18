__author__ = 'madalinoprea'

import re

class VplayRegex(object):
    def __init__(self):
        # FIXME: Currently titles with " are ignored
        # TV Shows
        self.tv_shows = re.compile('<a href="(?P<path>\S+)" title="(?P<title>[^"]+)"><span class="coll_poster" title="([^"]+)" style="background-image:url\((?P<image>\S+)\);">')
        self.tv_seasons = re.compile('<a class="([^"]*)" href="(?P<path>\S+)"><span>(?P<title>[a-zA-Z0-9 ]+)</span>')
        self.tv_show_description = re.compile('<p>(?P<description>[^<]+)</p>')
        self.tv_episodes = re.compile('''<a href="(?P<path>\S+)" title="(?P<full_title>.*)" class="coll-episode-box">
			<span class="thumb" style="background-image:url\((?P<image>\S+)\);"></span>([\s\v]+)<span class="title" title="(?P<title>.*)"(.*)>([\s\v]+)(?P<watched><span class="watch">)?''')
        self.tv_episode_key = re.compile('http://vplay.ro/watch/(.+?)/')
        self.dino = re.compile('&nqURL=(?P<url>[^&]+)(&subs=(?P<subs>[^&]+))?(&th=(?P<thumb>[^&]+))?')
        self.sub = re.compile('&subsData=(?P<data>.*)')

        # Videos
        self.videos = re.compile('<a href="(?P<path>\S+)" class="article(  last-box-row")?" data="(?P<shit>\S+)"><span class="thumbnail"><b>(?P<duration>[0-9:]+)</b><img src="(?P<image>[^"]+)" alt="(?P<title>[^"]+)">')
        self.username = re.compile('<a href="/(?P<profile_url>[^"]+)">Hi, (?P<username>.*)</a>')

    def get_username(self, data):
        match = self.username.search(data)
        if match:
            return match.group('username')
        else:
            return None

    def get_tv_shows(self, data):
        for match in self.tv_shows.finditer(data):
            yield match.groupdict()

    def get_tv_seasons(self, data):
        for match in self.tv_seasons.finditer(data):
            yield match.groupdict()

    def get_tv_show_description(self, data):
        for match in self.tv_show_description.finditer(data):
            return match.group('description')
        return ''

    def get_tv_episodes(self, data):
        for match in self.tv_episodes.finditer(data):
            yield match.groupdict()

    def get_tv_episode_key(self, url):
        matches = self.tv_episode_key.findall(url)
        if matches:
            return matches[0]
        else:
            return None

    def get_videos(self, data):
        for match in self.videos.finditer(data):
            yield match.groupdict()

    def get_dino(self, data):
        for match in self.dino.finditer(data):
            return match.groupdict()

    def get_sub(self, data):
        match = self.sub.search(data)
        if match:
            return match.groupdict()['data']
        else:
            return None
