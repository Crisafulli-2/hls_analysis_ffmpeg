import subprocess
import json
import sys
import requests
import re

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

def check_network(input_file):
    """Validate HLS playlist and segments"""

    # Detect if input is a URL or a local file
    if input_file.startswith("http"):
        try:
            # Fetch the M3U8 file from the URL
            response = requests.get(input_file, timeout=10)
            response.raise_for_status()  # Raise error if response is not 200
            content = response.text
        except requests.exceptions.RequestException as e:
            return {"Error": f"Failed to fetch M3U8 file: {str(e)}"}
    else:
        try:
            # Read the M3U8 file from the local file system
            with open(input_file, "r") as file:
                content = file.read()
        except FileNotFoundError:
            return {"Error": f"File not found: {input_file}"}

    try:
        # Extract segment URLs from the M3U8 content
        segment_urls = re.findall(r'(https?://[^\s]+\.ts)', content)
        failed_segments = []

        # Check the availability of each segment URL
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
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_hls.py <input file>")
        sys.exit(1)

    input_file = sys.argv[1]
    file_ext = input_file.split('.')[-1]

    results = {}

    # Analyze bitrate for supported video file types
    if file_ext in ["mp4", "mpeg", "ts"]:
        results.update(analyze_bitrate(input_file))
    elif file_ext == "m3u8":
        results.update(analyze_bitrate(input_file))
        results.update(check_network(input_file))
    else:
        print("Unsupported file type. Only MP4, MPEG-2, and M3U8 are supported.")
        sys.exit(1)

    # Save the analysis results to a JSON file
    with open("analysis_output.json", "w") as f:
        json.dump(results, f, indent=4)

    print("Analysis complete! Results saved to analysis_output.json.")

if __name__ == "__main__":
    main()