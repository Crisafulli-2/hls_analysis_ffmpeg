import time
import unittest
import json
import os
import sys
import requests
from urllib.request import urlopen

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from analyze_hls import analyze_m3u8

class TestPerformance(unittest.TestCase):
    def test_analyze_m3u8_performance(self):
        """Using TTLB and TTFB as an example"""
        # Load the M3U8 URL from the config file
        try:
            with open(os.path.join(os.path.dirname(__file__), '../../config.json'), 'r') as config_file:
                config = json.load(config_file)
                m3u8_url = config.get('m3u8_url')
                if not m3u8_url:
                    self.skipTest("No m3u8_url found in config file")
        except Exception as e:
            self.fail(f"Failed to load config file: {e}")

        # Test 1: Measure TTFB (Time To First Byte)
        print("\nMeasuring TTFB (Time To First Byte)...")
        ttfb_start = time.time()
        
        try:
            # Open connection for TTFB measurement
            conn = urlopen(m3u8_url)
            # Reading first byte indicates TTFB
            first_byte = conn.read(1)
            ttfb_end = time.time()
            ttfb = ttfb_end - ttfb_start
            
            print(f"TTFB: {ttfb:.4f} seconds")
            # TTFB should typically be under 1 second for a well-performing CDN
            self.assertLess(ttfb, 1.0, f"TTFB performance test failed: {ttfb:.4f}s is too slow")
            
            # Continue reading to ensure we close the connection properly
            remaining = conn.read()
            conn.close()
        except Exception as e:
            self.fail(f"TTFB test failed with error: {e}")

        # Test 2: Measure TTLB (Time To Last Byte)
        print("Measuring TTLB (Time To Last Byte)...")
        ttlb_start = time.time()
        
        try:
            # For TTLB we measure the full download time of the manifest
            response = requests.get(m3u8_url)
            ttlb_end = time.time()
            ttlb = ttlb_end - ttlb_start
            
            print(f"TTLB: {ttlb:.4f} seconds")
            # TTLB should typically be under 2 seconds for a manifest file
            self.assertLess(ttlb, 2.0, f"TTLB performance test failed: {ttlb:.4f}s is too slow")
            
            # Ensure we got valid content
            self.assertTrue(response.text.startswith('#EXTM3U'), 
                           "Response doesn't appear to be a valid M3U8 file")
        except Exception as e:
            self.fail(f"TTLB test failed with error: {e}")
            
        # Test 3: Measure analyze_m3u8 function execution time
        print("Measuring analyze_m3u8 function execution time...")
        analyze_start = time.time()
        
        try:
            # Call the analyze_m3u8 function with the M3U8 URL
            result = analyze_m3u8(m3u8_url)
            analyze_end = time.time()
            analyze_duration = analyze_end - analyze_start
            
            print(f"Analysis time: {analyze_duration:.4f} seconds")
            # Function execution should be reasonably quick
            self.assertLess(analyze_duration, 5.0, 
                          f"Analysis performance test failed: {analyze_duration:.4f}s is too slow")
        except Exception as e:
            self.fail(f"Analysis function test failed with error: {e}")
            
        # Print overall performance summary
        print("\nPerformance Summary:")
        print(f"- Time To First Byte (TTFB): {ttfb:.4f}s")
        print(f"- Time To Last Byte (TTLB): {ttlb:.4f}s")
        print(f"- Full Analysis Time: {analyze_duration:.4f}s")


if __name__ == "__main__":
    unittest.main()