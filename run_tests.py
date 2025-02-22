import concurrent.futures
import subprocess
import json
import os

def run_test(test_script):
    """Run a test script and return the result."""
    try:
        result = subprocess.run(['python3', '-m', 'unittest', test_script], capture_output=True, text=True)
        return {
            'script': test_script,
            'output': result.stdout,
            'error': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {
            'script': test_script,
            'output': '',
            'error': str(e),
            'returncode': 1
        }

def main():
    test_scripts = [
        'tests.functional.test_functional',
        'tests.performance.test_performance',
        'tests.load.test_load'
    ]

    results = []

    # Run tests asynchronously
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_test, script) for script in test_scripts]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Write the results to the output file
    output_path = os.path.join(os.path.dirname(__file__), 'test_results.json')
    try:
        with open(output_path, 'r+') as f:
            data = json.load(f)
            data['Test Results'] = results
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
    except FileNotFoundError:
        with open(output_path, 'w') as f:
            data = {'Test Results': results}
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to write to output file: {e}")

if __name__ == "__main__":
    main()