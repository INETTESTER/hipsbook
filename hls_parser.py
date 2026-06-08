from urllib.parse import urljoin


def extract_playlist_urls(master_text: str | None, base_url: str) -> list[str]:
    """
    Extract media playlist URLs from an HLS master playlist.
    """
    if not master_text:
        return []

    playlist_urls: list[str] = []

    for line in master_text.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if ".m3u8" in line:
            playlist_urls.append(urljoin(base_url, line))

    return playlist_urls


def extract_latest_media_urls(
    playlist_text: str | None,
    base_url: str,
    limit: int = 1,
) -> list[str]:
    """
    Extract latest media segment URLs from an HLS media playlist.
    """
    if not playlist_text:
        return []

    media_extensions = (
        ".ts",
        ".m4s",
        ".mp4",
        ".aac",
        ".mp3",
        ".vtt",
    )

    media_urls: list[str] = []

    for line in playlist_text.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        lower_line = line.lower()

        if any(ext in lower_line for ext in media_extensions):
            media_urls.append(urljoin(base_url, line))

    return media_urls[-limit:]


def detect_media_type(url: str) -> str:
    """
    Detect media type from URL for Locust request naming.
    """
    lower_url = url.lower()

    if "audio" in lower_url:
        return "audio"

    if "subtitle" in lower_url or ".vtt" in lower_url:
        return "subtitle"

    return "video"