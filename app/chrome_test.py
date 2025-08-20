import subprocess
import os


def debug_chrome_detailed():
    """Detailed Chrome debugging"""
    print("=== Chrome Debug Info ===")

    # Check if binaries exist and are executable
    chrome_path = "/usr/local/bin/google-chrome"
    driver_path = "/usr/local/bin/chromedriver"

    print(f"Chrome exists: {os.path.exists(chrome_path)}")
    print(f"Chrome executable: {os.access(chrome_path, os.X_OK)}")
    print(f"ChromeDriver exists: {os.path.exists(driver_path)}")
    print(f"ChromeDriver executable: {os.access(driver_path, os.X_OK)}")

    # Try running Chrome directly
    try:
        result = subprocess.run([chrome_path, "--version"],
                                capture_output=True, text=True, timeout=10)
        print(f"Chrome version output: {result.stdout}")
        print(f"Chrome stderr: {result.stderr}")
        print(f"Chrome return code: {result.returncode}")
    except Exception as e:
        print(f"Chrome direct run failed: {e}")

    # Try running ChromeDriver
    try:
        result = subprocess.run([driver_path, "--version"],
                                capture_output=True, text=True, timeout=10)
        print(f"ChromeDriver version: {result.stdout}")
        print(f"ChromeDriver stderr: {result.stderr}")
    except Exception as e:
        print(f"ChromeDriver run failed: {e}")

    # Check dependencies
    try:
        result = subprocess.run(["ldd", chrome_path],
                                capture_output=True, text=True)
        missing_deps = [line for line in result.stdout.split(
            '\n') if 'not found' in line]
        if missing_deps:
            print(f"Missing dependencies: {missing_deps}")
        else:
            print("All Chrome dependencies found")
    except Exception as e:
        print(f"Dependency check failed: {e}")


# Call this before creating driver
debug_chrome_detailed()
