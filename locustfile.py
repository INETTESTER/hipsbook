import os
import random
import time

from gevent.lock import Semaphore
from locust import HttpUser, task, between

from config import (
    REQUEST_TIMEOUT_SECONDS,
    LIVE_PATH,
    WEB_BASE,
    LIVE_DETAIL_API_URL,
    STREAM_API_KEY,
)

from hls_parser import (
    extract_playlist_urls,
    extract_latest_media_urls,
    detect_media_type,
)


# ---------------------------------------------------------------------------
# Load Test Profile
# ---------------------------------------------------------------------------
# Select profile from .env or command.
#
# Default:
#   TEST_PROFILE=realistic
#
# Override from command:
#   TEST_PROFILE=stress locust ...
#
# Available profiles:
#   realistic - normal live viewer simulation
#   stress    - heavier traffic for limit testing
# ---------------------------------------------------------------------------

TEST_PROFILE = os.getenv("TEST_PROFILE", "realistic").lower()


# ---------------------------------------------------------------------------
# Profile Settings
# ---------------------------------------------------------------------------
# These values control how frequently each virtual user performs:
#   - livestream API polling
#   - HLS master playlist refresh
#   - HLS media playlist refresh
#   - task loop delay
#
# Notes:
#   - Realistic profile is intentionally conservative to avoid overloading
#     the stream provider, local network, or load generator too quickly.
#   - Stress profile is intentionally heavier and should be used carefully.
# ---------------------------------------------------------------------------

if TEST_PROFILE == "stress":
    # -----------------------------------------------------------------------
    # Stress Test Settings
    # -----------------------------------------------------------------------
    # Generates heavier traffic than normal viewers.
    # Use this profile only when intentionally finding limits, bottlenecks,
    # provider rate limits, or breaking points.
    # -----------------------------------------------------------------------

    API_POLL_INTERVAL_SECONDS = 20
    HLS_PLAYLIST_REFRESH_SECONDS = 3
    MASTER_REFRESH_SECONDS = 45

    TASK_SLEEP_MIN_SECONDS = 0.8
    TASK_SLEEP_MAX_SECONDS = 1.5

elif TEST_PROFILE == "realistic":
    # -----------------------------------------------------------------------
    # Realistic Viewer Load Test Settings
    # -----------------------------------------------------------------------
    # Simulates normal HLS live viewers.
    #
    # These values are tuned to reduce unrealistic HLS pressure:
    #   - API polling is not too frequent
    #   - Media playlist refresh is moderate
    #   - Master playlist refresh is infrequent
    #   - Task loop has natural pacing
    #
    # This helps prevent the stream, bandwidth, or load generator CPU from
    # becoming saturated too quickly.
    # -----------------------------------------------------------------------

    API_POLL_INTERVAL_SECONDS = 60
    HLS_PLAYLIST_REFRESH_SECONDS = 8
    MASTER_REFRESH_SECONDS = 120

    TASK_SLEEP_MIN_SECONDS = 2.0
    TASK_SLEEP_MAX_SECONDS = 4.0

else:
    raise ValueError(
        f"Invalid TEST_PROFILE: {TEST_PROFILE}. "
        "Use 'realistic' or 'stress'."
    )


# ---------------------------------------------------------------------------
# Common Settings
# ---------------------------------------------------------------------------

# Number of recently downloaded media segments remembered per virtual user.
# This prevents the same user from repeatedly downloading the same segment.
SEGMENT_MEMORY_SIZE = 100

# Maximum number of latest segments to fetch from each media playlist.
# Keep this at 1 for realistic HLS viewer behavior.
# Increasing this value can greatly increase bandwidth usage.
LATEST_SEGMENT_LIMIT = 1

# Disabled by default.
# Enable this only if you explicitly want to include OPTIONS preflight traffic.
SIMULATE_CORS_PREFLIGHT = False


# ---------------------------------------------------------------------------
# Live Detail API Mode
# ---------------------------------------------------------------------------
# Controls how /api/livestream/:id is used.
#
# Modes:
#   normal
#       Poll /api/livestream/:id based on API_POLL_INTERVAL_SECONDS.
#
#   cache
#       Fetch /api/livestream/:id only when there is no cached playbackHlsUrl
#       or when the cache expires.
#
#       This mode uses a process-level lock so that only one virtual user
#       fetches live detail when the cache is empty or expired.
#
#       Recommended when the test objective is HLS playback capacity but
#       you still want Locust to obtain playbackHlsUrl automatically.
#
#   off
#       Do not call /api/livestream/:id at all.
#       Requires MASTER_M3U8_URL in .env.
#
# Examples:
#   LIVE_DETAIL_MODE=cache
#   LIVE_DETAIL_CACHE_TTL_SECONDS=86400
#
#   LIVE_DETAIL_MODE=off
#   MASTER_M3U8_URL=https://hips-stream.com/hls/.../index.m3u8
# ---------------------------------------------------------------------------

LIVE_DETAIL_MODE = os.getenv("LIVE_DETAIL_MODE", "cache").lower()

if LIVE_DETAIL_MODE not in ("normal", "cache", "off"):
    raise ValueError(
        f"Invalid LIVE_DETAIL_MODE: {LIVE_DETAIL_MODE}. "
        "Use 'normal', 'cache', or 'off'."
    )

LIVE_DETAIL_CACHE_TTL_SECONDS = int(
    os.getenv("LIVE_DETAIL_CACHE_TTL_SECONDS", "86400")
)

STATIC_MASTER_M3U8_URL = os.getenv("MASTER_M3U8_URL") or None


class LiveHlsViewerUser(HttpUser):
    # -----------------------------------------------------------------------
    # Process-level cache
    # -----------------------------------------------------------------------
    # This cache is shared by virtual users in the same Locust process.
    #
    # Important:
    #   When using --processes 4, each process has its own cache.
    #   Therefore, LIVE_DETAIL_MODE=cache may call /api/livestream/:id
    #   about once per process when cache is empty or expired.
    # -----------------------------------------------------------------------

    cached_master_m3u8_url: str | None = STATIC_MASTER_M3U8_URL
    cached_live_detail_at: float = time.time() if STATIC_MASTER_M3U8_URL else 0.0
    live_detail_cache_lock = Semaphore()

    # Locust wait time between task executions.
    # The task itself also has TASK_SLEEP_MIN_SECONDS / TASK_SLEEP_MAX_SECONDS
    # to simulate player pacing.
    wait_time = between(1, 2)

    connection_timeout = 10
    network_timeout = REQUEST_TIMEOUT_SECONDS

    def on_start(self):
        # Spread user start time to avoid all users starting at the same moment.
        time.sleep(random.uniform(0.5, 3.0))

        self.client.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        })

        self.joined_live = False
        self.master_m3u8_url: str | None = self.__class__.cached_master_m3u8_url
        self.playlist_urls: list[str] = []

        self.seen_segments: set[str] = set()
        self.seen_segment_order: list[str] = []

        # Randomize initial poll timing so users do not poll API together.
        self.last_api_poll = time.time() - random.uniform(
            0,
            API_POLL_INTERVAL_SECONDS,
        )

        # Randomize HLS refresh timing so users do not fetch playlists together.
        self.last_master_refresh = time.time() - random.uniform(
            0,
            MASTER_REFRESH_SECONDS,
        )
        self.last_playlist_refresh = time.time() - random.uniform(
            0,
            HLS_PLAYLIST_REFRESH_SECONDS,
        )

        if LIVE_DETAIL_MODE == "off" and not self.master_m3u8_url:
            raise RuntimeError(
                "LIVE_DETAIL_MODE=off requires MASTER_M3U8_URL in .env"
            )

        # Backoff state for API polling.
        self.api_backoff_until = 0.0

    def remember_segment(self, media_url: str):
        """
        Remember recently downloaded segments per virtual user.

        This prevents the same virtual user from downloading the same media
        segment repeatedly, which makes the test closer to real playback.
        """
        self.seen_segments.add(media_url)
        self.seen_segment_order.append(media_url)

        if len(self.seen_segment_order) > SEGMENT_MEMORY_SIZE:
            old_url = self.seen_segment_order.pop(0)
            self.seen_segments.discard(old_url)

    def safe_get(
        self,
        url: str,
        name: str,
        headers: dict | None = None,
        expected_status: tuple[int, ...] = (200,),
    ) -> str | None:
        """
        Safe GET wrapper with basic retry and Locust reporting.
        """
        retries = 1

        for _ in range(retries + 1):
            with self.client.get(
                url,
                name=name,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers=headers,
                catch_response=True,
            ) as res:
                if res.status_code in expected_status:
                    res.success()
                    return res.text

                if res.status_code == 0:
                    res.failure(f"{name} failed: connection timeout/reset")
                    return None

                if res.status_code in (401, 403):
                    res.failure(f"{name} auth/access error: {res.status_code}")

                    # Slow down this virtual user when access/auth errors occur.
                    time.sleep(random.uniform(10, 20))
                    continue

                if res.status_code == 429:
                    res.failure(f"{name} rate limited: 429")

                    # Back off more strongly when provider/server rate limit is hit.
                    time.sleep(random.uniform(10, 30))
                    continue

                if res.status_code >= 500:
                    res.failure(f"{name} server error: {res.status_code}")

                    # Short retry delay for temporary server-side failures.
                    time.sleep(random.uniform(1, 3))
                    continue

                res.failure(f"{name} failed: {res.status_code}")
                return None

        return None

    def preflight_live_detail(self):
        """
        Optional CORS preflight simulation.

        Disabled by default because browsers only send preflight requests
        under specific conditions. Enable SIMULATE_CORS_PREFLIGHT only when
        you explicitly want to include OPTIONS traffic in the test.
        """
        if not SIMULATE_CORS_PREFLIGHT:
            return

        with self.client.options(
            LIVE_DETAIL_API_URL,
            name="stream api OPTIONS /api/livestream/:id",
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "Origin": WEB_BASE,
                "Referer": f"{WEB_BASE}/",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-api-key",
            },
            catch_response=True,
        ) as res:
            if res.status_code in (200, 204):
                res.success()
            else:
                res.failure(f"preflight failed: {res.status_code}")

    def fetch_live_page_once(self):
        """
        Open the live page once per virtual user.
        """
        if self.joined_live:
            return

        self.safe_get(
            LIVE_PATH,
            "/live/:id",
            headers={
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Referer": f"{WEB_BASE}/",
            },
        )

        self.joined_live = True

    def fetch_live_detail(self) -> dict | None:
        """
        Fetch livestream detail API.

        This should be called only by poll_live_detail_if_needed().
        """
        if random.random() < 0.15:
            self.preflight_live_detail()

        with self.client.get(
            LIVE_DETAIL_API_URL,
            name="stream api GET /api/livestream/:id",
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Origin": WEB_BASE,
                "Referer": f"{WEB_BASE}/",
                "x-api-key": STREAM_API_KEY,
            },
            catch_response=True,
        ) as res:
            if res.status_code == 0:
                res.failure("live detail failed: connection timeout/reset")
                self.api_backoff_until = time.time() + random.uniform(30, 60)
                return None

            if res.status_code == 401:
                res.failure("live detail failed: 401")

                # Backoff 30-60 seconds to reduce hammering when auth/access
                # problems occur or when the server/provider is overwhelmed.
                self.api_backoff_until = time.time() + random.uniform(30, 60)
                return None

            if res.status_code != 200:
                res.failure(f"live detail failed: {res.status_code}")
                return None

            try:
                data = res.json()
            except Exception:
                res.failure("live detail invalid JSON")
                return None

            res.success()
            return data

    def update_master_url_from_live_detail(self, data: dict | None) -> dict | None:
        """
        Update master_m3u8_url and process-level cache from live detail response.
        """
        if not data:
            return None

        playback_hls_url = data.get("playbackHlsUrl")
        if playback_hls_url:
            now = time.time()

            self.master_m3u8_url = playback_hls_url
            self.__class__.cached_master_m3u8_url = playback_hls_url
            self.__class__.cached_live_detail_at = now

        return data

    def poll_live_detail_if_needed(self) -> dict | None:
        """
        Single entry point for /api/livestream/:id.

        LIVE_DETAIL_MODE behavior:
          - normal: poll API based on interval
          - cache : fetch once per process and reuse cached playbackHlsUrl
          - off   : never call API, use MASTER_M3U8_URL from .env
        """
        now = time.time()

        if LIVE_DETAIL_MODE == "off":
            if not self.master_m3u8_url:
                self.master_m3u8_url = STATIC_MASTER_M3U8_URL
            return None

        if LIVE_DETAIL_MODE == "cache":
            cached_url = self.__class__.cached_master_m3u8_url
            cache_age = now - self.__class__.cached_live_detail_at

            if cached_url and cache_age < LIVE_DETAIL_CACHE_TTL_SECONDS:
                self.master_m3u8_url = cached_url
                return None

            # Prevent many users from calling /api/livestream/:id at the same
            # time when cache is empty or expired.
            with self.__class__.live_detail_cache_lock:
                now = time.time()

                cached_url = self.__class__.cached_master_m3u8_url
                cache_age = now - self.__class__.cached_live_detail_at

                if cached_url and cache_age < LIVE_DETAIL_CACHE_TTL_SECONDS:
                    self.master_m3u8_url = cached_url
                    return None

                if now < self.api_backoff_until:
                    return None

                self.last_api_poll = now

                data = self.fetch_live_detail()
                return self.update_master_url_from_live_detail(data)

        # normal mode
        if now < self.api_backoff_until:
            return None

        jitter = random.uniform(0, 30)

        if now - self.last_api_poll < API_POLL_INTERVAL_SECONDS + jitter:
            return None

        self.last_api_poll = now

        data = self.fetch_live_detail()
        return self.update_master_url_from_live_detail(data)

    def refresh_master_if_needed(self):
        """
        Refresh HLS master playlist when needed.
        """
        now = time.time()

        if not self.master_m3u8_url:
            return

        if (
            self.playlist_urls
            and now - self.last_master_refresh < MASTER_REFRESH_SECONDS
        ):
            return

        master_text = self.safe_get(
            self.master_m3u8_url,
            "hls master index.m3u8",
            headers={
                "Accept": "*/*",
                "Referer": f"{WEB_BASE}/",
                "x-api-key": STREAM_API_KEY,
            },
        )

        playlist_urls = extract_playlist_urls(
            master_text,
            self.master_m3u8_url,
        )

        if playlist_urls:
            self.playlist_urls = playlist_urls
            self.last_master_refresh = now

    def refresh_playlists_and_segments(self):
        """
        Refresh HLS media playlists and fetch latest media segments.

        For each media playlist:
          1. Fetch playlist
          2. Extract latest media segment
          3. Download only unseen segment
        """
        now = time.time()

        if now - self.last_playlist_refresh < HLS_PLAYLIST_REFRESH_SECONDS:
            return

        self.last_playlist_refresh = now

        if not self.playlist_urls:
            return

        for playlist_url in self.playlist_urls:
            media_type = detect_media_type(playlist_url)

            playlist_name = (
                "hls audio playlist"
                if media_type == "audio"
                else "hls video playlist"
            )

            playlist_text = self.safe_get(
                playlist_url,
                playlist_name,
                headers={
                    "Accept": "*/*",
                    "Origin": WEB_BASE,
                    "Referer": f"{WEB_BASE}/",
                    "x-api-key": STREAM_API_KEY,
                },
            )

            media_urls = extract_latest_media_urls(
                playlist_text,
                playlist_url,
                limit=LATEST_SEGMENT_LIMIT,
            )

            for media_url in media_urls:
                if media_url in self.seen_segments:
                    continue

                segment_type = detect_media_type(media_url)

                if "init" in media_url.lower():
                    name = (
                        "hls audio init segment"
                        if segment_type == "audio"
                        else "hls video init segment"
                    )
                else:
                    name = (
                        "hls audio segment"
                        if segment_type == "audio"
                        else "hls video segment"
                    )

                self.safe_get(
                    media_url,
                    name,
                    headers={
                        "Accept": "*/*",
                        "Referer": f"{WEB_BASE}/",
                    },
                )

                self.remember_segment(media_url)

    @task
    def real_live_viewer_flow(self):
        """
        Main virtual viewer flow.
        """
        self.fetch_live_page_once()
        self.poll_live_detail_if_needed()
        self.refresh_master_if_needed()
        self.refresh_playlists_and_segments()

        # Simulate viewer pacing based on selected TEST_PROFILE.
        time.sleep(
            random.uniform(
                TASK_SLEEP_MIN_SECONDS,
                TASK_SLEEP_MAX_SECONDS,
            )
        )
