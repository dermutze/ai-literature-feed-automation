import streamlit as st
import subprocess
import os
import json

st.title("📚 Mein Literatur-Such-Assistent")
st.write("Dieses Tool sucht wissenschaftliche Arbeiten auf arXiv und bereitet die Texte für deine Firmen-KI vor.")

# Suchthemen anzeigen
config_path = "config/interests.yaml"
st.info("Das Tool sucht aktuell nach den im Projekt hinterlegten Standardthemen (z. B. Batterieforschung).")

if st.button("Starte Literatursuche & Text-Extraktion"):
    st.info("Suche läuft... Daten werden von arXiv abgerufen (ca. 1 Minute).")
    
    # Startet das originale Skript im Hintergrund (Suchen und Filtern)
    # Wir fangen den Prozess ab, bevor er versucht, eine externe KI aufzurufen
    result = subprocess.run(["python", "-c", "from src.main import main; main()"], capture_output=True, text=True)
    
    # Pfad zu den gefundenen Rohdaten/Artikeln im Projekt
    data_dir = "data/raw_articles" 
    
    # Falls das Skript wegen der fehlenden KI abbricht, schauen wir, ob trotzdem Daten da sind:
    if os.path.exists(data_dir) and os.listdir(data_dir):
        st.success("Erfolgreich Forschungsarbeiten gefunden!")
        st.write("Kopiere die unten stehenden Texte und füge sie in deine Firmen-KI ein:")
        
        for file in os.listdir(data_dir):
            if file.endswith(".json") or file.endswith(".txt"):
                st.subheader(f"📄 Artikel-Quelle: {file}")
                with open(os.path.join(data_dir, file), "r", encoding="utf-8") as f:
                    content = f.read()
                    # Text kompakt in einer Box zum leichten Kopieren anzeigen
                    st.text_area(label="Text für deine Firmen-KI kopieren:", value=content, height=200)
    else:
        st.error("Es wurden keine Daten gefunden. Vermutlich blockiert die Firmen-Firewall den Abruf von arXiv.")
        if result.stderr:
            st.code(result.stderr)
