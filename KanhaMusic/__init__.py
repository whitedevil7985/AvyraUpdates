from pyrogram import raw as _raw


def _patch_update_group_call_chat_id():
    cls = _raw.types.UpdateGroupCall
    if hasattr(cls, "chat_id"):
        return

    def _peer_to_chat_id(peer):
        if isinstance(peer, _raw.types.PeerChannel):
            return peer.channel_id
        if isinstance(peer, _raw.types.PeerChat):
            return peer.chat_id
        if isinstance(peer, _raw.types.PeerUser):
            return peer.user_id
        return None

    def chat_id(self):
        return _peer_to_chat_id(getattr(self, "peer", None))

    cls.chat_id = property(chat_id)


_patch_update_group_call_chat_id()

from KanhaMusic.core.bot import Kanha, Shruti
from KanhaMusic.core.dir import dirr
from KanhaMusic.core.git import git
from KanhaMusic.core.userbot import Userbot
from KanhaMusic.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

ayush = Kanha()
nand = ayush
userbot = Userbot()


from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()
