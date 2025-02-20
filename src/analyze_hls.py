import subprocess
import json
import sys
import requests
import re
import os

def analyze_bitrate(input_file):
    """Analyze bitrate using FFprobe"""
    # Command to run FFprobe and extract bitrate and frame rate information
    cmd = [
        "ffprobe", "-i", input_file, "-select_streams", "v",
        "-show_entries", "stream=bit_rate,avg_frame_rate", "-show_format",
        "-print_format", "json"
    ]
    try:
        # Run the command and capture the output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        # Extract average bitrate and frame rate from the output
        avg_bitrate = data["streams"][0].get("bit_rate", "Unknown")
        frame_rate = data["streams"][0].get("avg_frame_rate", "Unknown")
        
        return {"Average Bitrate": avg_bitrate, "Frame Rate": frame_rate}
    except Exception as e:
        return {"Error": f"Bitrate analysis failed: {str(e)}"}

def analyze_m3u8(input_file):
    """Analyze M3U8 file and its segments"""
    try:
        if input_file.startswith("http"):
            response = requests.get(input_file, timeout=10)
            response.raise_for_status()
            content = response.text
        else:
            with open(input_file, "r") as file:
                content = file.read()
        
        # Extract BANDWIDTH, CODECS, RESOLUTION, FRAME-RATE, and VIDEO-RANGE from the M3U8 content
        stream_info = re.findall(r'#EXT-X-STREAM-INF:BANDWIDTH=(\d+),CODECS="([^"]+)",RESOLUTION=(\d+x\d+),FRAME-RATE=(\d+),VIDEO-RANGE=(\w+)', content)
        
        # Initialize lists to store extracted values
        bitrates = []
        codecs = []
        resolutions = []
        frame_rates = []
        video_ranges = []

        # Extract values from the stream information
        for bandwidth, codec, resolution, frame_rate, video_range in stream_info:
            bitrates.append(int(bandwidth))
            codecs.append(codec)
            resolutions.append(resolution)
            frame_rates.append(frame_rate)
            video_ranges.append(video_range)

        # Calculate average, highest, and lowest bitrate in Mbps
        avg_bitrate = sum(bitrates) / len(bitrates) / 1_000_000 if bitrates else "Unknown"
        highest_bitrate = max(bitrates) / 1_000_000 if bitrates else "Unknown"
        lowest_bitrate = min(bitrates) / 1_000_000 if bitrates else "Unknown"
        # Use the first value for codecs, resolution, frame rate, and video range as an example
        codec = codecs[0] if codecs else "Unknown"
        resolution = resolutions[0] if resolutions else "Unknown"
        frame_rate = frame_rates[0] if frame_rates else "Unknown"
        video_range = video_ranges[0] if video_ranges else "Unknown"

        return {
            "Highest Bitrate (Mbps)": highest_bitrate,
            "Average Bitrate (Mbps)": avg_bitrate,
            "Lowest Bitrate (Mbps)": lowest_bitrate,
            "Codec": codec,
            "Resolution": resolution,
            "Frame Rate": frame_rate,
            "Video Range": video_range
        }
    except Exception as e:
        return {"Error": f"M3U8 analysis failed: {str(e)}"}

def check_network(input_file):
    """Validate HLS playlist and segments"""
    if input_file.startswith("http"):
        try:
            response = requests.get(input_file, timeout=10)
            response.raise_for_status()
            content = response.text
        except requests.exceptions.RequestException as e:
            return {"Error": f"Failed to fetch M3U8 file: {str(e)}"}
    else:
        try:
            with open(input_file, "r") as file:
                content = file.read()
        except FileNotFoundError:
            return {"Error": f"File not found: {input_file}"}

    try:
        segment_urls = re.findall(r'(https?://[^\s]+\.ts)', content)
        failed_segments = []

        for url in segment_urls:
            response = requests.head(url)
            if response.status_code != 200:
                failed_segments.append(url)

        return {
            "Network Check": "All segments available" if not failed_segments else "Missing segments",
            "Failed Segments": failed_segments
        }
    except Exception as e:
        return {"Error": f"Network validation failed: {str(e)}"}

def main():
    # Load the M3U8 URL from the config file
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
        input_file = config.get('m3u8_url')

    if not input_file:
        print("M3U8 URL not found in config file.")
        sys.exit(1)

    file_ext = input_file.split('.')[-1]

    results = {}

    if file_ext in ["mp4", "mpeg", "ts"]:
        results.update(analyze_bitrate(input_file))
    elif file_ext == "m3u8":
        results.update(analyze_m3u8(input_file))
        results.update(check_network(input_file))
    else:
        print("Unsupported file type. Only MP4, MPEG-2, and M3U8 are supported.")
        sys.exit(1)

    output_path = os.path.join(os.path.dirname(__file__), '../output/analysis_output.json')
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)

    print("Analysis complete! Results saved to analysis_output.json.")

if __name__ == "__main__":
    main()