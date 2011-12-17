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
TOP_MENU_LIST_ID = 200
TV_SHOW_MENU_ITEM_ID = 201
LOGIN_BUTTON_ID = 202           # Login/logout button
NAVIGATION_LIST_ID = 120        # Navigation menu
STATUS_LABEL_ID = 110           # Session status (logged in / logged out)
TV_SHOW_IMAGE_ID = 150

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
        self.last_played_episode = 0
        self.populate_tv_shows = True
        try:
            platform_func = getattr(mc, 'GetPlatform')
            self.platform = platform_func()
        except AttributeError:
            self.platform = 'None'

    # FIXME: See what returns mc.GetPlatform()
    def is_boxeebox(self):
        return self.platform != 'None'

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
        return '%s/in' % self.get_base_url()

    def _login(self):
        # Erase saved credentials
        if self.failed_login_count == self.MAX_FAILED_LOGIN_COUNT:
            self._logout()

        username = self.get_username()
        password = self.get_password()

        if username and password:
            params = 'usr_vplay=%s&pwd=%s&rbm=%s' % (username, password, 1)
            response = self.http.Post(self.get_login_url(), params)
            logged_username = self.get_username_from_page(response)

            if logged_username:
                self.logged_in = True
                return True
            else:
                self.failed_login_count = self.failed_login_count + 1
                mc.ShowDialogNotification('Unable to obtain log in.')

        return False

    '''
    Reset user credentials from local config so that user can re-introduce them.
    '''
    def _logout(self):
        # Reset saved credentials
        config = mc.GetApp().GetLocalConfig()
        config.Reset('username')
        config.Reset('password')
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

        # update UI
        self.update_login_status()

    '''
    Updates UI based on self.logged_in
    '''
    def update_login_status(self):
        button_label = 'Login'
        status_label = 'Logged out'
        if self.logged_in:
            button_label = 'Logout'
            status_label = 'Logged as %s' % self.username

        mc.GetActiveWindow().GetLabel(STATUS_LABEL_ID).SetLabel(status_label)
        mc.GetActiveWindow().GetButton(LOGIN_BUTTON_ID).SetLabel(button_label)

    # Maybe add base url as setting
    def get_base_url(self):
        return self.BASE_URL

    '''
    Executed at window load, used to update UI elements (set focus, etc)
    '''
    def on_load(self):
        #mc.GetActiveWindow().GetControl(TV_SHOW_MENU_ITEM_ID).SetFocus()

        # Update login status, we might already have cookies from previous run
        response = self.http.Get(self.get_base_url())
        username = self.get_username_from_page(response)
        if username:
            self.logged_in = True
            self.update_login_status()
            self.notify('Already authenticated as %s' % username)

        # Enforce login
        if not self.logged_in:
            self._login()

        # Coming back from player, select latest episode played
        list = mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID)
        items = list.GetItems()
        if len(items):
            list.SetFocusedItem(self.last_played_episode)
        elif self.populate_tv_shows:
            self.load_tv_shows()


    def get_tv_shows_url(self, page=1, search=None):
        url = '%s/coll/%s?' % (self.BASE_URL, page)

        if search:
            url = '%s&s=%s' % (url, search)
        return url

    def load_tv_shows(self):
        # clear nav list
        items = self.get_tv_shows()
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)
        mc.GetActiveWindow().PushState()

    '''
    App main controller - handles nav list's clicks
    '''
    def load_next(self):
        # save current window state
        mc.GetActiveWindow().PushState()

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
                self.last_played_episode = list.GetFocusedItem()
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
            self.last_played_episode = 0
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

        if page > 1:
            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel('Prev Page')
            item.SetProperty('type', nav_type)
            item.SetProperty('page', str(page-1))
            item.SetProperty('query', query)
            items.append(item)

    '''
    Returns a list of tv shows
    '''
    def get_tv_shows(self, search=None, page='1'):
        data = self.http.Get(self.get_tv_shows_url(page=page, search=search))
        page = int(page)

        founded = []
        pattern = '<a href="(?P<path>\S+)" title="(?P<title>[^"]+)"><span class="coll_poster" title="([^"]+)" style="background-image:url\((?P<image>\S+)\);">'

        r = re.compile(pattern)
        matches = r.finditer(data)
        for m in matches:
            founded.append(m.groupdict())

        items = mc.ListItems()

        # match[2] Image
        for show in founded:
            show_item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            show_item.SetLabel(show['title'])    # Title
            show_item.SetPath(show['path'])     # Path
            show_item.SetTitle(show['title'])
            show_item.SetTVShowTitle(show['title'])
            show_item.SetThumbnail(show['image'])

            # Custom properties
            show_item.SetProperty('type', TV_SHOW)
            show_item.SetProperty('tv_show', show['title'])

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
        pattern = '<a class="([^"]*)" href="(?P<path>\S+)"><span>(?P<title>[a-zA-Z0-9 ]+)</span>'
        r = re.compile(pattern)

        # retrieve tv show description
        description = ''
        pattern = '''<p>(?P<description>[^<]+)</p>'''
        description_r = re.compile(pattern)
        for match in description_r.finditer(data):
            description = match.group('description')

        items = mc.ListItems()
        for match in r.finditer(data):
            season = match.groupdict()

            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel(season['title'])
            item.SetPath(season['path'])
            item.SetTitle(season['title'])
            item.SetTVShowTitle(tv_show_item.GetTVShowTitle())
            item.SetThumbnail(tv_show_item.GetThumbnail())

            # Set custom
            item.SetProperty('type', TV_SEASON)
            item.SetProperty('tv_show', tv_show_item.GetProperty('tv_show'))
            item.SetProperty('tv_season', season['title'])
#            item.SetProperty('tv_show_thumb', tv_show_item.GetThumbnail())
            item.SetProperty('description', description)

            items.append(item)
        return items

    '''
    Returns a list of episodes for season
    '''
    def get_episodes(self, season_item):
        url = '%s%s' % (self.get_base_url(), season_item.GetPath())
        data = self.http.Get(url)

        pattern = '''<a href="(?P<path>\S+)" title="(?P<full_title>.*)" class="coll-episode-box">
			<span class="thumb" style="background-image:url\((?P<image>\S+)\);"></span>([\s\v]+)<span class="title" title="(?P<title>.*)"(.*)>([\s\v]+)(<span class="(?P<watched>.*)">)?'''
        r = re.compile(pattern)

        items = mc.ListItems()
        for match in r.finditer(data):
            episode = match.groupdict()
            watched = ''
            if episode['watched']:
                watched = '(Watched)'

            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel('%s %s' % (episode['title'], watched))
            item.SetPath(episode['path'])
            item.SetTitle(episode['title'])
            item.SetThumbnail(episode['image'])

            # custom properties
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', season_item.GetProperty('tv_show'))
            item.SetProperty('tv_season', season_item.GetProperty('tv_season'))
            item.SetProperty('tv_show_image', season_item.GetProperty('tv_show_thumb'))

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
        sub_raw_data = self.http.Post(subs_url, params)
        file_path = mc.GetTempDir() + lang + '_' + episode_key + '.sub'

        if sub_raw_data:
            try:
                sub_data = sub_raw_data.strip('&subsData=').rstrip('\n')
                sub_json = json.loads(sub_data)
                file = open(file_path, mode='w+')

                count = 1
                for json_line in sub_json:
                    line = '%d \n%s --> %s\n%s\n\n' % (count,
                                                       self.convert_time(json_line['f']),
                                                       self.convert_time(json_line['t']),
                                                       json_line['s'])

                    line = line.replace('<br>', ' ')
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
        match=re.compile('http://vplay.ro/watch/(.+?)/').findall(episode_url)
        episode_id = match[0]
        url = '%s/play/dinosaur.do' % self.get_base_url()
        params = 'key=%s' % episode_id
        data = self.http.Post(url, params)

        if not len(data):
            self.notify('Unable to contact dino. Please check your login status.')

        # Parse received data
        vals = data.split('&')
        attrs = {}
        for val in vals:
            if len(val) == 0:
                continue
            option = val.split('=')
            attrs[option[0]] = option[1]

        # Find subtitles
        sub_file_path = None
        selected_lang = None
        available_languages = []
        if 'subs' in attrs:
            for lang in json.loads(attrs['subs']):
                available_languages.append(str(lang))

#        self.log('Available languages: %s' % available_languages)
        # Shows select dialog if multiple subtitles are available
        if len(available_languages) > 1:
            # TODO: Test this on BoxeeBox (ShowDialogSelect works only for 1.0)
            if self.is_boxeebox():
                selection = mc.ShowDialogSelect("Please choose subtitle", available_languages)
                selected_lang = str(available_languages[selection])
            else:
                selected_lang = available_languages[0]
        else:
            if len(available_languages) == 1:
                selected_lang = available_languages[0]
        if selected_lang:
            sub_file_path = self._load_subs(episode_id, selected_lang)

        # Create Player Item
        list_item_type = mc.ListItem.MEDIA_VIDEO_CLIP

        # Is this an episode
        if episode_item.GetProperty('tv_season'):
            list_item_type = mc.ListItem.MEDIA_VIDEO_EPISODE

        item = mc.ListItem(list_item_type)
        item.SetPath(attrs['nqURL'])
        item.SetIcon(attrs['th'])
        item.SetTitle(episode_item.GetTitle())
        item.SetTVShowTitle(episode_item.GetTitle())
        item.SetThumbnail(episode_item.GetProperty('tv_show_thumb'))

        mc.GetPlayer().Play(item)

        if sub_file_path:
             xbmc.sleep(2000)
#             while player.GetLastPlayerAction() != player.EVENT_STARTED:
#                 xbmc.sleep(1000)
             # Hints: http://xbmc.sourceforge.net/python-docs/xbmc.html
             xbmc.Player().setSubtitles(sub_file_path)

    '''
    Search tv shows
    '''
    def search_tv_shows(self):
        query = mc.ShowDialogKeyboard('Enter search query', '', False)
        items = self.get_tv_shows(query)
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def search(self, query=None, page='1'):
        page = int(page)
        if not query:
            query = mc.ShowDialogKeyboard('Enter search query', '', False)

        # TODO: search and hd_videos are almost identical
        url = '%s/cat/all/%s/%d' % (self.get_base_url(), query, page)
        data = self.http.Get(url)
        pattern = '<a href="(?P<path>\S+)" class="article" data="(?P<shit>\S+)"><span class="thumbnail"><b>(?P<duration>[0-9:]+)</b><img src="(?P<image>[^"]+)" alt="(?P<title>[^"]+)">'
        r = re.compile(pattern)
        matches = r.finditer(data)

        items = mc.ListItems()
        for match in matches:
            video = match.groupdict()

            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel('%s (%s)' % (video['title'], video['duration']))
            item.SetPath(video['path'])
            item.SetTitle(video['title'])
            item.SetTVShowTitle(video['title'])
            item.SetThumbnail(video['image'])
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', 'Videos')
            item.SetProperty('tv_season', '')
            item.SetProperty('tv_show_thumb', video['image'])
            items.append(item)

        self._append_nav(items, page, SEARCH_PAGE, query)

        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def hd_videos(self, page='1'):
        page = int(page)
        url = '%s/cat/all/%d' % (self.get_base_url(), page)
        data = self.http.Get(url)
        pattern = '<a href="(?P<path>\S+)" class="article" data="(?P<shit>\S+)"><span class="thumbnail"><b>(?P<duration>[0-9:]+)</b><img src="(?P<image>[^"]+)" alt="(?P<title>[^"]+)">'

        r = re.compile(pattern)
        matches = r.finditer(data)

        items = mc.ListItems()
        for match in matches:
            video = match.groupdict()

            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel('%s (%s)' % (video['title'], video['duration']))
            item.SetPath(video['path'])
            item.SetTitle(video['title'])
            item.SetTVShowTitle(video['title'])
            item.SetThumbnail(video['image'])
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', 'Videos')
            item.SetProperty('tv_season', '')
            item.SetProperty('tv_show_thumb', video['image'])
            items.append(item)

        # Add nav buttons
        self._append_nav(items, page, HD_VIDEOS_PAGE)

        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    '''
    Returns username of current session or None if session is not authenticated
    '''
    def get_username_from_page(self, url_response):
        r = re.compile('<a href="/(?P<profile_url>.*?)">Hi, (?P<username>.*)</a>')
        u = r.search(url_response)

        return u.group('username')

