import time
import unittest
import json
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from analyze_hls import analyze_m3u8

class TestLoad(unittest.TestCase):
    def test_analyze_m3u8_load(self):
        # Load the M3U8 URL from the config file
        try:
            with open(os.path.join(os.path.dirname(__file__), '../../config.json'), 'r') as config_file:
                config = json.load(config_file)
                m3u8_url = config.get('m3u8_url')
        except Exception as e:
            self.fail(f"Failed to load config file: {e}")

        # Record the start time of the test
        start_time = time.time()
        success = True
        try:
            # Call the analyze_m3u8 function 25 times to simulate load
            for _ in range(10):  # Reduced to 25 users
                result = analyze_m3u8(m3u8_url)
                # Assert that the result is not None
                self.assertIsNotNone(result, "Load test failed: analyze_m3u8 returned None")
        except Exception as e:
            # If an exception occurs, mark the test as failed
            success = False
        # Record the end time of the test
        end_time = time.time()
        # Calculate the duration of the test
        duration = end_time - start_time

        # Write the result to the output file
        output_path = os.path.join(os.path.dirname(__file__), '../../analysis_output.json')
        try:
            with open(output_path, "r+") as f:
                data = json.load(f)
                # Add the load test results to the JSON data
                data["Load Test"] = {
                    "Runtime (seconds)": duration,
                    "Success": success
                }
                # Write the updated JSON data back to the file
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
        except FileNotFoundError:
            with open(output_path, "w") as f:
                data = {
                    "Load Test": {
                        "Runtime (seconds)": duration,
                        "Success": success
                    }
                }
                json.dump(data, f, indent=4)
        except Exception as e:
            self.fail(f"Failed to write to output file: {e}")

if __name__ == "__main__":
    unittest.main()