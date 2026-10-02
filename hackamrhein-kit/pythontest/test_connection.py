import os
from dotenv import load_dotenv
from supabase import create_client

# 1. Lädt die Umgebungsvariablen aus deiner .env Datei in dieses Skript
load_dotenv()

# 2. Liest die spezifischen Keys aus, die wir für das Backend brauchen
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")

# 3. Baut die aktive Verbindung zu deinem Supabase-Projekt auf
supabase = create_client(url, key)

# 4. Sendet einen Test-Befehl: "Wähle (*) aus 'sensor_readings', aber maximal 1 Zeile"
response = supabase.table('sensor_readings').select("*").limit(1).execute()

# 5. Gibt die Antwort der Datenbank im Terminal aus
print("Datenbank antwortet:", response.data)