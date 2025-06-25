"""Youtube utilities for downloading audio and subtitles."""

import asyncio
import functools
import re
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Annotated, List

import httpx
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._transcripts import FetchedTranscript
from youtube_transcript_api.formatters import Formatter
from yt_dlp import YoutubeDL


class AudioSegment(BaseModel):
    """Audio segments with start and end times."""

    id: Annotated[int, "Unique identifier of the segment."]
    start: Annotated[float, "Start time of the segment in seconds."]
    end: Annotated[float, "End time of the segment in seconds."]
    text: Annotated[str, "Text content of the segment."]


class Transcription(BaseModel):
    """Transcription of audio with segments."""

    text: Annotated[str, "Transcribed text of the audio."] = ""
    segments: Annotated[list[AudioSegment], "List of audio segments."] = []


class TranscriptionFormatter(Formatter):
    """Custom formatter that converts FetchedTranscript to Transcription pydantic model."""

    def format_transcript(
        self, transcript: FetchedTranscript, **kwargs
    ) -> Transcription:
        """Convert a FetchedTranscript to Transcription pydantic model.

        Args:
            transcript: The FetchedTranscript object from youtube_transcript_api
            **kwargs: Additional keyword arguments (unused)

        Returns:
            Transcription: A Transcription pydantic model with segments having start/end times
        """
        segments = []
        full_text = ""

        for i, snippet in enumerate(transcript.snippets):
            # Convert start + duration to start + end format
            start_time = snippet.start
            end_time = snippet.start + snippet.duration
            text = snippet.text.strip()

            segments.append(
                AudioSegment(
                    id=i,
                    start=start_time,
                    end=end_time,
                    text=text,
                )
            )

            full_text += text + " "

        return Transcription(
            text=full_text.strip(),
            segments=segments,
        )

    def format_transcripts(
        self, transcripts: List[FetchedTranscript], **kwargs
    ) -> List[Transcription]:
        """Convert a list of FetchedTranscripts to a list of Transcription pydantic models.

        Args:
            transcripts: List of FetchedTranscript objects from youtube_transcript_api
            **kwargs: Additional keyword arguments (unused)

        Returns:
            List[Transcription]: A list of Transcription pydantic models
        """
        return [
            self.format_transcript(transcript, **kwargs) for transcript in transcripts
        ]


def fetch_youtube_transcription(video_url_or_id: str) -> Transcription:
    """Fetch YouTube transcript using youtube_transcript_api and convert to Transcription model.

    Args:
        video_url_or_id: YouTube video url or ID (11 characters)

    Returns:
        Transcription: A Transcription pydantic model with segments having start/end times

    Example:
        >>> transcription = fetch_youtube_transcript_as_transcription("dQw4w9WgXcQ")
        >>> isinstance(transcription, Transcription)
        True
        >>> len(transcription.segments) > 0
        True
    """
    video_id_match = re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", video_url_or_id)
    video_id = video_id_match.group(1) if video_id_match else video_url_or_id

    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)

    formatter = TranscriptionFormatter()
    return formatter.format_transcript(transcript)


def download_youtube_audio(
    url: str, download_subtitles: bool = False
) -> tuple[Path, list[dict] | None]:
    """Downloads audio from a YouTube URL and converts it to MP3 format.

    Optionally downloads subtitles with timestamps.

    Examples:
        >>> audio_path, subs = download_youtube_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        >>> isinstance(audio_path, Path)
        True
        >>> audio_path.suffix
        '.mp3'
        >>> audio_path, subs = download_youtube_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True)
        >>> isinstance(subs, list)
        True

    Args:
        url: The YouTube video URL to download audio from.
        download_subtitles: Whether to download and return subtitles. Defaults to False.

    Returns:
        tuple[Path, list[dict] | None]: A tuple containing:
            - Path to the downloaded and converted MP3 file
            - List of subtitle entries with timestamps if download_subtitles=True, None otherwise.
              Each subtitle entry is a dict with 'text' and 'start' keys.

    Raises:
        DownloadError: If the video cannot be downloaded
        PostProcessingError: If the audio conversion fails
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": f"{tempfile.gettempdir()}/%(title)s.%(ext)s",
        "writeautomaticsub": download_subtitles,
        "subtitlesformat": "json",
        "subtitleslangs": ["en"],
        "quiet": True,
        "no_warnings": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_path = Path(f"{tempfile.gettempdir()}/{info['title']}.mp3")

        if download_subtitles:
            subtitles = []
            if info.get("subtitles") or info.get("automatic_captions"):
                subs_data = info.get("subtitles", {}).get("en") or info.get(
                    "automatic_captions", {}
                ).get("en")
                if subs_data:
                    for entry in subs_data:
                        if "text" in entry and "start" in entry:
                            subtitles.append(
                                {"text": entry["text"], "start": entry["start"]}
                            )
            return audio_path, subtitles

        return audio_path, None


def get_youtube_info(url: str, ydl_opts: dict | None = None) -> dict:
    """Get YouTube video information.

    Args:
        url: The YouTube video URL to get information from.
        ydl_opts: Optional additional options for yt-dlp.

    Returns:
        A dictionary containing video information.
    """
    if ydl_opts is None:
        ydl_opts = {}

    with YoutubeDL(ydl_opts) as ydl:
        return ydl.sanitize_info(ydl.extract_info(url, download=False))


async def download_youtube_subtitles(
    url: str, language: str = "en", supress_ytdl_output: bool = True
) -> str:
    """Downloads and parses YouTube subtitles into AudioSegments format async.

    Args:
        url: The YouTube video URL to download subtitles from.
        language: The language code for the subtitles. Defaults to "en".
        supress_ytdl_output: Whether to suppress yt-dlp output. Defaults to True.

    Returns:
        The content of the downloaded subtitles in VTT format.
    """
    ydl_opts = {
        "skip_download": True,
        "writeautomaticsub": False,  # Download auto-generated subtitles if available
        "writesubtitles": True,  # NOTE: This is required to download the subtitles. But where does it save?
        "subtitlesformat": "vtt",
        "subtitleslangs": [language],
        "quiet": supress_ytdl_output,
        "no_warnings": supress_ytdl_output,
    }

    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as exc:
        info = await loop.run_in_executor(
            exc, functools.partial(get_youtube_info, url=url, ydl_opts=ydl_opts)
        )

    # Check if the requested subtitles are available
    requested_subs = info.get("requested_subtitles", None)

    if not requested_subs or language not in requested_subs:
        raise ValueError(f"Subtitles in {language} are not available for this video.")

    vtt_url = requested_subs.get(language).get("url")

    async with httpx.AsyncClient() as client:
        response = await client.get(vtt_url)
        response.raise_for_status()

    return response.text


def _vtt_time_to_seconds(vtt_time: str) -> float:
    """Convert VTT timestamp format to seconds.

    Args:
        vtt_time: VTT timestamp in format "HH:MM:SS.mmm"

    Returns:
        float: Time in seconds
    """
    parts = vtt_time.split(":")
    match len(parts):
        case 3:  # HH:MM:SS.mmm
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        case 2:  # MM:SS.mmm
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        case _:
            return float(vtt_time)


# TODO: Is there any faster way to parse the VTT file, without manually iterating through lines?
def convert_vtt_to_segments(vtt_content: str) -> Transcription:
    """Convert VTT content to a list of AudioSegment.

    Args:
        vtt_content: The content of the VTT file as a string.

    Returns:
        A list of AudioSegments.
    """
    # Parse VTT content into AudioSegments
    transcription = Transcription()
    lines = vtt_content.strip().split("\n")

    # Skip header lines
    i = 0
    while i < len(lines) and not lines[i].strip().replace("-->", "").strip():
        i += 1

    segment_id = 0
    while i < len(lines):
        # Skip empty lines
        if not lines[i].strip():
            i += 1
            continue

        # Parse timestamp line
        if "-->" in lines[i]:
            time_parts = lines[i].split("-->")
            start_time = _vtt_time_to_seconds(time_parts[0].strip())
            end_time = _vtt_time_to_seconds(time_parts[1].strip())

            # Collect the text content
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                # Replace &nbsp; with empty string
                text_line = lines[i].strip().replace("&nbsp;", "")
                text_lines.append(text_line)
                i += 1

            text = " ".join(text_lines)
            # Remove speaker indicators like "- " at the beginning
            text = text.lstrip("- ")

            transcription.text += text + " "

            transcription.segments.append(
                AudioSegment(id=segment_id, start=start_time, end=end_time, text=text)
            )
            segment_id += 1
        else:
            # Skip other non-timestamp lines
            i += 1

    return transcription
