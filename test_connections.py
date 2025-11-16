#!/usr/bin/env python3
"""
Test script to verify configuration, Ollama, and API connections.
Run this to ensure all services are properly configured before running SCRIBE.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import yaml

# Load environment variables
load_dotenv()


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name: str, success: bool, message: str = ""):
    """Print test result with color coding."""
    status = "PASS" if success else "FAIL"
    symbol = "[+]" if success else "[-]"
    print(f"{symbol} {test_name}: {status}")
    if message:
        print(f"    {message}")


def test_environment_variables():
    """Test that required environment variables are set."""
    print_header("ENVIRONMENT VARIABLES")

    results = {}

    # Required variables
    required_vars = [
        ("REDDIT_CLIENT_ID", "Reddit API"),
        ("REDDIT_CLIENT_SECRET", "Reddit API"),
        ("YOUTUBE_API_KEY", "YouTube API"),
    ]

    # Optional variables
    optional_vars = [
        ("OLLAMA_HOST", "Ollama (default: http://localhost:11434)"),
        ("DISCORD_WEBHOOK_URL", "Discord notifications"),
    ]

    all_required_present = True

    print("\nRequired variables:")
    for var_name, description in required_vars:
        value = os.getenv(var_name)
        if value:
            # Mask the value for security
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print_result(f"{var_name} ({description})", True, f"Value: {masked}")
            results[var_name] = True
        else:
            print_result(f"{var_name} ({description})", False, "Not set")
            results[var_name] = False
            all_required_present = False

    print("\nOptional variables:")
    for var_name, description in optional_vars:
        value = os.getenv(var_name)
        if value:
            masked = value[:20] + "..." if len(value) > 20 else value
            print_result(f"{var_name} ({description})", True, f"Value: {masked}")
        else:
            print_result(f"{var_name} ({description})", False, "Not set (using default or disabled)")

    return all_required_present


def test_configuration_files():
    """Test that configuration files exist and are valid."""
    print_header("CONFIGURATION FILES")

    config_files = [
        "config/settings.yaml",
        "config/ollama_config.yaml",
    ]

    all_valid = True
    configs = {}

    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    configs[config_file] = config_data
                print_result(f"{config_file}", True, f"Valid YAML with {len(config_data)} top-level keys")
            except yaml.YAMLError as e:
                print_result(f"{config_file}", False, f"Invalid YAML: {e}")
                all_valid = False
        else:
            print_result(f"{config_file}", False, "File not found")
            all_valid = False

    # Validate key configuration entries
    if "config/settings.yaml" in configs:
        settings = configs["config/settings.yaml"]
        print("\nConfiguration details:")

        if "reddit" in settings:
            subreddits = settings["reddit"].get("subreddits", [])
            print(f"    - Reddit subreddits configured: {len(subreddits)}")

        if "youtube" in settings:
            keywords = settings["youtube"].get("keywords", [])
            channels = settings["youtube"].get("channels", [])
            print(f"    - YouTube keywords: {len(keywords)}")
            print(f"    - YouTube channels: {len(channels)}")

        if "analysis" in settings:
            categories = settings["analysis"].get("categories", [])
            print(f"    - Analysis categories: {len(categories)}")

        if "report" in settings:
            language = settings["report"].get("language", "en")
            print(f"    - Report language: {language}")

    if "config/ollama_config.yaml" in configs:
        ollama_config = configs["config/ollama_config.yaml"]
        model = ollama_config.get("model", "unknown")
        print(f"    - Ollama model: {model}")

    return all_valid


def test_ollama_connection():
    """Test connection to Ollama service."""
    print_header("OLLAMA CONNECTION")

    try:
        import ollama

        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        print(f"Connecting to Ollama at: {host}")

        # Create client
        client = ollama.Client(host=host)

        # Test 1: List available models
        print("\nAvailable models:")
        models_response = client.list()

        # Handle different response formats (dict, list, or Pydantic object)
        model_list = []
        if isinstance(models_response, dict) and "models" in models_response:
            model_list = models_response["models"]
        elif isinstance(models_response, list):
            model_list = models_response
        elif hasattr(models_response, 'models'):
            # Handle Pydantic object-style response
            model_list = models_response.models

        if model_list:
            model_names = []
            for model in model_list:
                # Handle different model info formats
                if isinstance(model, dict):
                    model_name = model.get("name") or model.get("model") or str(model)
                elif hasattr(model, 'model'):
                    # Pydantic Model object
                    model_name = model.model
                else:
                    model_name = str(model)
                model_names.append(model_name)
                print(f"    - {model_name}")
            print_result("List models", True, f"Found {len(model_list)} models")
        else:
            print_result("List models", False, "No models found")
            return False

        # Test 2: Check if configured model is available
        with open("config/ollama_config.yaml", 'r', encoding='utf-8') as f:
            ollama_config = yaml.safe_load(f)

        configured_model = ollama_config.get("model", "qwen3:14b")

        # Check both exact match and base name match
        model_available = any(
            configured_model in name or name.startswith(configured_model.split(":")[0])
            for name in model_names
        )

        if model_available:
            print_result(f"Configured model ({configured_model})", True, "Model is available")
        else:
            print_result(f"Configured model ({configured_model})", False,
                        f"Model not found. Available: {', '.join(model_names[:5])}")
            return False

        # Test 3: Simple generation test
        print("\nTesting text generation...")
        response = client.generate(
            model=configured_model,
            prompt="Say 'Hello' in one word.",
            options={"num_predict": 10}
        )

        if response and "response" in response:
            generated_text = response["response"].strip()[:50]
            print_result("Text generation", True, f"Response: {generated_text}")
        else:
            print_result("Text generation", False, "No response received")
            return False

        return True

    except ImportError:
        print_result("Ollama library", False, "ollama package not installed")
        return False
    except Exception as e:
        print_result("Ollama connection", False, f"Error: {str(e)}")
        return False


def test_reddit_api():
    """Test Reddit API connection."""
    print_header("REDDIT API")

    try:
        import praw

        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")

        if not client_id or not client_secret:
            print_result("Reddit credentials", False, "Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET")
            return False

        print("Connecting to Reddit API...")

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="SCRIBE:ConfigTest:v1.0 (connection test)"
        )

        # Test 1: Check if read-only mode works
        print_result("Read-only mode", reddit.read_only, "Connected in read-only mode")

        # Test 2: Fetch a single post from r/test
        print("Fetching test post from r/test...")
        subreddit = reddit.subreddit("test")
        posts = list(subreddit.hot(limit=1))

        if posts:
            post = posts[0]
            print_result("Fetch posts", True, f"Retrieved post: {post.title[:50]}...")
        else:
            print_result("Fetch posts", False, "No posts retrieved")
            return False

        # Test 3: Check rate limit info
        print(f"\nRate limit remaining: {reddit.auth.limits.get('remaining', 'N/A')}")
        print(f"Rate limit reset: {reddit.auth.limits.get('reset_timestamp', 'N/A')}")

        return True

    except ImportError:
        print_result("PRAW library", False, "praw package not installed")
        return False
    except Exception as e:
        print_result("Reddit API", False, f"Error: {str(e)}")
        return False


def test_youtube_api():
    """Test YouTube API connection."""
    print_header("YOUTUBE API")

    try:
        from googleapiclient.discovery import build

        api_key = os.getenv("YOUTUBE_API_KEY")

        if not api_key:
            print_result("YouTube credentials", False, "Missing YOUTUBE_API_KEY")
            return False

        print("Connecting to YouTube API...")

        youtube = build("youtube", "v3", developerKey=api_key)

        # Test 1: Search for a video
        print("Performing test search...")
        request = youtube.search().list(
            part="snippet",
            q="artificial intelligence",
            type="video",
            maxResults=1
        )
        response = request.execute()

        if response and "items" in response and len(response["items"]) > 0:
            video = response["items"][0]
            title = video["snippet"]["title"][:50]
            print_result("Search API", True, f"Found: {title}...")
        else:
            print_result("Search API", False, "No results returned")
            return False

        # Test 2: Check quota info (via response metadata)
        print(f"\nPage info: {response.get('pageInfo', {})}")

        return True

    except ImportError:
        print_result("Google API library", False, "google-api-python-client not installed")
        return False
    except Exception as e:
        error_msg = str(e)
        if "quotaExceeded" in error_msg:
            print_result("YouTube API", False, "API quota exceeded")
        elif "API key not valid" in error_msg or "forbidden" in error_msg.lower():
            print_result("YouTube API", False, "Invalid API key")
        else:
            print_result("YouTube API", False, f"Error: {error_msg}")
        return False


def test_discord_webhook():
    """Test Discord webhook (without sending a message)."""
    print_header("DISCORD WEBHOOK")

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print_result("Discord webhook", False, "DISCORD_WEBHOOK_URL not set (optional)")
        print("    Discord notifications will be disabled.")
        return True  # Optional feature

    try:
        import requests

        # Validate URL format
        if "discord.com/api/webhooks/" in webhook_url or "discordapp.com/api/webhooks/" in webhook_url:
            print_result("Webhook URL format", True, "Valid Discord webhook URL format")
        else:
            print_result("Webhook URL format", False, "Invalid webhook URL format")
            return False

        # Test webhook with GET request (doesn't send message)
        print("Validating webhook...")
        response = requests.get(webhook_url)

        if response.status_code == 200:
            webhook_info = response.json()
            print_result("Webhook validation", True,
                        f"Webhook name: {webhook_info.get('name', 'Unknown')}")
            print(f"    Channel ID: {webhook_info.get('channel_id', 'Unknown')}")
            print(f"    Guild ID: {webhook_info.get('guild_id', 'Unknown')}")
        else:
            print_result("Webhook validation", False, f"HTTP {response.status_code}")
            return False

        return True

    except ImportError:
        print_result("Requests library", False, "requests package not installed")
        return False
    except Exception as e:
        print_result("Discord webhook", False, f"Error: {str(e)}")
        return False


def test_directory_structure():
    """Test that required directories exist or can be created."""
    print_header("DIRECTORY STRUCTURE")

    required_dirs = [
        "config",
        "data",
        "data/reports",
        "logs",
        "src",
    ]

    all_ok = True

    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print_result(f"{dir_path}/", True, "Exists")
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                print_result(f"{dir_path}/", True, "Created")
            except Exception as e:
                print_result(f"{dir_path}/", False, f"Cannot create: {e}")
                all_ok = False

    return all_ok


def test_python_dependencies():
    """Test that required Python packages are installed."""
    print_header("PYTHON DEPENDENCIES")

    dependencies = [
        ("dotenv", "python-dotenv"),
        ("yaml", "PyYAML"),
        ("praw", "praw"),
        ("googleapiclient", "google-api-python-client"),
        ("youtube_transcript_api", "youtube-transcript-api"),
        ("ollama", "ollama"),
        ("requests", "requests"),
        ("schedule", "schedule"),
        ("aiosqlite", "aiosqlite"),
        ("dateutil", "python-dateutil"),
        ("pytz", "pytz"),
    ]

    all_installed = True

    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print_result(package_name, True, "Installed")
        except ImportError:
            print_result(package_name, False, f"Not installed (pip install {package_name})")
            all_installed = False

    return all_installed


def main():
    """Run all configuration tests."""
    print("\n" + "="*60)
    print("  SCRIBE - Configuration & Connection Test Suite")
    print("="*60)

    results = {}

    # Run all tests
    results["dependencies"] = test_python_dependencies()
    results["directories"] = test_directory_structure()
    results["config_files"] = test_configuration_files()
    results["env_vars"] = test_environment_variables()
    results["ollama"] = test_ollama_connection()
    results["reddit"] = test_reddit_api()
    results["youtube"] = test_youtube_api()
    results["discord"] = test_discord_webhook()

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        symbol = "[+]" if success else "[-]"
        print(f"{symbol} {test_name.replace('_', ' ').title()}: {status}")

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} tests passed")
    print(f"{'='*60}")

    if passed == total:
        print("\nAll tests passed! SCRIBE is ready to run.")
        print("Execute: python main.py --mode once")
        return 0
    else:
        print("\nSome tests failed. Please fix the issues above before running SCRIBE.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
