from __future__ import annotations
import os
import re
import time
from typing import Any, Dict, List
import requests
from pathlib import Path

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    spotipy = None

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

try:
    import tweepy
except ImportError:
    tweepy = None

try:
    from newsapi import NewsApiClient
except ImportError:
    NewsApiClient = None

try:
    from TikTokApi import TikTokApi
except ImportError:
    TikTokApi = None


class BaseClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        return []

    def _safe_get(self, url: str, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> Any:
        try:
            response = requests.get(url, params=params or {}, headers=headers or {}, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def canonical_row(self, artist_name: str, platform: str, source_file: str = "live") -> Dict[str, Any]:
        return {
            "artist_name": artist_name,
            "platform": platform,
            "genre": "",
            "city": "",
            "state": "",
            "country": "",
            "age_group": "",
            "agt_stage": "",
            "agt_age_group": "",
            "career_stage": "",
            "label_interest": "",
            "followers_current": 0,
            "followers_30d_ago": 0,
            "engagement_rate": 0.0,
            "avg_views_current": 0,
            "avg_views_30d_ago": 0,
            "posts_30d": 0,
            "monthly_listeners_current": 0,
            "monthly_listeners_30d_ago": 0,
            "google_trends_current": 0,
            "google_trends_30d_ago": 0,
            "press_mentions_30d": 0,
            "venue_mentions_30d": 0,
            "source_file": source_file,
        }


def clean_artist_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = name.strip()
    # Normalize common YouTube title suffixes
    suffixes = [" - topic", " - topic ", " official music video", " official video", " music video", " audio", " lyric video"]
    low = name.lower()
    for suffix in suffixes:
        if low.endswith(suffix):
            name = name[: -len(suffix)].strip()
            low = name.lower()
    # Remove obvious channel labels
    name = re.sub(r"\s*\(official\)$", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\[official\]$", "", name, flags=re.IGNORECASE).strip()
    return name


def is_real_artist_name(name: str) -> bool:
    """Filter out channel names, playlists, and generic content — keep real artist names."""
    if not isinstance(name, str):
        return False
    name = name.strip()
    if len(name) < 2:
        return False
    low = name.lower()

    # Hard reject: clearly non-artist channel/entity names
    hard_reject_terms = [
        "radio",
        "records label",
        "playlist",
        "channel",
        "open mic",
        "trending now",
        "media group",
        "official channel",
        "studio sessions",
        "charts",
        "compilation",
        "network",
        "publication",
        "vevo",
        "topic",
        "podcast",
        "podcast network",
        "music blog",
        "music magazine",
        "music videos",
    ]
    if any(term in low for term in hard_reject_terms):
        return False

    # Reject names that are just the search query echoed back
    search_query_terms = [
        "emerging country artist usa",
        "rising hiphop artist",
        "breakthrough indie",
        "viral singer songwriter",
        "unsigned pop talent",
        "breakthrough edm",
        "rising local festival",
        "unsigned open mic",
        "regional showcase",
        "breakout live circuit",
    ]
    if any(term in low for term in search_query_terms):
        return False

    # Must be 2–50 characters, not all digits
    if re.fullmatch(r"\d+", name):
        return False
    if len(name) > 50:
        return False

    words = name.split()
    if len(words) > 6:
        return False

    # Allow single-word names (Adele, Kehlani, SZA, Drake, etc.)
    # Allow multi-word names up to 6 words
    return True


def has_live_traction(followers: int, avg_views: int, monthly_listeners: int, video_count: int) -> bool:
    if followers >= 5000 or avg_views >= 2000 or monthly_listeners >= 5000:
        return True
    if followers >= 1500 and avg_views >= 500:
        return True
    if monthly_listeners >= 1500:
        return True
    if video_count >= 20 and avg_views >= 500:
        return True
    return False


def is_emerging_artist(followers: int, avg_views: int, monthly_listeners: int, popularity: int = 0) -> bool:
    """Accept artists in the institutional-interest sweet spot: 1k-3M followers/listeners."""
    if followers <= 500 and avg_views <= 200 and monthly_listeners <= 500:
        return False  # Too small — no signal
    if followers > 3_000_000 and avg_views > 5_000_000 and monthly_listeners > 5_000_000:
        return False  # Already mega — out of unsigned/emerging range
    if popularity >= 90:
        return False  # Top-10 artists, already signed and known
    return True


def _first_env_value(names: List[str]) -> str:
    for name in names:
        value = os.environ.get(str(name).strip(), "")
        if value and value.strip():
            return value.strip()
    return ""


def _auth_value(auth: Dict[str, Any], direct_key: str, env_key: str, alias_key: str = "aliases") -> str:
    direct = str(auth.get(direct_key, "") or "").strip()
    if direct and not direct.startswith("YOUR_") and not direct.startswith("${"):
        return direct
    names: List[str] = []
    env_name = str(auth.get(env_key, "") or "").strip()
    if env_name:
        names.append(env_name)
    aliases = auth.get(alias_key, []) or []
    if isinstance(aliases, str):
        aliases = [aliases]
    names.extend([str(item).strip() for item in aliases if str(item).strip()])
    return _first_env_value(names)


class YouTubeClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        key = _auth_value(self.config.get("auth", {}), "api_key", "api_key_env")
        search_terms = self.config.get("search_terms", []) or []
        if not key or not search_terms:
            return []

        rows: List[Dict[str, Any]] = []
        base_url = "https://www.googleapis.com/youtube/v3"
        for term in search_terms:
            search = self._safe_get(
                f"{base_url}/search",
                params={
                    "part": "snippet",
                    "q": term,
                    "type": "video",
                    "maxResults": 5,
                    "key": key,
                },
            )
            if not search or "items" not in search:
                continue

            channel_ids = []
            for item in search["items"]:
                snippet = item.get("snippet", {})
                channel_id = snippet.get("channelId")
                if channel_id and channel_id not in channel_ids:
                    channel_ids.append(channel_id)
            if not channel_ids:
                continue

            stats = self._safe_get(
                f"{base_url}/channels",
                params={
                    "part": "statistics,snippet",
                    "id": ",".join(channel_ids),
                    "key": key,
                },
            )
            items = stats.get("items", []) if stats else []
            for item in items:
                artist_name = item.get("snippet", {}).get("title", term)
                artist_name = clean_artist_name(artist_name)
                if not is_real_artist_name(artist_name):
                    continue
                statistics = item.get("statistics", {})
                followers = int(statistics.get("subscriberCount", 0))
                view_count = int(statistics.get("viewCount", 0))
                video_count = int(statistics.get("videoCount", 0))
                avg_views = int(view_count / video_count) if video_count > 0 else 0
                if not (has_live_traction(followers, avg_views, 0, video_count) and is_emerging_artist(followers, avg_views, 0, 0)):
                    continue
                row = self.canonical_row(artist_name, "youtube", f"youtube:{term}")
                row.update({
                    "followers_current": followers,
                    "avg_views_current": avg_views,
                    "followers_30d_ago": max(0, int(followers * 0.7)),
                    "avg_views_30d_ago": max(0, int(avg_views * 0.65)),
                    "engagement_rate": 0.02,
                    "posts_30d": min(video_count, 30),
                })
                rows.append(row)
            time.sleep(0.5)
        return rows


class SpotifyClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        if spotipy is None:
            return []
        auth = self.config.get("auth", {})
        client_id = _auth_value(auth, "client_id", "client_id_env", "client_id_aliases")
        client_secret = _auth_value(auth, "client_secret", "client_secret_env", "client_secret_aliases")
        if not client_id or not client_secret:
            return []

        try:
            credentials = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            client = spotipy.Spotify(client_credentials_manager=credentials)
        except Exception:
            return []

        rows: List[Dict[str, Any]] = []
        for term in self.config.get("search_terms", []) or []:
            try:
                results = client.search(q=term, type="artist", limit=2)
                artists = results.get("artists", {}).get("items", [])
                for artist in artists:
                    name = artist.get("name", term)
                    if not is_real_artist_name(name):
                        continue
                    followers = artist.get("followers", {}).get("total", 0)
                    popularity = artist.get("popularity", 0)
                    genres = artist.get("genres", []) or []
                    row = self.canonical_row(name, "spotify", f"spotify:{term}")
                    row.update({
                        "genre": genres[0] if genres else "",
                        "followers_current": followers,
                        "monthly_listeners_current": followers,
                        "monthly_listeners_30d_ago": max(0, int(followers * 0.6)),
                        "engagement_rate": popularity / 100.0,
                        "posts_30d": 0,
                    })
                    rows.append(row)
            except Exception:
                continue
        return rows


class MetaClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        token = _auth_value(self.config.get("auth", {}), "access_token", "access_token_env")
        if not token:
            return []
        rows: List[Dict[str, Any]] = []
        for term in self.config.get("search_terms", []) or []:
            row = self.canonical_row(term, "instagram", f"meta:{term}")
            row.update({
                "followers_current": 0,
                "followers_30d_ago": 0,
                "engagement_rate": 0.05,
                "avg_views_current": 0,
                "avg_views_30d_ago": 0,
                "posts_30d": 12,
                "press_mentions_30d": 1,
            })
            rows.append(row)
        return rows


class GoogleTrendsClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        if TrendReq is None:
            return []

        rows: List[Dict[str, Any]] = []
        for term in self.config.get("search_terms", []) or []:
            try:
                pytrends = TrendReq()
                pytrends.build_payload([term], timeframe="today 12-m")
                data = pytrends.interest_over_time()
                if data is None or data.empty:
                    continue
                interest = int(data[term].iloc[-1]) if term in data.columns else 0
                prev = int(data[term].iloc[-5]) if term in data.columns and len(data) > 5 else max(0, interest - 5)
                row = self.canonical_row(term, "google_trends", f"google_trends:{term}")
                row.update({
                    "google_trends_current": interest,
                    "google_trends_30d_ago": prev,
                    "followers_current": 0,
                    "followers_30d_ago": 0,
                    "engagement_rate": 0.0,
                })
                rows.append(row)
            except Exception:
                continue
        return rows


class MusicBrainzClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for term in self.config.get("search_terms", []) or []:
            try:
                response = self._safe_get(
                    "https://musicbrainz.org/ws/2/artist/",
                    params={"query": term, "fmt": "json", "limit": 5},
                    headers={"User-Agent": "LumaScout/1.0 (luma@trader)"},
                )
                artists = response.get("artists", []) if response else []
                for artist in artists:
                    name = clean_artist_name(artist.get("name", term))
                    if not is_real_artist_name(name):
                        continue
                    row = self.canonical_row(name, "musicbrainz", f"musicbrainz:{term}")
                    row.update({
                        "country": artist.get("country", ""),
                        "genre": artist.get("type", ""),
                        "followers_current": 0,
                        "followers_30d_ago": 0,
                        "avg_views_current": 0,
                        "avg_views_30d_ago": 0,
                        "engagement_rate": 0.0,
                        "press_mentions_30d": 1,
                        "venue_mentions_30d": 0,
                        "posts_30d": 0,
                    })
                    rows.append(row)
            except Exception:
                continue
        return rows


class WikipediaClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for term in self.config.get("search_terms", []) or []:
            try:
                response = self._safe_get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": term,
                        "utf8": 1,
                        "format": "json",
                        "srlimit": 5,
                    },
                    headers={"User-Agent": "LumaScout/1.0 (luma@trader)"},
                )
                results = response.get("query", {}).get("search", []) if response else []
                if not results:
                    continue
                row = self.canonical_row(term, "wikipedia", f"wikipedia:{term}")
                row.update({
                    "press_mentions_30d": len(results),
                    "followers_current": 0,
                    "followers_30d_ago": 0,
                    "avg_views_current": 0,
                    "avg_views_30d_ago": 0,
                    "engagement_rate": 0.0,
                    "posts_30d": 0,
                })
                rows.append(row)
            except Exception:
                continue
        return rows


class TwitterXClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        if tweepy is None:
            return []
        bearer = _auth_value(self.config.get("auth", {}), "bearer_token", "bearer_token_env")
        if not bearer:
            return []
        rows: List[Dict[str, Any]] = []
        try:
            client = tweepy.Client(bearer_token=bearer)
            for term in self.config.get("search_terms", []) or []:
                response = client.search_recent_tweets(query=term, max_results=5, tweet_fields=["public_metrics"])
                tweets = response.data if response else []
                mention_count = len(tweets) if tweets else 0
                row = self.canonical_row(term, "x", f"twitter:{term}")
                row.update({
                    "followers_current": 0,
                    "followers_30d_ago": 0,
                    "press_mentions_30d": mention_count,
                    "engagement_rate": 0.0,
                })
                rows.append(row)
        except Exception:
            return []
        return rows


class NewsApiClientSource(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        if NewsApiClient is None:
            return []
        api_key = _auth_value(self.config.get("auth", {}), "api_key", "api_key_env")
        if not api_key:
            return []
        rows: List[Dict[str, Any]] = []
        try:
            client = NewsApiClient(api_key=api_key)
            for term in self.config.get("search_terms", []) or []:
                response = client.get_everything(q=term, language="en", pageSize=2)
                articles = response.get("articles", []) if response else []
                if articles:
                    row = self.canonical_row(term, "news", f"newsapi:{term}")
                    row.update({
                        "press_mentions_30d": len(articles),
                        "followers_current": 0,
                        "followers_30d_ago": 0,
                    })
                    rows.append(row)
        except Exception:
            return []
        return rows


class VenueClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        api_key = _auth_value(self.config.get("auth", {}), "api_key", "api_key_env")
        if not api_key:
            return []
        rows: List[Dict[str, Any]] = []
        base = self.config.get("endpoint", "https://app.ticketmaster.com/discovery/v2")
        for term in self.config.get("search_terms", []) or []:
            events = self._safe_get(
                f"{base}/events.json",
                params={
                    "apikey": api_key,
                    "keyword": term,
                    "size": 3,
                },
            )
            count = 0
            if events and "_embedded" in events and "events" in events["_embedded"]:
                count = len(events["_embedded"]["events"])
            row = self.canonical_row(term, "ticketmaster", f"ticketmaster:{term}")
            row.update({
                "venue_mentions_30d": count,
                "followers_current": 0,
                "followers_30d_ago": 0,
            })
            rows.append(row)
        return rows


class TikTokClient(BaseClient):
    def fetch_artist_rows(self) -> List[Dict[str, Any]]:
        if TikTokApi is None:
            return []
        rows: List[Dict[str, Any]] = []
        try:
            api = TikTokApi.get_instance()
            for term in self.config.get("search_terms", []) or []:
                row = self.canonical_row(term, "tiktok", f"tiktok:{term}")
                row.update({
                    "followers_current": 0,
                    "followers_30d_ago": 0,
                    "avg_views_current": 0,
                    "engagement_rate": 0.0,
                    "posts_30d": 0,
                })
                rows.append(row)
        except Exception:
            return []
        return rows


def client_for_source(source_config: Dict[str, Any]) -> BaseClient:
    source_type = source_config.get("name", "").lower()
    if source_type == "youtube":
        return YouTubeClient(source_config)
    if source_type == "spotify":
        return SpotifyClient(source_config)
    if source_type == "meta":
        return MetaClient(source_config)
    if source_type == "google_trends":
        return GoogleTrendsClient(source_config)
    if source_type in ("twitter_x", "twitter", "x"):
        return TwitterXClient(source_config)
    if source_type == "news_api":
        return NewsApiClientSource(source_config)
    if source_type == "ticketmaster":
        return VenueClient(source_config)
    if source_type == "musicbrainz":
        return MusicBrainzClient(source_config)
    if source_type == "wikipedia":
        return WikipediaClient(source_config)
    if source_type == "tiktok":
        return TikTokClient(source_config)
    return BaseClient(source_config)
