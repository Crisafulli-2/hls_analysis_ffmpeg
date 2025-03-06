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
        # Fetch the M3U8 file
        response = requests.get(input_file)
        response.raise_for_status()
        content = response.text
        
        # Extract stream information from the M3U8 file
        stream_info = re.findall(r'#EXT-X-STREAM-INF:BANDWIDTH=(\d+),CODECS="([^"]+)",RESOLUTION=(\d+x\d+),FRAME-RATE=(\d+),VIDEO-RANGE=(\w+)', content)
        
        if not stream_info:
            return {"Error": "No stream information found in the M3U8 file"}
        
        # Calculate bitrates and other metrics
        bitrates = [int(info[0]) for info in stream_info]
        highest_bitrate = max(bitrates) / 1_000_000  # Convert to Mbps
        lowest_bitrate = min(bitrates) / 1_000_000   # Convert to Mbps
        avg_bitrate = sum(bitrates) / len(bitrates) / 1_000_000  # Convert to Mbps
        
        # Extract other stream information
        codec = stream_info[0][1]
        resolution = stream_info[0][2]
        frame_rate = stream_info[0][3]
        video_range = stream_info[0][4]
        
        # Check if all segments are accessible
        segment_urls = re.findall(r'^(?!#)(.+\.ts)$', content, re.MULTILINE)
        base_url = '/'.join(input_file.split('/')[:-1]) + '/'
        
        failed_segments = []
        for segment in segment_urls:
            segment_url = base_url + segment if not segment.startswith('http') else segment
            try:
                segment_response = requests.head(segment_url, timeout=5)
                if segment_response.status_code != 200:
                    failed_segments.append(segment_url)
            except requests.exceptions.RequestException:
                failed_segments.append(segment_url)
        
        network_check = "All segments available" if not failed_segments else f"{len(failed_segments)} segments unavailable"
        
        # Compile results
        results = {
            "Highest Bitrate (Mbps)": round(highest_bitrate, 3),
            "Average Bitrate (Mbps)": round(avg_bitrate, 4),
            "Lowest Bitrate (Mbps)": round(lowest_bitrate, 3),
            "Codec": codec,
            "Resolution": resolution,
            "Frame Rate": frame_rate,
            "Video Range": video_range,
            "Network Check": network_check,
            "Failed Segments": failed_segments
        }
        
        return results
    except Exception as e:
        return {"Error": f"M3U8 analysis failed: {str(e)}"}

def main():
    """Main function to run the analysis"""
    try:
        # Load the M3U8 URL from config.json
        config_path = 'config.json'  # Keep using the root path for config.json
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            m3u8_url = config.get('m3u8_url')
            
        if not m3u8_url:
            print("Error: M3U8 URL not found in config.json")
            sys.exit(1)
            
        print(f"Analyzing M3U8: {m3u8_url}")
        
        # Run the M3U8 analysis
        ffprobe_metrics = analyze_m3u8(m3u8_url)
        
        # Create output directory if it doesn't exist
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        
        # Path to main output JSON
        output_path = os.path.join(output_dir, 'analysis_output.json')
        
        # Check if the output file exists and load existing data
        try:
            with open(output_path, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        
        # Add or update the FFprobe metrics
        data['FFprobe_Metrics'] = ffprobe_metrics
        
        # Save the updated file
        with open(output_path, 'w') as output_file:
            json.dump(data, output_file, indent=4)
            
        print("Analysis complete")
        print(f"Results saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()