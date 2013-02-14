#   Copyright 2012-2013 Josh Kearney
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import account


c = SharedCodeService.constants


def Start():
    ObjectContainer.title1 = c.PLUGIN_TITLE
    ObjectContainer.art = R(c.PLUGIN_ART)

    DirectoryObject.thumb = R(c.PLUGIN_ICON_DEFAULT)
    VideoClipObject.thumb = R(c.PLUGIN_ICON_DEFAULT)
    InputDirectoryObject.thumb = R(c.PLUGIN_ICON_SEARCH)
    PrefsObject.thumb = R(c.PLUGIN_ICON_PREFS)
    NextPageObject.thumb = R(c.PLUGIN_ICON_NEXT)


@handler("/video/amazoninstantvideo", c.PLUGIN_TITLE, thumb=c.PLUGIN_ICON_DEFAULT, art=c.PLUGIN_ART)
def MainMenu():
    logged_in = account.logged_in()
    if not logged_in:
        logged_in = account.authenticate()

    is_prime = account.is_prime()

    oc = ObjectContainer()

    if logged_in:
        if is_prime:
            oc.add(DirectoryObject(key=Callback(BrowseMenu, browse_type="movie"), title="Browse Movies"))
            oc.add(DirectoryObject(key=Callback(BrowseMenu, browse_type="tv"), title="Browse TV Shows"))

        oc.add(DirectoryObject(key=Callback(BrowseMenu, is_library=True), title="Your Library"))

        if is_prime:
            oc.add(DirectoryObject(key=Callback(BrowseMenu, is_watchlist=True), title="Your Watchlist"))
            oc.add(InputDirectoryObject(key=Callback(Search), title="Search", prompt="Search for a Movie or TV Show", thumb=R(c.PLUGIN_ICON_SEARCH)))

    oc.add(PrefsObject(title="Preferences"))

    return oc


@route("/video/amazoninstantvideo/browsemenu", is_library=bool, is_watchlist=bool)
def BrowseMenu(is_library=False, is_watchlist=False, browse_type=None, query=None, pagination_url=None):
    if query:
        title = "Search for '%s'" % query.title()
        if not pagination_url:
            # NOTE(jk0): Only build a query URL if we're performing a new
            # search and not using pagination on a previous search.
            query = query.replace(" ", "%20")
            browse_url = c.SEARCH_URL % query
    elif is_library:
        title = "Your Library"
        browse_url = c.LIBRARY_URL
    elif is_watchlist:
        title = "Your Watchlist"
        browse_url = c.WATCHLIST_URL
    elif browse_type == "movie":
        title = "Browse Movies"
        browse_url = c.MOVIES_URL
    else:
        title = "Browse TV Shows"
        browse_url = c.TV_URL

    if pagination_url:
        browse_url = c.AMAZON_URL + pagination_url

    html = HTML.ElementFromURL(browse_url)
    items = html.xpath(c.BROWSE_PATTERN)

    oc = ObjectContainer(title2=title)

    for item in items:
        try:
            asin = item.xpath(c.ASIN_PATTERN)[0]
            title = item.xpath(c.TITLE_PATTERN)[0].strip()
            image_link = item.xpath(c.IMAGE_LINK_PATTERN)[0]

            thumb = Resource.ContentsOfURLWithFallback(url=image_link, fallback=c.PLUGIN_ICON_DEFAULT)
        except IndexError:
            continue

        if browse_type == "tv" or "season" in title.lower():
            oc.add(SeasonObject(key=Callback(TVSeason, asin=asin, title=title, thumb=thumb, is_library=is_library), rating_key=asin, title=title, thumb=thumb))
        else:
            oc.add(MovieObject(url=c.PRODUCT_URL % asin, source_title=c.PLUGIN_TITLE, title=title, thumb=thumb))

    pagination_url = html.xpath(c.PAGINATION_PATTERN)
    if len(pagination_url) > 0:
        oc.add(NextPageObject(key=Callback(BrowseMenu, browse_type=browse_type, query=query, pagination_url=pagination_url[0]), title="Next..."))

    if len(oc) == 0:
        return ObjectContainer(header="No Results", message="No results were found.")

    return oc


@route("/video/amazoninstantvideo/search")
def Search(query):
    return BrowseMenu(query=query)


@route("/video/amazoninstantvideo/tvseason", is_library=bool)
def TVSeason(asin, title, thumb, is_library):
    html = HTML.ElementFromURL(c.PRODUCT_URL % asin)
    episodes = html.xpath(c.EPISODE_BROWSE_PATTERN)

    oc = ObjectContainer(title2=title)

    for episode in episodes:
        is_owned = True if episode.xpath(c.IS_OWNED_PATTERN)[0].strip() == "Owned" else False

        if not is_library or is_owned:
            asin = episode.xpath(c.EPISODE_ASIN_PATTERN)[0]
            title = episode.xpath(c.EPISODE_TITLE_PATTERN)[0].strip()
            summary = episode.xpath(c.EPISODE_SUMMARY_PATTERN)[0].strip()

            oc.add(EpisodeObject(url=c.PRODUCT_URL % asin, source_title=c.PLUGIN_TITLE, title=title, summary=summary, thumb=thumb))

    return oc
