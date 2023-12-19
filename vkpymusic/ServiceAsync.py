import os
import configparser
import logging
from typing import Optional, Union, Tuple, List

import aiofiles
from httpx import AsyncClient, Response

from .Song import Song
from .Playlist import Playlist
from .Logger import get_logger


logger: logging.Logger = get_logger(__name__)


class ServiceAsync:
    def __init__(self, user_agent: str, token: str):
        self.user_agent = user_agent
        self.__token = token

    @classmethod
    def parse_config(cls, filename: str="config_vk.ini"):
        """
        Create an instance of Service from config.
        
        Args:
            filename (str): Filename of config (default value = "config_vk.ini").
        """
        configfile_path = os.path.join(os.path.dirname(__file__), filename)
        try:
            config = configparser.ConfigParser()
            config.read(configfile_path, encoding="utf-8")
            user_agent = config["VK"]["user_agent"]
            token = config["VK"]["token_for_audio"]
            return ServiceAsync(user_agent, token)
        except Exception as e:
            logger.warning(e)

    @staticmethod
    def del_config(filename: str="config_vk.ini"):
        """
        Delete config created by 'TokenReceiver'.
        
        Args:
            filename (str): Filename of config (default value = "config_vk.ini").
        """
        configfile_path = os.path.join(os.path.dirname(__file__), filename)
        try:
            os.remove(configfile_path)
            logger.info("Config successful deleted!")
        except Exception as e:
            logger.warning(e)

    async def __get_response(
        self,
        method: str,
        params: List[Tuple[str, Union[str, int]]]
    ) -> Response:
        headers = {"User-Agent": self.user_agent}
        url = f"https://api.vk.com/method/audio.{method}"
        parameters = [
            ("access_token", self.__token),
            ("https", 1),
            ("lang", "ru"),
            ("extended", 1),
            ("v", "5.131"),
        ]
        for pair in params:
            parameters.append(pair)
        async with AsyncClient() as session:
            session.headers.update(headers)
            response = await session.post(url=url, params=parameters)
        return response

    async def __getCount(self, user_id: int) -> Response:
        params = [("owner_id", user_id)]
        return await self.__get_response("getCount", params)

    async def __get(
        self,
        user_id: int,
        count: int=100,
        offset: int=0,
        playlist_id: Optional[int]=None,
        access_key: Optional[str]=None
    ) -> Response:
        params = [
            ("owner_id", user_id),
            ("count", count),
            ("offset", offset)
        ]
        if playlist_id:
            params.append(("album_id", playlist_id))
            params.append(("access_key", access_key))
        return await self.__get_response("get", params)

    async def __search(
        self,
        text: str,
        count: int=100,
        offset: int=0
    ) -> Response:
        params = [
            ("q", text),
            ("count", count),
            ("offset", offset),
            ("sort", 0),
            ("autocomplete", 1),
        ]
        return await self.__get_response("search", params)

    async def __getPlaylists(
        self,
        user_id: int,
        count: int=50,
        offset: int=0
    ) -> Response:
        params = [
            ("owner_id", user_id),
            ("count", count),
            ("offset", offset),
        ]
        return await self.__get_response("getPlaylists", params)

    async def __searchPlaylists(
        self,
        text: str,
        count: int=50,
        offset: int=0
    ) -> Response:
        params = [
            ("q", text),
            ("count", count),
            ("offset", offset),
        ]
        return await self.__get_response("searchPlaylists", params)

    async def __searchAlbums(
        self,
        text: str,
        count: int=50,
        offset: int=0
    ) -> Response:
        params = [
            ("q", text),
            ("count", count),
            ("offset", offset),
        ]
        return await self.__get_response("searchAlbums", params)

    async def __response_to_songs(
        self,
        response: Response
    ) -> List[Song]:
        response = response.json()
        try:
            items = response["response"]["items"]
        except Exception as e:
            logger.error(e)
        songs: list[Song] = []
        for item in items:
            song = Song.from_json(item)
            songs.append(song)
        return songs

    async def __response_to_playlists(
        self,
        response: Response
    ) -> List[Playlist]:
        response = response.json(encoding="utf-8")
        try:
            items = response["response"]["items"]
        except Exception as e:
            logger.error(e)
        playlists: list[Playlist] = []
        for item in items:
            playlist = Playlist.from_json(item)
            playlists.append(playlist)
        return playlists

    async def get_count_by_user_id(
        self,
        user_id: Union[str, int]
    ) -> int:
        """
        Get count of all user's songs.
        
        Args:
            user_id (str | int): VK user id. (NOT USERNAME! vk.com/id*******).
        
        Returns:
            int: count of all user's songs.
        """
        user_id = int(user_id)
        logger.info(f"Request by user: {user_id}")
        try:
            response = await self.__getCount(user_id)
            # data = json.loads(response.content.decode("utf-8"))
            data = response.json(encoding="utf-8")
            songs_count = int(data["response"])
        except Exception as e:
            logger.error(e)
            return
        logger.info(f"Count of user's songs: {songs_count}")
        return songs_count

    async def get_songs_by_userid(
        self,
        user_id: Union[str, int],
        count: int=100,
        offset: int=0
    ) -> List[Song]:
        """
        Search songs by owner/user id.
        
        Args:
            user_id (str | int): VK user id. (NOT USERNAME! vk.com/id*******).
            count (int):          Count of resulting songs (for VK API: default/max = 100).
            offset (int):         Set offset for result. For example, count = 100, offset = 100 -> 101-200.
        Returns:
            list[Song]: List of songs.
        """
        user_id = int(user_id)
        logger.info(f"Request by user: {user_id}")
        try:
            response: Response = await self.__get(user_id, count, offset)
            songs = await self.__response_to_songs(response)
        except Exception as e:
            logger.error(e)
            return
        if len(songs) == 0:
            logger.info("No results found ._.")
        else:
            logger.info("Results:")
            for i, song in enumerate(songs, start=1):
                logger.info(f"{i}) {song}")
        return songs

    async def get_songs_by_playlist_id(
        self,
        user_id: Union[str, int],
        playlist_id: int,
        access_key: str,
        count: int=100,
        offset: int=0,
    ) -> List[Song]:
        """
        Get songs by playlist id.
        Args:
            user_id (str | int): VK user id. (NOT USERNAME! vk.com/id*******).
            playlist_id (int):    VK playlist id. (Take it from methods for playlist).
            access_key (str):     VK access key. (Take it from methods for playlist).
            count (int):          Count of resulting songs (for VK API: default/max = 100).
            offset (int):         Set offset for result. For example, count = 100, offset = 100 -> 101-200.
        
        Returns:
            list[Song]: List of songs.
        """
        user_id = int(user_id)
        logger.info(f"Request by user: {user_id}")
        try:
            response: Response = await self.__get(
                user_id, count, offset, playlist_id, access_key
            )
            songs = await self.__response_to_songs(response)
        except Exception as e:
            logger.error(e)
            return
        if len(songs) == 0:
            logger.info("No results found ._.")
        else:
            logger.info("Results:")
            for i, song in enumerate(songs, start=1):
                logger.info(f"{i}) {song}")
        return songs

    async def get_songs_by_playlist(
        self,
        playlist: Playlist,
        count: int=10,
        offset: int=0
    ) -> List[Song]:
        """
        Get songs by instance of 'Playlist'.
        
        Args:
            playlist (Playlist): Instance of 'Playlist' (take from methods for receiving Playlist).
            count (int):         Count of resulting songs (for VK API: default/max = 100).
            offset (int):        Set offset for result. For example, count = 100, offset = 100 -> 101-200.
        
        Returns:
            list[Song]: List of songs.
        """
        logger.info(f"Request by playlist: {playlist}")
        try:
            response: Response = await self.__get(
                playlist.owner_id,
                count,
                offset,
                playlist.playlist_id,
                playlist.access_key,
            )
            songs = await self.__response_to_songs(response)
        except Exception as e:
            logger.error(e)
            return
        if len(songs) == 0:
            logger.info("No results found ._.")
        else:
            logger.info("Results:")
            for i, song in enumerate(songs, start=1):
                logger.info(f"{i}) {song}")
        return songs

    async def search_songs_by_text(
        self,
        text: str,
        count: int=3,
        offset: int=0
    ) -> List[Song]:
        """
        Search songs by text/query.
        
        Args:
            text (str):   Text of query. Can be title of song, author, etc.
            count (int):  Count of resulting songs (for VK API: default/max = 100).
            offset (int): Set offset for result. For example, count = 100, offset = 100 -> 101-200.
        
        Returns:
            list[Song]: List of songs.
        """
        logger.info(f'Request by text: "{text}" в количестве {count}')
        try:
            response: Response = await self.__search(text, count, offset)
            songs = await self.__response_to_songs(response)
        except Exception as e:
            logger.error(e)
            return
        if len(songs) == 0:
            logger.info("No results found ._.")
        else:
            logger.info("Results:")
            for i, song in enumerate(songs, start=1):
                logger.info(f"{i}) {song}")
        return songs

    async def get_playlists_by_userid(
        self,
        user_id: Union[str, int],
        count: int=5,
        offset: int=0
    ) -> List[Playlist]:
        """
        Get playlist by owner/user id.

        Args:
            user_id (str | int): VK user id. (NOT USERNAME! vk.com/id*******).
            count (int):          Count of resulting playlists (for VK API: default = 50, max = 100).
            offset (int):         Set offset for result. For example, count = 100, offset = 100 -> 101-200.
        
        Returns:
            list[Playlist]: List of playlists.
        """
        user_id = int(user_id)
        logger.info(f"Request by user: {user_id}")

        try:
            response: Response = await self.__getPlaylists(
                user_id, count, offset
            )
            playlists = await self.__response_to_playlists(response)
        except Exception as e:
            logger.error(e)
            return
        if len(playlists) == 0:
            logger.info("No results found ._.")
        else:
            logger.info("Results:")
            for i, playlist in enumerate(playlists, start=1):
                logger.info(f"{i}) {playlist}")
        return playlists

    async def search_playlists_by_text(
        self,
        text: str,
        count: int=5,
        offset: int=0
    ) -> List[Playlist]:
        """
        Search playlists by text/query.
        Playlist - it user's collection of songs.
        
        Args:
            text (str):   Text of query. Can be title of playlist, genre, etc.
            count (int):  Count of resulting playlists (for VK API: default = 50, max = 100).
            offset (int): Set offset for result. For example, count = 100, offset = 100 -> 101-200.

        Returns:
            list[Playlist]: List of playlists.
        """
        logger.info(f"Request by text: {text}")
        try:
            response: Response = await self.__searchPlaylists(
                text, count, offset
            )
            playlists = await self.__response_to_playlists(response)
        except Exception as e:
            logger.error(e)
            return
        if len(playlists) == 0:
            logger.info("No results found ._.")
        else:
            logger.info("Results:")
            for i, playlist in enumerate(playlists, start=1):
                logger.info(f"{i}) {playlist}")
        return playlists

    async def search_albums_by_text(
        self,
        text: str,
        count: int=5,
        offset: int=0
    ) -> List[Playlist]:
        """
        Search albums by text/query.
        Album - artists's album/collection of songs.
        In obj context - same as 'Playlist'.
        
        Args:
            text (str):   Text of query. Can be title of album, name of artist, etc.
            count (int):  Count of resulting playlists (for VK API: default = 50, max = 100).
            offset (int): Set offset for result. For example, count = 100, offset = 100 -> 101-200.
        
        Returns:
            list[Playlist]: List of albums.
        """
        logger.info(f"Request by text: {text}")
        try:
            response: Response = await self.__searchAlbums(
                text, count, offset
            )
            playlists = await self.__response_to_playlists(response)
        except Exception as e:
            logger.error(e)
            return
        if len(playlists) == 0:
            logger.info("No results found ._.")
        else:
            logger.info("Results:")
            for i, playlist in enumerate(playlists, start=1):
                logger.info(f"{i}) {playlist}")
        return playlists

    @staticmethod
    async def save_music(
        song: Song,
        overwrite: bool=False
    ) -> str:
        """
        Save song to '{workDirectory}/Music/{songname}.mp3'.
        
        Args:
            song (Song): 'Song' instance obtained from 'Service' methods.
            overwrite (bool): Overwrite file if it exists
        
        Returns:
            str: relative path of downloaded music.
        """
        song.to_safe()
        file_name_mp3 = f"{song}.mp3"
        url = song.url
        async with AsyncClient() as session:
            response = await session.get(url=url)
            if response.status_code == 200:
                if not os.path.exists("Music"):
                    os.makedirs("Music")
                    logger.info("Folder 'Music' was created")
                file_path = os.path.join(os.getcwd(), "Music", file_name_mp3)
                if not os.path.exists(file_path):
                    if "index.m3u8" in url:
                        logger.error(".m3u8 detected!")
                        return
                else:
                    logger.warning(f"File with name '{file_name_mp3}' exists.")
                    if not overwrite:
                        return file_path
            logger.info(f"Downloading {song}...")
            async with aiofiles.open(file_path, "wb") as output_file:
                await output_file.write(response.read())
        logger.info(f"Success! Music was downloaded in '{file_path}'")
        return file_path
