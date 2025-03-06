# HLS Analysis Tool

## Project Overview

This project provides tools for analyzing HLS (HTTP Live Streaming) video streams across multiple platforms. It combines the power of FFmpeg's analysis capabilities with native macOS AVFoundation playback to provide comprehensive metrics about HLS streams.

## Key Features

- **Stream Analysis**: Extract technical details from HLS streams using FFprobe
- **Native Playback**: Play HLS streams directly using macOS AVFoundation
- **Metrics Collection**: Gather real-time streaming performance metrics
- **Performance Testing**: Tools to verify stream functionality and performance

## Project Structure

```
hls_analysis_ffmpeg/
├── src/                      # Main source code
│   ├── analyze_hls.py        # FFprobe-based stream analyzer
│   ├── core/                 # Core functionality
│   │   ├── hls_player.py     # macOS native HLS player using AVFoundation
│   │   └── ...
│   └── ...
├── tests/                    # Test suite
│   ├── functional_tests/     # Tests for stream loading functionality
│   ├── performance_tests/    # Tests for streaming performance
│   └── ...
├── output/                   # Output directory for collected metrics
├── analyze_hls_output.json   # JSON file containing collected metrics
├── config.json               # Configuration file (contains m3u8 URL)
├── README.md                 # Project documentation
└── run_tests.py              # Test runner script
```

## Installation

### Prerequisites

- Python 3.6+
- FFmpeg/FFprobe (for analyze_hls.py)
- macOS with PyObjC (for hls_player.py)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hls_analysis_ffmpeg.git
cd hls_analysis_ffmpeg
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your stream URL in `config.json`:
```json
{
    "m3u8_url": "https://your-stream-url.m3u8"
}
```

## Usage

### Analyzing a Stream with FFprobe

```bash
python3 src/analyze_hls.py
```

This will analyze the HLS stream specified in `config.json` and output technical details to the terminal and the `analyze_hls_output.json` file.

### Playing a Stream with AVFoundation (macOS only)

```bash
python3 src/core/hls_player.py
```

This will:
1. Launch a native macOS player window
2. Load and play the HLS stream specified in `config.json`
3. Collect streaming performance metrics in real-time
4. Save the metrics to `analyze_hls_output.json` when playback ends

### Running Tests

```bash
python3 run_tests.py
```

## Metrics Collected

The tool collects various metrics depending on the analysis method:

### FFprobe Metrics
- Stream format
- Codec details
- Bitrate information
- Resolution
- Duration
- Container format

### AVFoundation Metrics (macOS only)
- **Bitrate**: Current bitrate, observed bitrate, average audio/video bitrate
- **Duration**: Startup time, watched duration, transfer duration
- **Statistics**: Number of stalls, segments downloaded, bytes transferred
- **Server**: Server address, playback session ID

## Output Format

Metrics are saved to `analyze_hls_output.json` in the following format:

```json
{
    "FFprobe_Metrics": {
        "Highest Bitrate (Mbps)": 2.468,
        "Average Bitrate (Mbps)": 2.097,
        "Lowest Bitrate (Mbps)": 1.727,
        "Codec": "mp4a.40.2,avc1.100.40",
        "Resolution": "1680x750",
        "Frame Rate": "24",
        "Video Range": "SDR",
        "Network Check": "All segments available",
        "Failed Segments": []
    },
    "AVFoundation_Metrics": {
        "Bitrate": {
            "observedBitrate": 19.065,
            "averageVideoBitrate": 2.165,
            "averageAudioBitrate": 0.0,
            "indicatedBitrate": 2.468
        },
        "Duration": {
            "transferDuration": 12.532,
            "startupTime": 5.324,
            "durationWatched": 10.726,
            "segmentsDownloadedDuration": 140.0,
            "InitialBufferingTime": 5.32
        },
        "Statistics": {
            "numberOfDroppedVideoFrames": 0,
            "numberOfSegmentsDownloaded": 35,
            "numberOfMediaRequests": 35,
            "numberOfStalls": 0,
            "numberOfBytesTransferred": 37880872,
            "numberOfServerAddressChanges": 0,
            "BufferingEvents": 0
        },
        "Server": {
            "serverAddress": "46.23.86.222",
            "playbackSessionID": "E31E2DBA-F8AB-42A0-BADE-E3DF2C35BB5D"
        },
        "PlayerEvents": {
            "PlayCount": 8,
            "PauseCount": 7,
            "PlayEvents": [],
            "PauseEvents": []
        }
    }
}
```

## Development

### Creating a New Feature

1. Create a new branch:
```bash
git checkout -b feature-name
```

2. Make your changes

3. Push to GitHub and create a PR:
```bash
git push -u origin feature-name
```

## Platform Support

- **Stream Analysis**: Works on all platforms (macOS, Linux, Windows) with FFmpeg installed
- **Native Playback**: macOS only (requires PyObjC and AVFoundation)

## Future Scope

### Performance and Resource Optimization
- **HTTP Session Reuse**: Implement connection pooling to reduce overhead when making multiple requests to the same server
- **Parallel Downloads**: Use async I/O or threading to download multiple segments simultaneously
- **Caching**: Add intelligent caching of manifests and segments to reduce redundant downloads
- **Smart Retry Logic**: Implement exponential backoff for retries to handle temporary network issues efficiently

### Testing Enhancements
- **Unit Test Coverage**: Develop comprehensive unit tests for each component (parser, downloader, analyzer)
- **Mocking External Services**: Use mocking frameworks to simulate different server behaviors and edge cases
- **Parameterized Testing**: Add tests with different input types to ensure robustness
- **CI Integration**: Set up GitHub Actions workflow for automated testing on every push
- **Coverage Analysis**: Add code coverage reporting to identify untested parts of the codebase

### Feature Expansion
- **Live Stream Analytics**: Add specialized metrics for live streams (latency, segment availability)
- **Multi-CDN Support**: Track performance across different CDNs for the same content
- **Adaptive Bitrate Analysis**: Analyze ABR performance under different network conditions
- **Video Quality Metrics**: Integrate with tools to assess perceptual quality metrics (VMAF, PSNR)
- **Historical Data Tracking**: Store and visualize performance trends over time

### User Experience
- **Interactive Dashboard**: Build a web-based dashboard for visualizing stream metrics
- **Alerting System**: Implement alerts for performance degradation or streaming issues
- **CLI Improvements**: Enhance command line interface with more options and better output formatting
- **Batch Processing**: Add support for analyzing multiple streams in batch mode


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- FFmpeg team for their excellent media analysis tools
- Apple for the AVFoundation framework
