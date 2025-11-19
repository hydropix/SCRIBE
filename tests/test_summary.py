"""
Test script for Discord summary feature

This script tests the daily summary generation and Discord webhook sending
without running a full SCRIBE collection cycle.
"""

import os
import logging
from dotenv import load_dotenv
from src.processors.ollama_client import OllamaClient
from src.notifiers.discord_notifier import DiscordNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Sample test data (simulating relevant contents)
test_contents = [
    {
        'translated_title': 'GPT-5 annoncé avec des capacités de raisonnement améliorées',
        'category': 'Large Language Models',
        'hook': 'OpenAI dévoile des améliorations majeures en raisonnement logique',
        'insights': '• Amélioration de 40% sur les benchmarks de raisonnement\n• Nouvelle architecture avec mémoire de travail étendue',
        'relevance_score': 9
    },
    {
        'translated_title': 'Claude 4 surpasse les modèles concurrents en programmation',
        'category': 'AI Tools & Applications',
        'hook': 'Anthropic lance Claude 4 avec des capacités de codage exceptionnelles',
        'insights': '• Taux de réussite de 85% sur HumanEval\n• Support de 20+ langages de programmation',
        'relevance_score': 8
    },
    {
        'translated_title': 'Nouvelle régulation IA en Europe : impact sur les startups',
        'category': 'AI Regulation & Policy',
        'hook': "L'UE impose des règles strictes sur les modèles d'IA",
        'insights': '• Obligation de transparence pour les grands modèles\n• Fonds de 10M€ pour aider les startups à se conformer',
        'relevance_score': 7
    },
    {
        'translated_title': 'Llama 4 open source avec 200B paramètres',
        'category': 'Open Source Models',
        'hook': 'Meta libère son plus grand modèle open source',
        'insights': '• Performances comparables à GPT-4\n• Gratuit pour usage commercial\n• Formation sur 15T tokens',
        'relevance_score': 9
    },
    {
        'translated_title': 'Robots humanoïdes dans les entrepôts Amazon',
        'category': 'Robotics & Embodied AI',
        'hook': 'Amazon déploie 1000 robots humanoïdes pour la logistique',
        'insights': '• Réduction de 30% du temps de traitement\n• IA de vision pour navigation autonome',
        'relevance_score': 8
    }
]

def test_summary_generation():
    """Test the summary generation with Ollama"""
    print("\n" + "="*60)
    print("TEST 1: Summary Generation with Ollama")
    print("="*60)

    try:
        # Initialize Ollama client with French language
        client = OllamaClient(language="French")

        # Generate summary
        print("\nGenerating summary with Ollama...")
        summary = client.generate_daily_summary(
            relevant_contents=test_contents,
            max_length=1900
        )

        print("\n" + "-"*60)
        print("Generated Summary:")
        print("-"*60)
        print(summary)
        print("-"*60)
        print(f"\nSummary length: {len(summary)} characters")

        if len(summary) > 2000:
            print("⚠️  WARNING: Summary exceeds Discord's 2000 character limit!")
        else:
            print("✓ Summary length is within Discord's limit")

        return summary

    except Exception as e:
        print(f"\n❌ Error generating summary: {e}")
        return None

def test_discord_webhook(summary_text):
    """Test sending summary to Discord webhook"""
    print("\n" + "="*60)
    print("TEST 2: Discord Webhook Sending")
    print("="*60)

    # Check if webhook URL is configured
    webhook_url = os.getenv('DISCORD_SUMMARY_WEBHOOK_URL')

    if not webhook_url:
        print("\n⚠️  DISCORD_SUMMARY_WEBHOOK_URL not configured in .env")
        print("Skipping webhook test. To test, add your webhook URL to .env:")
        print("DISCORD_SUMMARY_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        return False

    try:
        # Initialize Discord notifier
        notifier = DiscordNotifier()

        # Send summary
        print(f"\nSending summary to webhook...")
        print(f"Webhook: {webhook_url[:50]}...")

        success = notifier.send_summary(
            summary_text=summary_text,
            mention_role=""  # No mention for testing
        )

        if success:
            print("\n✓ Summary sent successfully to Discord!")
            return True
        else:
            print("\n❌ Failed to send summary to Discord")
            return False

    except Exception as e:
        print(f"\n❌ Error sending to Discord: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SCRIBE - Discord Summary Feature Test")
    print("="*60)

    # Test 1: Generate summary
    summary = test_summary_generation()

    if summary:
        # Test 2: Send to Discord (if configured)
        test_discord_webhook(summary)

    print("\n" + "="*60)
    print("Tests completed")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
