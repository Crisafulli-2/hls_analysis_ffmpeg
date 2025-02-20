# HLS Analysis

This project provides a script to analyze HLS (HTTP Live Streaming) playlists and video files using FFmpeg. The script can extract bitrate and frame rate information from video files and validate the availability of HLS segments.

## Requirements

- Python 3.x
- FFmpeg (including `ffprobe`)
- Required Python packages: `requests`

## Installation

1. Install FFmpeg:
   - On macOS, use Homebrew:
     ```sh
     brew install ffmpeg
     ```
   - On Ubuntu, use APT:
     ```sh
     sudo apt update
     sudo apt install ffmpeg
     ```

2. Install the required Python packages:
   ```sh
   pip install requests