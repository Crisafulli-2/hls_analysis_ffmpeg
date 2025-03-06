import unittest
import json
import os
import sys
import requests

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from analyze_hls import analyze_m3u8

class TestFunctional(unittest.TestCase):
    def test_analyze_m3u8_functionality(self):
        """Test basic functionality of HLS analysis: URL accessibility and bitrate presence"""
        # Load the M3U8 URL from the config file
        try:
            with open(os.path.join(os.path.dirname(__file__), '../../config.json'), 'r') as config_file:
                config = json.load(config_file)
                m3u8_url = config.get('m3u8_url')
                if not m3u8_url:
                    self.skipTest("No m3u8_url found in config file")
        except Exception as e:
            self.fail(f"Failed to load config file: {e}")

        # Test 1: Check if the M3U8 URL is accessible
        try:
            response = requests.get(m3u8_url, timeout=10)
            self.assertEqual(response.status_code, 200, f"M3U8 URL is not accessible: {m3u8_url}")
            self.assertTrue(response.text.startswith('#EXTM3U'), "Response doesn't appear to be a valid M3U8 file")
        except requests.RequestException as e:
            self.fail(f"Failed to access M3U8 URL: {e}")

        # Test 2: Verify bitrate information is available
        try:
            result = analyze_m3u8(m3u8_url)
            
            # Simply check if bitrate keys exist in the result
            self.assertIn("Average Bitrate (Mbps)", result, 
                         "Test failed: 'Average Bitrate (Mbps)' not found in result")
            self.assertIn("Highest Bitrate (Mbps)", result, 
                         "Test failed: 'Highest Bitrate (Mbps)' not found in result")
            self.assertIn("Lowest Bitrate (Mbps)", result, 
                         "Test failed: 'Lowest Bitrate (Mbps)' not found in result")
            
            # Log the values found (without validation)
            print(f"\nFound bitrate information in the HLS stream")
            
        except Exception as e:
            self.fail(f"Error analyzing M3U8 stream: {e}")

if __name__ == "__main__":
    unittest.main()