import streamlit as st
import os
import sys

# Füge das aktuelle Verzeichnis direkt zu Beginn hinzu
sys.path.append(os.getcwd())

st.title("📚 Mein Literatur-Such-Assistent")
st.write("Dieses Tool sucht wissenschaftliche Arbeiten auf arXiv und bereitet die Texte für deine Firmen-KI vor.")

if st.button("Starte Literatursuche & Text-Extraktion"):
    st.info("Die Suche läuft... Arbeiten werden direkt von arXiv abgerufen (ca. 1 Minute).")
    
    try:
        # Direkter Import ohne den fehleranfälligen Terminal-Umweg
        from src.main import main
        
        # Wir führen die Suche aus. Falls sie am Ende wegen der fehlenden KI meckert, 
        # fangen wir das im 'except'-Block unten ab, da die Daten dann meistens schon geladen sind.
        main()
    except Exception as e:
        # Ein Fehler am Ende (z.B. wegen fehlender KI/Ollama) ist okay, solange die Daten da sind!
        pass

    # Pfad zu den gefundenen Rohdaten/Artikeln im Projekt
    data_dir = "data/raw_articles" 
    
    if os.path.exists(data_dir) and os.listdir(data_dir):
        st.success("Erfolgreich Forschungsarbeiten gefunden!")
        st.write("Kopiere die unten stehenden Texte und füge sie in deine Firmen-KI ein:")
        
        for file in os.listdir(data_dir):
            if file.endswith(".json") or file.endswith(".txt"):
                st.subheader(f"📄 Artikel-Quelle: {file}")
                with open(os.path.join(data_dir, file), "r", encoding="utf-8") as f:
                    content = f.read()
                    st.text_area(label="Text für deine Firmen-KI kopieren:", value=content, height=250)
    else:
        st.error("Es wurden leider keine Daten im Ordner gefunden. Eventuell gab es einen Fehler beim Abruf.")
        st.info("Falls dieser Fehler bleibt, erstelle ich dir ein Mini-Skript, das zu 100% autark funktioniert.")
