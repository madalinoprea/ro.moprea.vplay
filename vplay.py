__author__ = 'madalinoprea'

import mc

import simplejson as json


import re
import random

import codecs
import xbmc

# See http://developer.boxee.tv/MC_Module

# options of ListItem type property
TV_SHOW = 'TV_SHOW'
TV_SEASON = 'TV_SEASON'
TV_EPISODE = 'TV_EPISODE'

class Vplay(object):
    BASE_URL = 'http://vplay.ro'

    def log(self, msg):
        mc.LogInfo('VPLAY: %s' % msg)

    def notify(self, msg):
        self.log('NOTIFICATION %s' % msg)
        mc.ShowDialogNotification(msg)

    def __init__(self):
        self.http = mc.Http()

        config = mc.GetApp().GetLocalConfig()
        self.username = config.GetValue('username')
        self.password = config.GetValue('password')

    def get_username(self):
        if not self.username:
            self.username = mc.ShowDialogKeyboard('Enter Username', '', False)
            config = mc.GetApp().GetLocalConfig()
            config.SetValue('username', self.username)

        return self.username

    def get_password(self):
        if not self.password:
            self.password = mc.ShowDialogKeyboard('Enter Password', '', True)
            config = mc.GetApp().GetLocalConfig()
            config.SetValue('password', self.password)

        return self.password

    def get_login_url(self):
        return '%s/login/?rtr=' % self.get_base_url()

    def login(self):
        username = self.get_username()
        password = self.get_password()

        if username and password:
            params = 'username=%s&pwd=%s&remember_me=%s&login=Conectare' % (username, password, 1)
            self.http.Post(self.get_login_url(), params)
            responseCookie = str(self.http.GetHttpHeader('Set-Cookie'))
            self.notify('Response: ' + responseCookie)

            if ('vplay_Q1j') in responseCookie:
                return True
            else:
                mc.ShowDialogNotification('Unable to obtain cookie')
                self.log('Cookie missing')

        return False

    # Maybe add base url as setting
    def get_base_url(self):
        return self.BASE_URL

    def get_tv_shows_url(self, page=0, search=None):
        url = '%s/serials/?page=%s' % (self.BASE_URL, page)

        if search:
            url = '%s&s=%s' % (url, search)
        return url


    def test(self):
        mc.ShowDialogNotification('TEST video..')

    def load_tv_shows(self):
        # clear nav list
        items = self.get_tv_shows()
        mc.GetActiveWindow().GetList(120).SetItems(items)

    def load_next(self):
        list = mc.GetActiveWindow().GetList(120)
        item = list.GetItem(list.GetFocusedItem())
        items = None # items to populate list
        
        if item:
            item_type = item.GetProperty('type')
            if item_type == TV_SHOW:
                items = self.get_seasons(item)
            elif item_type == TV_SEASON:
                # must load season's episodes
                items = self.get_episodes(item)
            elif item_type == TV_EPISODE:
                self.play_episode(item)
        else:
            # Load default list
            items = self.get_tv_shows()

        if items:
            mc.GetActiveWindow().GetList(120).SetItems(items)


    '''
    Returns a list of tv shows
    '''
    def get_tv_shows(self, search=None):
        data = self.http.Get(self.get_tv_shows_url(search=search))

        founded = []
        match = re.compile('<a href="(/serials/browse.do\?sid=[0-9]+)" target="_top" class="group-item"(.+?)title="(.+?)"><img src="(.+?)" width="312" height="103"([ ].?)>(.+?)</a>').findall(data)
        founded = founded + match
        match = re.compile('<a href="(/serials/browse.do\?sid=[0-9]+)" target="_top"  class="group-item"(.+?)title="Seriale Online: (.+?)"><img src="(.+?)" width="312" height="103">(.+?)</a>').findall(data)
        founded = founded + match

        self.log('%s' % match)
        
        items = mc.ListItems()

        # match[2] Image
        for show in founded:
            self.log('Image url: %s' % show[3])

            show_item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            show_item.SetLabel(show[2])    # Title
            show_item.SetPath(show[0])     # Path
            show_item.SetTitle(show[2])
            show_item.SetTVShowTitle(show[2])
            show_item.SetThumbnail(show[3])

            # Custom properties
            show_item.SetProperty('type', TV_SHOW)
            show_item.SetProperty('tv_show', show[2])

            items.append(show_item)
        return items

    '''
    Returns a list of season for tv_show show
    '''
    def get_seasons(self, tv_show_item):
        url = '%s%s' % (self.get_base_url(), tv_show_item.GetPath())
        data = self.http.Get(url)
        match=re.compile('<a href="(\?sid=[0-9]+&ses=([0-9]+)?)"( class="sel")?>(.+?)</a>').findall(data)

        self.log('%s' % match)
        items = mc.ListItems()
        for season in match:
            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel(season[3])
            item.SetPath(season[0])
            item.SetTitle(season[3])
            item.SetTVShowTitle(tv_show_item.GetTVShowTitle())
            item.SetThumbnail(tv_show_item.GetThumbnail())

            # Set custom
            item.SetProperty('type', TV_SEASON)
            item.SetProperty('tv_show', tv_show_item.GetProperty('tv_show'))
            item.SetProperty('tv_season', season[3])
            item.SetProperty('tv_show_thumb', tv_show_item.GetThumbnail())

            items.append(item)
        return items

    '''
    Returns a list of episodes for season
    '''
    def get_episodes(self, season_item):
        url = '%s/serials/browse.do%s' % (self.get_base_url(), season_item.GetPath())
        self.log('Loading url: %s' % url)
        data = self.http.Get(url)
        match=re.compile('<a href="(.+?)" class="serials-item"( style="margin-right: 0;")?><img src="(.+?)" width="160" height="85">( <div class="iswat" title="Watched"><img src="http://i.vplay.ro/ic/tick16.png"></div> )?(.+?)( <div class="isusb" title="Subtitrari">SUB</div>)?</a>').findall(data)

        self.log('Episodes found: %s' % match)

        items = mc.ListItems()
        # path is like /watch/2j21q73j/
        # [2] is image url
        for episode in match:
            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel(episode[4])
            item.SetPath(episode[0])
            item.SetTitle('%s %s %s' % (season_item.GetProperty('tv_show'),
                                        season_item.GetProperty('tv_season'),
                                        episode[4]) )
            item.SetTVShowTitle(season_item.GetTVShowTitle())
            item.SetThumbnail(episode[2])

            # custom properties
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', season_item.GetProperty('tv_show'))
            item.SetProperty('tv_season', season_item.GetProperty('tv_season'))
            item.SetProperty('tv_show_thumb', season_item.GetProperty('tv_show_thumb'))

            items.append(item)
        return items

    def convert_time_to_something(self, f):
        f = int(f)
        def min_and_sec(f):
            if f > 60:
                f_minute = f/60
                f_secunde = f%60
            else:
                f_minute = "00"
                f_secunde = f

            if f_minute < 10:
                f_minute = "0" + str(f_minute)
            if f_secunde < 10:
                f_secunde = "0" + str(f_secunde)
            return str(f_minute) + ":" + str(f_secunde) + ",0"

        if f > 3600:
            hours = f / 3600
            f = f % 3600
            if hours < 10:
                hours = "0" + str(hours)
            else:
                hours = str(hours)
        else:
            hours = "00"

        final = hours + ":" + min_and_sec(f)

        return final

    def _load_subs(self, episode_key, lang='RO'):
        subs_url = '%s/play/subs.do' % self.get_base_url()
        params = 'key=%s&lang=%s' % (episode_key, lang)
        self.log('SUBS URL: %s' % subs_url)
        sub_raw_data = self.http.Post(subs_url, params)
        file_path = mc.GetTempDir() + episode_key + '.sub'

        if sub_raw_data:
            try:
                sub_data = sub_raw_data.strip('&subsData=').rstrip('\n')
                sub_json = json.loads(sub_data)

                self.log('Saving sub to %s' % file_path)
                file = codecs.open(file_path, encoding='utf-8', mode='w+')
                self.lof('File opened')

                count = 1
                for json_line in sub_json:
                    line = '%d\n %s --> %s\n%s\n\n' % (count,
                                                       self.convert_time_to_something(json_line['f']),
                                                       self.convert_time_to_something(json_line['t']),
                                                       json_line['s'])
                    self.log('Line: %s' % line)
                    file.write(line)
                    self.log('Wrote in file')
                    count = count + 1
                file.close()
            except Exception, ex:
                file_path = None
                self.log('Error loading sub: %s' % ex)

        return file_path

    def play_episode(self, episode_item):
        episode_path = episode_item.GetPath()

        episode_url = '%s%s' % (self.get_base_url(), episode_path)
        data = self.http.Get(episode_url)
        self.log('URL: %s' % episode_url)
#        self.log('Data: %s ' % data)
        match=re.compile('http://vplay.ro/watch/(.+?)/').findall(episode_url)
        episode_id = match[0]

        url = '%s/play/dinosaur.do?key=%s&rand=%s' % (self.get_base_url(), episode_id, random.random())
        data = self.http.Get(url)
        #&nqURL=http://sx.io/vpl/s3m/dqnh9k7p.vod:798eb45f9d6c23bd9f6f21b3eaa828e6:4ed2bcf8&subs=["RO","EN","BG","PL"]&th=http://i.vplay.ro/th/dq/dqnh9k7p/0.jpg

        self.log('Data: %s' % data)

        if not len(data):
            self.notify('Unable to contact dino')

        # Parse received data
        vals = data.split('&')
        attrs = {}
        for val in vals:
            if len(val) == 0:
                continue
            option = val.split('=')
            attrs[option[0]] = option[1]

        self.log('Options: %s' % attrs)
        
        video_url = attrs['nqURL']
        self.log('Video: %s' % video_url)

        # Find subtitle
        sub_file_path = self._load_subs(episode_id)

        item = mc.ListItem()
        item.SetPath(attrs['nqURL'])
        item.SetIcon(attrs['th'])
        item.SetTitle(episode_item.GetTitle())
        self.log('Player title: %s' % item.GetTitle())
        item.SetTVShowTitle(episode_item.GetTitle())
        item.SetThumbnail(episode_item.GetProperty('tv_show_thumb'))
        
        mc.GetPlayer().Play(item)

        if sub_file_path:
             xbmc.sleep(3000)
             while (self.GetLastPlayerEvent() != self.EVENT_STARTED):
                 xbmc.sleep(1000)
                 xbmc.Player().setSubtitles(sub_file_path)

    '''
    Search tv shows
    '''
    def search_tv_shows(self):
        self.query = mc.ShowDialogKeyboard('Enter search query', '', False)
        items = self.get_tv_shows(self.query)
        mc.GetActiveWindow().GetList(120).SetItems(items)
        
