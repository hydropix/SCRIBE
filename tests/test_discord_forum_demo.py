"""
Demonstration script for Discord forum channel webhook support

This script demonstrates how to use SCRIBE's Discord notifier with forum channels.
"""

import sys
import os
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notifiers.discord_notifier import DiscordNotifier

# Your test forum webhook
FORUM_WEBHOOK_URL = "https://discord.com/api/webhooks/1441708680851755171/gPlbj5fCsX-B4sn85wX1nz08So2kWoc3BD5euPCLNWXmrdM0f_7Js66SCKl53gsng_1H"


def demo_forum_report():
    """Demonstrate a full SCRIBE report to a forum channel"""
    print("\n" + "="*70)
    print("DEMO: Full SCRIBE Report to Forum Channel")
    print("="*70 + "\n")

    # Configure Discord notifier with forum support
    current_date = datetime.now().strftime('%d %B %Y')

    config = {
        "webhook_env": "DEMO_FORUM_WEBHOOK",
        "rich_embeds": True,
        "thread_name": f"🤖 AI Trends Report - {current_date}"
    }

    # Set the webhook URL
    os.environ["DEMO_FORUM_WEBHOOK"] = FORUM_WEBHOOK_URL

    # Create notifier
    notifier = DiscordNotifier(config)

    # Sample analyzed content (like SCRIBE would produce)
    relevant_contents = [
        {
            "title": "Claude 4 Released with Groundbreaking Capabilities",
            "translated_title": "Claude 4 sort avec des capacités révolutionnaires",
            "hook": "Anthropic dévoile Claude 4, repoussant les limites de l'IA conversationnelle",
            "insights": """**Innovations majeures:**
- Architecture multi-modale avancée
- Amélioration de 40% en raisonnement logique
- Fenêtre de contexte étendue à 500K tokens

**Impact:**
Cette release marque un tournant dans l'évolution des LLMs, avec des applications directes en recherche et développement.""",
            "category": "Large Language Models",
            "relevance_score": 10,
            "metadata": {
                "source": "reddit",
                "author": "anthropic_official",
                "subreddit": "artificial",
                "url": "https://reddit.com/r/artificial/claude4",
                "permalink": "https://reddit.com/r/artificial/claude4",
                "image_url": "https://picsum.photos/800/400?random=1"
            }
        },
        {
            "title": "Open Source Computer Vision Model Surpasses GPT-4V",
            "translated_title": "Modèle de vision open source surpasse GPT-4V",
            "hook": "Une équipe de recherche publie un modèle de vision par ordinateur open source",
            "insights": """**Caractéristiques:**
- Précision de 94.2% sur les benchmarks standard
- Modèle entièrement open source (MIT license)
- Optimisé pour les GPU consumer

**Applications:**
- Analyse médicale d'images
- Détection d'objets en temps réel
- Accessibilité pour les développeurs""",
            "category": "Computer Vision",
            "relevance_score": 9,
            "metadata": {
                "source": "youtube",
                "channel_title": "AI Research Today",
                "video_id": "dQw4w9WgXcQ",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ"
            }
        },
        {
            "title": "Breakthrough in Reinforcement Learning for Robotics",
            "translated_title": "Percée en apprentissage par renforcement pour la robotique",
            "hook": "Des robots apprennent des tâches complexes 10x plus rapidement",
            "insights": """**Innovation technique:**
- Nouvel algorithme de RL basé sur l'apprentissage par imitation
- Réduction du temps d'entraînement de 90%
- Transfert d'apprentissage entre différents robots

**Implications industrielles:**
Cette avancée pourrait accélérer l'adoption de robots autonomes dans la logistique et la manufacture.""",
            "category": "Robotics & Embodied AI",
            "relevance_score": 8,
            "metadata": {
                "source": "reddit",
                "author": "robotics_lab",
                "subreddit": "MachineLearning",
                "url": "https://reddit.com/r/MachineLearning/rl_breakthrough",
                "permalink": "https://reddit.com/r/MachineLearning/rl_breakthrough"
            }
        }
    ]

    print(f"Sending report with {len(relevant_contents)} insights to forum channel...")
    print(f"   Thread name: {config['thread_name']}")
    print()

    # Send the rich report
    success = notifier.send_rich_report(relevant_contents, mention_role="")

    if success:
        print("SUCCESS: Report sent successfully!")
        print(f"\nSummary:")
        print(f"   - Total insights: {len(relevant_contents)}")
        print(f"   - Categories covered: {len(set(c['category'] for c in relevant_contents))}")
        print(f"   - Average relevance: {sum(c['relevance_score'] for c in relevant_contents) / len(relevant_contents):.1f}/10")
    else:
        print("FAILED: Failed to send report")

    return success


def demo_summary_notification():
    """Demonstrate a daily summary notification to a forum channel"""
    print("\n" + "="*70)
    print("DEMO: Daily Summary to Forum Channel")
    print("="*70 + "\n")

    current_date = datetime.now().strftime('%d %B %Y')

    config = {
        "webhook_env": "DEMO_FORUM_WEBHOOK",
        "summary": {
            "webhook_env": "DEMO_FORUM_WEBHOOK"
        },
        "thread_name": f"📊 AI Summary - {current_date}"
    }

    os.environ["DEMO_FORUM_WEBHOOK"] = FORUM_WEBHOOK_URL

    notifier = DiscordNotifier(config)

    # Sample AI-generated summary
    summary = """# 🤖 Résumé Quotidien - AI Trends

**Date:** {date}

## 📈 Vue d'ensemble

Aujourd'hui marque une journée exceptionnelle dans le monde de l'IA avec 3 annonces majeures :

1. **Claude 4 Release** - Anthropic repousse les limites des LLMs avec une architecture révolutionnaire
2. **Vision Model Open Source** - Un nouveau modèle surpasse GPT-4V tout en étant accessible à tous
3. **Robotics Breakthrough** - L'apprentissage par renforcement fait un bond de 10x en efficacité

## 🎯 Impact

Ces développements convergent vers une démocratisation accrue de l'IA avancée, avec des implications directes pour :
- Les développeurs (accès à des outils plus puissants)
- L'industrie (automation accélérée)
- La recherche (nouvelles frontières explorables)

## 💡 À surveiller

- Réaction de la communauté aux nouvelles capacités de Claude 4
- Adoption du modèle de vision open source
- Déploiements industriels des nouvelles techniques de RL

---
*Rapport généré par SCRIBE - Source Content Retrieval and Intelligence Bot Engine*
""".format(date=current_date)

    print(f"Sending daily summary to forum channel...")
    print(f"   Thread name: {config['thread_name']}")
    print()

    success = notifier.send_summary(summary, mention_role="")

    if success:
        print("SUCCESS: Summary sent successfully!")
        print(f"\nSummary length: {len(summary)} characters")
    else:
        print("FAILED: Failed to send summary")

    return success


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SCRIBE - Discord Forum Channel Demo")
    print("="*70)
    print("\nThis demo shows how SCRIBE's Discord notifier works with forum channels.")
    print(f"Target webhook: {FORUM_WEBHOOK_URL[:50]}...")

    results = []

    # Demo 1: Full report
    results.append(("Full Report", demo_forum_report()))

    print("\n" + "-"*70)
    print("Waiting 3 seconds before next demo...")
    print("-"*70)
    import time
    time.sleep(3)

    # Demo 2: Summary
    results.append(("Daily Summary", demo_summary_notification()))

    # Final summary
    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    for name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{status} - {name}")

    print("\nCheck your Discord forum channel to see the results!")
