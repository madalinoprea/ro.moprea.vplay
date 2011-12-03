__author__ = 'madalinoprea'

import mc

import simplejson as json


import re
import random
from datetime import timedelta

import xbmc

# See http://developer.boxee.tv/MC_Module

# options of ListItem type property
TV_SHOW = 'TV_SHOW'
TV_SHOW_PAGE = 'TV_SHOW_PAGE'
TV_SEASON = 'TV_SEASON'
TV_EPISODE = 'TV_EPISODE'
SEARCH_PAGE = 'SEARCH_NEXT_PAGE'
HD_VIDEOS_PAGE = 'HD_VIDEOS_PAGE'

# Control IDs
LOGIN_BUTTON_ID = 202           # Login/logout button
NAVIGATION_LIST_ID = 120        # Navigation menu
STATUS_LABEL_ID = 110           # Session status (logged in / logged out)

class Vplay(object):
    BASE_URL = 'http://vplay.ro'
    MAX_FAILED_LOGIN_COUNT = 3

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
        self.logged_in = False
        self.failed_login_count = 0

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

    def _login(self):
        # Erase saved credentials
        if self.failed_login_count == self.MAX_FAILED_LOGIN_COUNT:
            self._logout()

        username = self.get_username()
        password = self.get_password()

        if username and password:
            params = 'username=%s&pwd=%s&remember_me=%s&login=Conectare' % (username, password, 1)
            self.http.Post(self.get_login_url(), params)
            responseCookie = str(self.http.GetHttpHeader('Set-Cookie'))
            self.notify('Response: ' + responseCookie)

            if ('vplay_Q1j') in responseCookie:
                self.logged_in = True
                return True
            else:
                self.failed_login_count = self.failed_login_count + 1
                mc.ShowDialogNotification('Unable to obtain cookie')
                self.log('Cookie missing')

        return False

    '''
    Reset user credentials from local config so that user can re-introduce them.
    '''
    def _logout(self):
        # Reset saved credentials
        config = mc.GetApp().GetLocalConfig()
        config.SetValue('username', '')
        config.SetValue('password', '')
        self.username = ''
        self.password = ''

        # Reset http object (hopefully it will erase any saved cookies
        self.http.Reset()
        self.logged_in = False
        self.failed_login_count = 0

    def toggle_login(self):
        if self.logged_in:
            self._logout()
        else:
            self._login()

        # update text
        button_label = 'Login'
        status_label = 'Logged out'
        # login might fail, we check again
        if self.logged_in:
            button_label = 'Logout'
            status_label = 'Logged as %s' % self.username

        mc.GetActiveWindow().GetLabel(STATUS_LABEL_ID).SetLabel(status_label)
        mc.GetActiveWindow().GetButton(LOGIN_BUTTON_ID).SetLabel(button_label)


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
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def load_next(self):
        list = mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID)
        item = list.GetItem(list.GetFocusedItem())
        items = None # items to populate list
        
        if item:
            item_type = item.GetProperty('type')
            if item_type == TV_SHOW:
                items = self.get_seasons(item)
            elif item_type == TV_SHOW_PAGE:
                page = item.GetProperty('page')
                items = self.get_tv_shows(page=page)
            elif item_type == TV_SEASON:
                # must load season's episodes
                items = self.get_episodes(item)
            elif item_type == TV_EPISODE:
                self.play_episode(item)
            elif item_type == SEARCH_PAGE:
                query = item.GetProperty('query')
                page = item.GetProperty('page')
                self.search(query, page)
            elif item_type == HD_VIDEOS_PAGE:
                page = item.GetProperty('page')
                items = self.hd_videos(page)
        else:
            # Load default list
            items = self.get_tv_shows()

        if items:
            self.notify('List updated.')
            mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)


    '''
    Inserts Next Page and Prev Page buttons

    nav_type    one of this values: TV_SHOW_PAGE, HD_VIDEOS_PAGE, SEARCH_PAGE
    query       Used for Search
    '''
    def _append_nav(self, items, page, nav_type, query=''):
        # append back button
        item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
        item.SetLabel('Next Page')
        item.SetProperty('type', nav_type)
        item.SetProperty('page', str(page+1))
        item.SetProperty('query', query)
        items.append(item)

        if page:
            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel('Prev Page')
            item.SetProperty('type', nav_type)
            item.SetProperty('page', str(page-1))
            item.SetProperty('query', query)
            items.append(item)

    '''
    Returns a list of tv shows
    '''
    def get_tv_shows(self, search=None, page='0'):
        data = self.http.Get(self.get_tv_shows_url(page=page, search=search))
        page = int(page)

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

        # append navigation
        self._append_nav(items, page, TV_SHOW_PAGE)

        return items

    '''
    Returns a list of seasons for tv_show show
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

    '''
    Converts Vplay subtitle time into sub format
    '''
    def convert_time(self, f):
        return '%s,0' % str(timedelta(seconds=f))

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
                file = open(file_path, mode='w+')

                count = 1
                for json_line in sub_json:
                    line = '%d\n%s --> %s\n%s\n\n' % (count,
                                                       self.convert_time(json_line['f']),
                                                       self.convert_time(json_line['t']),
                                                       json_line['s'])
                    file.write(line.encode('utf-8'))
                    count = count + 1
                file.close()
            except Exception, ex:
                file_path = None
                self.log('Error saving sub: %s' % ex)

        return file_path

    def play_episode(self, episode_item):
        episode_path = episode_item.GetPath()

        episode_url = '%s%s' % (self.get_base_url(), episode_path)
        data = self.http.Get(episode_url)
        self.log('URL: %s' % episode_url)
        match=re.compile('http://vplay.ro/watch/(.+?)/').findall(episode_url)
        episode_id = match[0]

        url = '%s/play/dinosaur.do?key=%s&rand=%s' % (self.get_base_url(), episode_id, random.random())
        data = self.http.Get(url)
        #&nqURL=http://sx.io/vpl/s3m/dqnh9k7p.vod:798eb45f9d6c23bd9f6f21b3eaa828e6:4ed2bcf8&subs=["RO","EN","BG","PL"]&th=http://i.vplay.ro/th/dq/dqnh9k7p/0.jpg

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

        video_url = attrs['nqURL']

        # Find subtitle
        sub_file_path = self._load_subs(episode_id)
        self.log('Subtitle saved to %s' % sub_file_path)

        item = mc.ListItem()
        item.SetPath(attrs['nqURL'])
        item.SetIcon(attrs['th'])
        item.SetTitle(episode_item.GetTitle())
        item.SetTVShowTitle(episode_item.GetTitle())
        item.SetThumbnail(episode_item.GetProperty('tv_show_thumb'))
        
        mc.GetPlayer().Play(item)

        if sub_file_path:
             xbmc.sleep(3000)
#             while (self.GetLastPlayerEvent() != self.EVENT_STARTED):
#                 xbmc.sleep(1000)
             xbmc.Player().setSubtitles(sub_file_path)

    '''
    Search tv shows
    '''
    def search_tv_shows(self):
        query = mc.ShowDialogKeyboard('Enter search query', '', False)
        items = self.get_tv_shows(query)
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def search(self, query=None, page='0'):
        page = int(page)
        if not query:
            query = mc.ShowDialogKeyboard('Enter search query', '', False)
            
        url = '%s/search?q=%s&page=%d' % (self.get_base_url(), query, page)
        data = self.http.Get(url)
        matches = re.compile('<a href="(/watch/.*?/)" class="vbox-th"><img src="(.*?)" width="168" height="96" alt="(.*?)"').findall(data)

        self.log('Videos: %s' % matches)
        items = mc.ListItems()
        
        # match[0] = path, match[1] = img url , match[2] = title
        for video in matches:
            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel(video[2])
            item.SetPath(video[0])
            item.SetTitle(video[2])
            item.SetTVShowTitle(video[2])
            item.SetThumbnail(video[1])
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', 'Videos')
            item.SetProperty('tv_season', '')
            item.SetProperty('tv_show_thumb', video[1])
            items.append(item)

        self._append_nav(items, page, SEARCH_PAGE, query)

        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def hd_videos(self, page='0'):
        page = int(page)
        url = '%s/hd_music/?page=%d' % (self.get_base_url(), page)
        data = self.http.Get(url)
        matches = re.compile('<a href="(/watch/.*?/)" class="vbox-th"><img src="(.*?)" width="168" height="96" alt="(.*?)"').findall(data)

        self.log('HD Videos: %s' % matches)
        items = mc.ListItems()

        # match[0] = path, match[1] = img url , match[2] = title
        for video in matches:
            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel(video[2])
            item.SetPath(video[0])
            item.SetTitle(video[2])
            item.SetTVShowTitle(video[2])
            item.SetThumbnail(video[1])
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', 'Videos')
            item.SetProperty('tv_season', '')
            item.SetProperty('tv_show_thumb', video[1])
            items.append(item)

        # Add nav buttons
        self._append_nav(items, page, HD_VIDEOS_PAGE)

        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

