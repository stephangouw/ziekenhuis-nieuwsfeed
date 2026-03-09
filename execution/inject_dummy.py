import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from execution.database import insert_article, update_article_ai_data
from datetime import datetime

print("Injecting fake data...")
now = datetime.now().strftime("%Y-%m-%d")
insert_article("Máxima MC", "Brainport", "Baanbrekend onderzoek schildklierkanker", "https://mmc.nl/dummy1", now, "Content")
insert_article("Albert Schweitzer", "mProve", "Nieuwe behandeling hartfalen in regio", "https://asz.nl/dummy2", now, "Content")
insert_article("Erasmus MC", "NFU", "Grote sprong in AI voor radiologie", "https://erasmus.nl/dummy3", now, "Content")

# Get IDs (assuming they are 1, 2, 3)
update_article_ai_data(1, "Een nieuwe, minder invasieve behandeling voor schildklierkanker toont veelbelovende resultaten in een recente studie.", ["Oncologie", "Onderzoek", "Innovatie"])
update_article_ai_data(2, "Patiënten met hartfalen kunnen nu rekenen op een nieuwe, gepersonaliseerde aanpak dankzij een samenwerking binnen de regio.", ["Cardiologie", "Netwerkzorg"])
update_article_ai_data(3, "Kunstmatige intelligentie wordt succesvol ingezet om radiologen sneller en accurater diagnoses te laten stellen.", ["AI", "Radiologie", "Innovatie"])
print("Fake data injected.")
