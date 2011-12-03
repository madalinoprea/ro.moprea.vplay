
# Description
Boxee app to browse easier video sharing site http://vplay.ro

Current status: alpha (don't be fulled by version number)

## TODO
 - Add navigation buttons for series and episodes (Back to TV Show, Back to Series)

## Release Notes

### Version 1.5
 - Loads subtitles available on Vplay
 - Adds logout option and possibility to reset saved login credentials
 - Adds pagination for tv shows
 - Adds login status
 - Create app repository: http://moprea.ro/repository
 - Create script that builds package (zips everything excluding unwanted files) - check FAQ To get the instructions


### Version 1.4
 - Search added for tv shows and common videos
 - Correct meta data added to player item
 - Images added to list items for tv shows, series, episodes

### Version 1.2
 - Check why images (bg) are not rendered: media folder moved to correct subfolder
 - Change icon: Using our custom (weird image)

## Credits
 - Cornel Damian for https://github.com/corneldamian/xbmc.plugin.vplay.ro

## FAQ
 - Package the app:
 `git archive --format zip --output ~/Sites/repository/download/ro.moprea.vplay-1.5.zip --prefix ro.moprea.vplay/ master`
 - To sign app package, go here: http://www.boxee.tv/developer/apps



