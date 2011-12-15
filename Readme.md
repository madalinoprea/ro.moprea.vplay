
# Description
Boxee app to browse easier video sharing site http://vplay.ro

Current status: alpha (don't be fulled by version number)

## TODO
 - Implement support for multiple subtitles associated to a tv episode (EN if available)

## Release Notes

### Version 2.1
 - Update app to work with new Vplay's design
 - Watched episode are marked

### Version 1.9
 - Focus main menu when app is opened
 - Improve session status detection

### Version 1.8
 - A package that has required properties (app id, repository url) to be deployed on Boxee Apps

### Version 1.7
 - Add navigation buttons for series and episodes (Back to TV Show, Back to Series)

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



