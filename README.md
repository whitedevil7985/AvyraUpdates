<div align="center">

# 🎵 𝐒𝐡𝐫𝐮𝐭𝐢 𝐌𝐮𝐬𝐢𝐜 𝐁𝐨𝐭

> **High-Performance, Next-Gen Telegram Voice Chat Music & Video Streaming Bot**  
> Powered by **Kurigram**, **PyTgCalls**, and an **Ultra-Fast Dual-API Streaming Engine**.

<p align="center">
  <img src="https://graph.org/file/7557c0e0e0c1708f62d6a-6892ea881cc1555c83.jpg" alt="Shruti Music" width="300" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
</p>

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Telegram Channel](https://img.shields.io/badge/Channel-@MeowCloner-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/MeowCloner)
[![Telegram Support](https://img.shields.io/badge/Support-@MeowClone-0088cc?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/MeowClone)

<br>

<p align="center">
  <a href="#-key-features">Key Features</a> •
  <a href="#-quick-deploy">Deploy</a> •
  <a href="#-vps-installation">VPS Setup</a> •
  <a href="#-configuration">Configuration</a> •
  <a href="#-commands">Commands</a> •
  <a href="#-credits">Credits</a>
</p>

---

</div>

## 🌟 Key Features

- ⚡ **Dual-API Streaming Engine**:
  Runs **NUB API** and **Ritesh API** simultaneously in a high-speed parallel race. Whichever responds first delivers the stream instantly without buffering, with reliable `yt-dlp` fallback!
- 🎶 **Smart Autoplay (No Repeats)**:
  Advanced title fingerprinting, candidate deduplication, and YouTube Watch Next algorithm to ensure continuous, fresh music recommendations without repeating tracks.
- 🎵 **Multi-Platform Resolvers**:
  Full support for **YouTube** (Search, URLs, Playlists), **Spotify** (Tracks, Playlists, Albums, Artists with zero-credential web scraping fallback), **SoundCloud**, **Apple Music**, **Resso**, and **Telegram Audio/Video files**.
- 🎛️ **Interactive Controls**:
  Now Playing panel with live interactive inline buttons (Pause, Resume, Skip, Replay, Stop, Autoplay Toggle, and real-time seek bar).
- 👥 **Multi-Assistant Architecture**:
  Support for 1 to 5 Telegram assistant accounts for distributed load and smooth streaming across thousands of voice chats.
- 📺 **Crystal Clear HD Video Streaming**:
  Stream 720p/1080p video directly inside group video chats with customizable quality parameters.
- 🛠️ **Powerful Admin & Sudo Controls**:
  Global bans, chat blacklisting, channel-play linking, maintenance mode, speedtest, broadcast tools, and rich logging.

---

## 🚀 Quick Deploy

Choose your preferred hosting platform:

<div align="center">

### Heroku
<a href="https://heroku.com/deploy?template=https://github.com/Hackerbhai03/Shruti">
  <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy to Heroku" height="38">
</a>

<br><br>

### Render
<a href="https://render.com/deploy?repo=https://github.com/Hackerbhai03/Shruti">
  <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="38">
</a>

</div>

---

## 🖥️ VPS Installation

Deploy Shruti Music on any **Ubuntu / Debian** server with Python 3.10 or 3.11:

### 1. Update Packages & Install System Dependencies
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git ffmpeg curl screen
```

### 2. Clone the Repository
```bash
git clone https://github.com/Hackerbhai03/Shruti.git
cd Shruti
```

### 3. Create & Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Requirements
```bash
pip install -U pip wheel
pip install -r requirements.txt
```

### 5. Setup Environment Variables
Create and edit your `.env` file:
```bash
cp .env.sample .env 2>/dev/null || touch .env
nano .env
```
*(Fill in your credentials from the [Configuration](#-configuration) section below)*

### 6. Start the Bot
Run directly or inside a screen session:
```bash
screen -S shruti
bash start
```
> Press `Ctrl + A`, then `D` to detach the screen session. Reattach anytime using `screen -r shruti`.

---

## 🐳 Docker Deployment

Run effortlessly inside a lightweight Docker container:

```bash
# Build the Docker image
docker build -t shrutimusic .

# Run the container
docker run -d --name shrutimusic --env-file .env --restart always shrutimusic
```

View live logs:
```bash
docker logs -f shrutimusic
```

---

## ⚙️ Configuration

Set these variables in your `.env` file or hosting environment:

### Mandatory Variables

| Variable | Description |
| :--- | :--- |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | Bot Token from [@BotFather](https://t.me/BotFather) |
| `MONGO_DB_URI` | MongoDB Atlas URI string for database persistence |
| `LOGGER_ID` | Telegram Log Group / Channel ID (e.g. `-100xxxxxxxxxx`) |
| `OWNER_ID` | Telegram User ID of the bot owner |
| `STRING_SESSION` | Pyrogram v2 string session of your Assistant account |

### API & Streaming Configuration (Pre-configured)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `YTUBE_API_TOKEN` | `c8t5JHzIKs` | NUB YouTube API Token |
| `YTUBE_API_BASE_URL` | `https://api.nubcoders.com` | NUB YouTube API Base URL |
| `RITESH_API_KEY` | `riteshfree7a13156394b9c397822c0006` | Ritesh YouTube API Key |
| `RITESH_API_URL` | `https://api.riteshyt.in` | Ritesh YouTube API Base URL |

### Optional Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `STRING_SESSION2` to `5` | `None` | Additional assistant accounts for multi-client scaling |
| `DURATION_LIMIT` | `6000` | Max duration allowed per track in minutes |
| `PLAYLIST_FETCH_LIMIT` | `25` | Maximum number of songs to import from a playlist |
| `SPOTIFY_CLIENT_ID` | `None` | Spotify App Client ID *(Auto-fallback to web scraper if empty)* |
| `SPOTIFY_CLIENT_SECRET` | `None` | Spotify App Client Secret |
| `AUTO_LEAVING_ASSISTANT` | `False` | Assistant leaves voice chat automatically when empty |
| `SUPPORT_CHANNEL` | `https://t.me/MeowCloner` | Channel URL shown in bot interface |
| `SUPPORT_CHAT` | `https://t.me/MeowClone` | Support group URL shown in bot interface |

---

## 📜 Commands Reference

### 🎧 Playback Commands
| Command | Description |
| :--- | :--- |
| `/play <song/url>` | Play audio stream in voice chat |
| `/vplay <song/url>` | Play video stream in voice chat |
| `/playforce <song/url>` | Force-play audio immediately, replacing current track |
| `/vplayforce <song/url>` | Force-play video immediately |
| `/pause` | Pause active stream |
| `/resume` | Resume paused stream |
| `/skip` | Skip to next song in queue |
| `/end` or `/stop` | Stop playback and clear voice chat queue |
| `/seek <seconds>` | Seek stream forward |
| `/seekback <seconds>` | Seek stream backward |
| `/speed <0.5x-2.0x>` | Adjust stream playback speed |
| `/loop <1-10>` | Loop the current track |
| `/shuffle` | Shuffle the upcoming tracks in queue |
| `/autoplay` | Toggle smart autoplay on/off |

### 📋 Queue & Info Commands
| Command | Description |
| :--- | :--- |
| `/queue` | View the current track and upcoming list |
| `/playing` or `/player` | Display interactive player control panel |
| `/song <query>` | Download audio/video song directly to Telegram |
| `/ping` | Check bot uptime, ping latency and system RAM usage |
| `/stats` | View global bot usage statistics |

### ⚙️ Group Settings
| Command | Description |
| :--- | :--- |
| `/auth <user>` | Authorize a member to use admin commands |
| `/unauth <user>` | Revoke member authorization |
| `/authlist` | List all authorized members |
| `/playmode` | Toggle between everyone / admin-only play modes |
| `/channelplay <channel>` | Link and stream inside a connected channel |
| `/settings` | Open group configuration menu |
| `/language` | Change bot display language |

### 👑 Sudo / Owner Commands
| Command | Description |
| :--- | :--- |
| `/broadcast <msg>` | Broadcast announcement to all chats |
| `/gban <user>` | Globally ban a user from all groups |
| `/ungban <user>` | Remove global ban from user |
| `/blchat <chat_id>` | Blacklist a chat from using the bot |
| `/logger <on/off>` | Toggle play activity logger |
| `/maintenance <on/off>` | Toggle maintenance mode |
| `/restart` | Restart bot process |
| `/update` | Pull latest updates from Git repository |

---

## 🤝 Community & Support

Need assistance or have queries? Join our official community:

<p align="center">
  <a href="https://t.me/MeowClone">
    <img src="https://img.shields.io/badge/Telegram-Join%20Support%20Group-blue.svg?style=for-the-badge&logo=telegram">
  </a>
  &nbsp;&nbsp;
  <a href="https://t.me/MeowCloner">
    <img src="https://img.shields.io/badge/Telegram-Updates%20Channel-cyan.svg?style=for-the-badge&logo=telegram">
  </a>
</p>

---

<div align="center">

### ❤️ Made with Love by **[Hackerbhai03](https://github.com/Hackerbhai03)**

⭐ **Star this repository if you found it useful!**

</div>
