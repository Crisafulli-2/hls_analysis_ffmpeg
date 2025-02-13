# HLS Analysis with FFmpeg

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

   Usage
Run the script with the input file (either a video file or an HLS playlist):

python3 analyze_hls.py <input file>
Supported file types:

MP4
MPEG-2
M3U8
The analysis results will be saved to analysis_output.json.

Example
python3 analyze_hls.py example.m3u8

Output
The output will be saved in analysis_output.json with the following structure:

{
    "Average Bitrate": "Unknown",
    "Frame Rate": "24/1",
    "Network Check": "All segments available",
    "Failed Segments": []
}