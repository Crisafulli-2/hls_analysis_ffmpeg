import concurrent.futures
import subprocess
import time
import os
import sys

def run_test(test_script):
    """Run a test script and return the result with execution time."""
    test_name = test_script.split('.')[-1]
    
    # Define manual test purposes
    test_purposes = {
        'test_functional': "Test basic functionality of HLS analysis: URL accessibility and bitrate presence",
        'test_performance': "Using TTLB and TTFB as an example",
        'test_load': "Call m3u8 25 times to represent numerous users"
    }
    
    # Get the purpose from our manual mapping
    purpose = test_purposes.get(test_name, f"Tests for {test_name}")
    
    print(f"\nRunning {test_name}...")
    start_time = time.time()
    
    try:
        result = subprocess.run(['python3', '-m', 'unittest', test_script], capture_output=True, text=True)
        execution_time = time.time() - start_time
        
        return {
            'script': test_script,
            'name': test_name,
            'purpose': purpose,
            'execution_time': execution_time,
            'output': result.stdout,
            'error': result.stderr,
            'success': result.returncode == 0
        }
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            'script': test_script,
            'name': test_name,
            'purpose': purpose,
            'execution_time': execution_time,
            'output': '',
            'error': str(e),
            'success': False
        }

def format_time(seconds):
    """Format time in seconds to a readable string."""
    if seconds < 1:
        return f"{seconds*1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"

def main():
    test_scripts = [
        'tests.functional.test_functional',
        'tests.performance.test_performance',
        'tests.load.test_load'
    ]

    results = []
    print("\n===== RUNNING HLS ANALYSIS TESTS =====\n")

    # Run tests asynchronously
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_test, script) for script in test_scripts]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Print results to terminal
    print("\n===== TEST RESULTS =====\n")
    
    # Count successes and failures
    success_count = sum(1 for r in results if r['success'])
    
    for idx, result in enumerate(results, 1):
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"Test {idx}: {result['name']} - {status}")
        print(f"Purpose: {result['purpose']}")
        print(f"Execution time: {format_time(result['execution_time'])}")
        
        # Print errors if any
        if not result['success']:
            print("\nError output:")
            print(result['error'] if result['error'] else result['output'])
        print("-" * 50)
    
    # Print summary
    print(f"\nSummary: {success_count}/{len(results)} tests passed")
    
    # Return non-zero exit code if any tests failed
    if success_count < len(results):
        sys.exit(1)

if __name__ == "__main__":
    main()