"""
Module containing the Blog source class
"""
import dataclasses
import logging
import typing
from datetime import datetime
from dateutil.parser import isoparse
import pytz
import pyyoutube


from authority.model.contribution import Contribution
from authority.sources.base_ import AuthoritySource
from authority.util.google_secrets import SecretManager
from authority.util.lazy_env import lazy_env

if typing.TYPE_CHECKING:
    import collections.abc

@dataclasses.dataclass
class Channel:
    username: str
    author: str
    channel_id: str

_channels = [Channel("@martinperez9665", "Martín Pérez Rodríguez", "UC0-IFu7XWoeT-QehlXxNmiw")]


class YoutubeChannel(AuthoritySource):
    """
    youtube channel scraper implementation
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_channel: typing.Optional[Channel] = None
        self._api_key = lazy_env(
                    key="YOUTUBE_API_KEY",
                    default=lambda: SecretManager().get_secret(
                        "authority-contribution-scraper-youtube-api-key"
                    ),
                )


    @property
    def name(self) -> str:
        return f"youtube.com/{self.current_channel.username}" if self.current_channel else "youtube.com"

    @classmethod
    def scraper_id(cls) -> str:
        return "youtube.com"

    @property
    def _contribution_type(self) -> str:
        return "blog"

    def _get_latest_entry(self, username: str) -> datetime:
        return self.sink.latest_entry(
            type=self._contribution_type, scraper_id=self.name
        )

    @property
    def _feed(self) -> "collections.abc.Generator[Contribution, None, None]":
        api = pyyoutube.Api(api_key=self._api_key)

        for self.current_channel in _channels:
            latest = self._get_latest_entry(self.current_channel.username)
            logging.info(
                "reading new vlogs from https://%s since %s", self.name, latest
            )
            now = datetime.now().astimezone(pytz.utc)

            channel_info = api.get_channel_info(channel_id=self.current_channel.channel_id)

            playlist_id = channel_info.items[0].contentDetails.relatedPlaylists.uploads

            page_token = None
            uploads_playlist_items = api.get_playlist_items(
                playlist_id=playlist_id, count=50, limit=50, page_token=page_token
            )

            for item in uploads_playlist_items.items:
                published_at = isoparse(item.contentDetails.videoPublishedAt)
                if latest < published_at < now:
                    yield from self._process_vlog_entry(item, published_at)

    def _process_vlog_entry(self, entry: pyyoutube.PlaylistItem, published_date: datetime) -> "collections.abc.Generator[Contribution, None, None]":


            url = f"https://www.youtube.com/watch?v=" + entry.contentDetails.videoId
            yield Contribution(
                guid=url,
                author=self.current_channel.author,
                date=published_date,
                title=entry.snippet.title,
                url=url,
                scraper_id=self.name,
                type=self._contribution_type,
            )


if __name__ == "__main__":
    from authority.util.test_source import test_source

    test_source(source=YoutubeChannel)
