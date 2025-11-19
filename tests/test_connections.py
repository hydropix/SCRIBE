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

# Load environment variables (override=True to prioritize .env over system vars)
load_dotenv(override=True)


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

    all_valid = True
    configs = {}

    # Test global config
    global_config_path = Path("config/global.yaml")
    if global_config_path.exists():
        try:
            with open(global_config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                configs["config/global.yaml"] = config_data
            print_result("config/global.yaml", True, f"Valid YAML with {len(config_data)} top-level keys")

            if "ollama" in config_data:
                model = config_data["ollama"].get("model", "unknown")
                print(f"    - Ollama model: {model}")
        except yaml.YAMLError as e:
            print_result("config/global.yaml", False, f"Invalid YAML: {e}")
            all_valid = False
    else:
        print_result("config/global.yaml", False, "File not found")
        all_valid = False

    # Discover and test all packages
    packages_dir = Path("packages")
    if not packages_dir.exists():
        print_result("packages/", False, "Packages directory not found")
        return False

    packages = [d for d in packages_dir.iterdir() if d.is_dir()]

    if not packages:
        print_result("packages/", False, "No packages found")
        return False

    print(f"\nFound {len(packages)} package(s):")

    for package_dir in packages:
        package_name = package_dir.name
        print(f"\n  Package: {package_name}")

        # Check settings.yaml
        settings_path = package_dir / "settings.yaml"
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = yaml.safe_load(f)
                    configs[str(settings_path)] = settings
                print_result(f"    settings.yaml", True, f"Valid YAML")

                # Show package details
                if "reddit" in settings:
                    subreddits = settings["reddit"].get("subreddits", [])
                    print(f"        - Reddit subreddits: {len(subreddits)}")

                if "youtube" in settings:
                    keywords = settings["youtube"].get("keywords", [])
                    channels = settings["youtube"].get("channels", [])
                    print(f"        - YouTube keywords: {len(keywords)}")
                    print(f"        - YouTube channels: {len(channels)}")

                if "analysis" in settings:
                    categories = settings["analysis"].get("categories", [])
                    print(f"        - Analysis categories: {len(categories)}")

                if "report" in settings:
                    language = settings["report"].get("language", "en")
                    print(f"        - Report language: {language}")

            except yaml.YAMLError as e:
                print_result(f"    settings.yaml", False, f"Invalid YAML: {e}")
                all_valid = False
        else:
            print_result(f"    settings.yaml", False, "Not found")
            all_valid = False

        # Check prompts.yaml
        prompts_path = package_dir / "prompts.yaml"
        if prompts_path.exists():
            try:
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                print_result(f"    prompts.yaml", True, "Valid YAML")
            except yaml.YAMLError as e:
                print_result(f"    prompts.yaml", False, f"Invalid YAML: {e}")
                all_valid = False
        else:
            print_result(f"    prompts.yaml", False, "Not found")
            all_valid = False

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
        with open("config/global.yaml", 'r', encoding='utf-8') as f:
            global_config = yaml.safe_load(f)

        configured_model = global_config.get("ollama", {}).get("model", "qwen3:14b")

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
    """Test Discord webhooks for all packages."""
    print_header("DISCORD WEBHOOKS")

    try:
        import requests

        # Discover webhooks from packages
        packages_dir = Path("packages")
        webhooks_found = []

        if packages_dir.exists():
            for package_dir in packages_dir.iterdir():
                if package_dir.is_dir():
                    settings_path = package_dir / "settings.yaml"
                    if settings_path.exists():
                        with open(settings_path, 'r', encoding='utf-8') as f:
                            settings = yaml.safe_load(f)

                        package_name = package_dir.name

                        # Check main webhook
                        if "discord" in settings:
                            webhook_env = settings["discord"].get("webhook_env")
                            if webhook_env:
                                webhooks_found.append((package_name, "main", webhook_env))

                            # Check summary webhook
                            summary = settings["discord"].get("summary", {})
                            if summary.get("enabled"):
                                summary_webhook_env = summary.get("webhook_env")
                                if summary_webhook_env:
                                    webhooks_found.append((package_name, "summary", summary_webhook_env))

        if not webhooks_found:
            print_result("Discord webhooks", False, "No webhook configurations found in packages")
            print("    Discord notifications will be disabled.")
            return True  # Optional feature

        all_valid = True
        for package_name, webhook_type, env_var in webhooks_found:
            webhook_url = os.getenv(env_var)

            if not webhook_url:
                print_result(f"{package_name} ({webhook_type})", False, f"{env_var} not set")
                continue

            # Validate URL format
            if "discord.com/api/webhooks/" not in webhook_url and "discordapp.com/api/webhooks/" not in webhook_url:
                print_result(f"{package_name} ({webhook_type})", False, "Invalid webhook URL format")
                all_valid = False
                continue

            # Test webhook with GET request (doesn't send message)
            response = requests.get(webhook_url)

            if response.status_code == 200:
                webhook_info = response.json()
                print_result(f"{package_name} ({webhook_type})", True,
                            f"Webhook: {webhook_info.get('name', 'Unknown')}")
            else:
                print_result(f"{package_name} ({webhook_type})", False, f"HTTP {response.status_code}")
                all_valid = False

        return all_valid

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
