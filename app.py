__author__ = 'madalinoprea'

import mc
import xbmc

from datetime import timedelta
import simplejson as json

from vplay.urls import VplayUrls
from vplay.regex import VplayRegex

# See http://developer.boxee.tv/MC_Module

# options of ListItem type property
TV_SHOW = 'TV_SHOW'
TV_SHOW_PAGE = 'TV_SHOW_PAGE'
TV_SEASON = 'TV_SEASON'
TV_EPISODE = 'TV_EPISODE'
HD_VIDEOS_PAGE = 'HD_VIDEOS_PAGE'

# Control IDs
TOP_MENU_LIST_ID = 200
TV_SHOW_MENU_ITEM_ID = 201
LOGIN_BUTTON_ID = 202           # Login/logout button
NAVIGATION_LIST_ID = 120        # Navigation menu
TV_SHOW_IMAGE_ID = 150

class VplayApp(mc.Player):
    MAX_FAILED_LOGIN_COUNT = 3

    def log(self, msg):
        mc.LogInfo('VPLAY: %s' % msg)

    def notify(self, msg):
        self.log('NOTIFICATION %s' % msg)
        mc.ShowDialogNotification(msg)

    def __init__(self):
        mc.Player.__init__(self, True)

        self.http = mc.Http()
        self.r = VplayRegex()
        self.u = VplayUrls()

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
    # TODO: Update this when I'll recover my boxee box
    def is_boxeebox(self):
        return False
#        return self.platform != 'None'

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

    def _login(self):
        # Erase saved credentials
        if self.failed_login_count == self.MAX_FAILED_LOGIN_COUNT:
            self._logout()

        username = self.get_username()
        password = self.get_password()

        if username and password:
            response = self.http.Post(self.u.get_login_url(), self.u.get_login_params(username, password))
            logged_username = self.r.get_username(response)

            if logged_username:
                self.logged_in = True
            else:
                self.failed_login_count = self.failed_login_count + 1
                mc.ShowDialogNotification('Unable to log in.')
                self.logged_in = False

        self.update_login_status()
        return self.logged_in

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
        self.update_login_status()

    def toggle_login(self):
        if self.logged_in:
            self._logout()
        else:
            self._login()

    '''
    Updates UI based on self.logged_in
    '''
    def update_login_status(self):
        button_label = 'Login'
        if self.logged_in:
            button_label = 'Logout %s' % self.username

        mc.GetActiveWindow().GetButton(LOGIN_BUTTON_ID).SetLabel(button_label)

    '''
    Executed at window load, used to update UI elements (set focus, etc)
    '''
    def on_load(self):
        # Update login status, we might already have cookies from previous run
        response = self.http.Get(self.u.get_base_url())
        username = self.r.get_username(response)
        if username:
            self.logged_in = True
            self.update_login_status()

        # Enforce login
        if not self.logged_in:
            self._login()

        # Coming back from player
        list = mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID)
        items = list.GetItems()

        # Load the initial list
        if len(items) == 0 and self.populate_tv_shows:
            self.populate_tv_shows = False
            self.load_tv_shows()

        self.log('Last focused item: %s' % self.last_played_episode)
        # Play the next episode
        if self.GetLastPlayerEvent() == self.EVENT_ENDED:
            # do we have a next episode
            if self.last_played_episode + 1 < len(items):
                list.SetFocusedItem(self.last_played_episode + 1)
                current_item = list.GetItem(self.last_played_episode + 1)
                self.load_next()

                # If current item is nav item, we have to play first item on next page
                if current_item.GetProperty('type') in (HD_VIDEOS_PAGE, ):
                    self.load_next()
            else:
                # only focus last played episode
                list.SetFocusedItem(self.last_played_episode)
        else:
            # Maybe player is in background or user stopped the player
            list.SetFocusedItem(self.last_played_episode)

    def load_tv_shows(self):
        # clear nav list
        items = self.get_tv_shows()
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)
        mc.GetActiveWindow().PushState()

    '''
    Search tv shows
    '''
    def search_tv_shows(self):
        query = mc.ShowDialogKeyboard('Enter search query', '', False)
        items = self.get_tv_shows(query)
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def load_hd_videos(self):
        items = self.get_hd_videos()
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def search_videos(self):
        query = mc.ShowDialogKeyboard('Enter search query', '', False)
        items = self.get_hd_videos(query=query)
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    def load_top50_videos(self):
        items = self.get_top50_videos()
        mc.GetActiveWindow().GetList(NAVIGATION_LIST_ID).SetItems(items)

    '''
    App main controller - handles nav list's clicks
    '''
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
                self.last_played_episode = list.GetFocusedItem()
                self.play_episode(item)
            elif item_type == HD_VIDEOS_PAGE:
                query = item.GetProperty('query')
                page = item.GetProperty('page')
                items = self.get_hd_videos(page, query)
        else:
            # Load default list
            items = self.get_tv_shows()

        if items:
            # save current window state
            mc.GetActiveWindow().PushState()

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
            if query:
                item.SetProperty('query', query)
            items.append(item)

    '''
    Returns a list of tv shows
    '''
    def get_tv_shows(self, search=None, page='1'):
        data = self.http.Get(self.u.get_tv_shows_url(page=int(page), search=search))
        page = int(page)

        items = mc.ListItems()
        for show in self.r.get_tv_shows(data):
            show_item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            show_item.SetLabel(show['title'])
            show_item.SetPath(show['path'])
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
        data = self.http.Get(self.u.get_tv_seasons_url(tv_show_item.GetPath()))
        description = self.r.get_tv_show_description(data)

        items = mc.ListItems()
        for season in self.r.get_tv_seasons(data):
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
        data = self.http.Get(self.u.get_tv_seasons_url(season_item.GetPath()))

        items = mc.ListItems()
        for episode in self.r.get_tv_episodes(data):
            watched = ''
            if episode['watched']:
                watched = '(Watched)'

            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel('%s %s' % (episode['title'], watched))
            item.SetPath(episode['path'])
            item.SetTitle(episode['title'])
            item.SetTVShowTitle(season_item.GetProperty('tv_show'))
            item.SetThumbnail(episode['image'])

            # custom properties
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', season_item.GetProperty('tv_show'))
            item.SetProperty('tv_season', season_item.GetProperty('tv_season'))
            item.SetProperty('tv_show_image', season_item.GetProperty('tv_show_thumb'))

            items.append(item)
        return items

    def get_hd_videos(self, page='1', query=''):
        page = int(page)
        data = self.http.Get(self.u.get_hdvideos_url(page, query))

        items = mc.ListItems()
        for video in self.r.get_videos(data):
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
        self._append_nav(items, page, HD_VIDEOS_PAGE, query)
        return items

    def get_top50_videos(self):
        data = self.http.Get(self.u.get_top50_url())
        items = mc.ListItems()
        for video in self.r.get_top50_videos(data):
            item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
            item.SetLabel(video['title'])
            item.SetPath(video['path'])
            item.SetTitle(video['title'])
            item.SetTVShowTitle(video['title'])
            item.SetThumbnail(video['image'])
            item.SetProperty('type', TV_EPISODE)
            item.SetProperty('tv_show', 'Top50 Videos')
            item.SetProperty('tv_season', '')
            item.SetProperty('tv_show_thumb', video['image'])
            items.append(item)

        return items

    '''
    Converts Vplay subtitle time into sub format
    '''
    def convert_time(self, f):
        return '%s,0' % str(timedelta(seconds=f))

    def _load_subs(self, episode_key, lang='RO'):
        sub_raw_data = self.http.Post(self.u.get_subs_url(), self.u.get_subs_params(episode_key, lang))
        file_path = None

        if sub_raw_data:
            file_path = mc.GetTempDir() + lang + '_' + episode_key + '.sub'
            try:
                sub_data = self.r.get_sub(sub_raw_data)
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
        episode_item.Dump()
        episode_url = self.u.get_tv_episode_url(episode_item.GetPath())
        episode_key = self.r.get_tv_episode_key(episode_url)
        data = self.http.Post(self.u.get_dino_url(), self.u.get_dino_params(episode_key))

        if not len(data):
            self.notify('Unable to contact dino. Please check your login status.')

        dino_data = self.r.get_dino(data)
        self.log('Dino data: %s' % dino_data)

        # Find subtitles
        sub_file_path = None
        selected_lang = None
        available_languages = []
        if dino_data['subs']:
            for lang in json.loads(dino_data['subs']):
                available_languages.append(str(lang))

        self.log('Available languages: %s' % available_languages)
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
            sub_file_path = self._load_subs(episode_key, selected_lang)

        # Create Player Item
        list_item_type = mc.ListItem.MEDIA_VIDEO_CLIP

        # Is this an episode
        if episode_item.GetProperty('tv_season'):
            list_item_type = mc.ListItem.MEDIA_VIDEO_EPISODE

        item = mc.ListItem(list_item_type)
        item.SetPath(dino_data['url'])
        item.SetIcon(dino_data['thumb'])
        item.SetTitle(episode_item.GetTitle())
        item.SetTVShowTitle('%s / %s' % (episode_item.GetTVShowTitle(), episode_item.GetProperty('tv_season')))
        item.SetThumbnail(episode_item.GetProperty('tv_show_thumb'))
        item.SetReportToServer(False)

        self.Play(item)

        if sub_file_path:
             xbmc.sleep(8000)
#             while player.GetLastPlayerAction() != player.EVENT_STARTED:
#                 xbmc.sleep(1000)
             # Hints: http://xbmc.sourceforge.net/python-docs/xbmc.html
             xbmc.Player().setSubtitles(sub_file_path)
