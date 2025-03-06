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
    "AVFoundation_Metrics": {
        "indicatedBitrate": 2.45,
        "observedBitrate": 2.37,
        "numberOfStalls": 0,
        "startupTime": 0.354,
        "...": "..."
    },
    "FFprobe_Metrics": {
        "...": "..."
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- FFmpeg team for their excellent media analysis tools
- Apple for the AVFoundation framework
