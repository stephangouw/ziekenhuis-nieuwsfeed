import os
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent dir to path to import database
sys.path.append(str(Path(__file__).parent.parent))
from execution.database import get_unsummarized_articles, update_article_ai_data

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("Please install google-genai: pip install google-genai")
    sys.exit(1)

def process_articles():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("No GEMINI_API_KEY found in .env file. Please add one.")
        return

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return

    articles = get_unsummarized_articles(limit=20)
    if not articles:
        logger.info("No new articles to summarize.")
        return

    logger.info(f"Found {len(articles)} articles to process using AI.")

    for article in articles:
        content_to_summarize = article['original_content'] if article.get('original_content') else article['title']
        
        prompt = f"""
        Je bent een medisch nieuwscorrespondent. Hieronder vind je een nieuwsartikel (of alleen de titel/korte omschrijving) afkomstig van het ziekenhuis '{article['hospital_name']}'.
        
        Artikel inhoud:
        {content_to_summarize}
        
        Jouw taak:
        1. Schrijf een heldere, korte samenvatting (maximaal 3 zinnen) in begrijpelijke, B1 taalniveau. Geen academisch of moeilijk medisch jargon.
        2. Bedenk maximaal Drie (3) brede tags die dit artikel categoriseren (bijv. "Oncologie", "Innovatie", "Patiëntenzorg", "Onderzoek").
        
        Geef je antwoord EXACT in dit JSON formaat (zonder markdown of andere tekst eromheen):
        {{
            "summary": "Jouw samenvatting hier...",
            "tags": ["Tag1", "Tag2", "Tag3"]
        }}
        """

        try:
            logger.info(f"Generating summary for: {article['title']}")
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            
            # The response text should be JSON
            result_text = response.text.strip()
            
            # Parse JSON
            result_json = json.loads(result_text)
            
            summary = result_json.get("summary", "Geen samenvatting beschikbaar.")
            tags = result_json.get("tags", [])
            
            # Update DB
            update_article_ai_data(article['id'], summary, tags)
            logger.info(f"Successfully updated article {article['id']}")
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response for article {article['id']}: {result_text}")
        except Exception as e:
            logger.error(f"Error calling Gemini API for article {article['id']}: {e}")

if __name__ == "__main__":
    process_articles()
