import streamlit as st
import subprocess
import os
import sys

st.title("📚 Mein Literatur-Such-Assistent")
st.write("Dieses Tool sucht wissenschaftliche Arbeiten auf arXiv und bereitet die Texte für deine Firmen-KI vor.")

if st.button("Starte Literatursuche & Text-Extraktion"):
    st.info("Die Suche läuft... Arbeiten werden von arXiv abgerufen (ca. 1 Minute).")
    
    # JETZT KORREKT: 'import os' direkt im Befehl hinzugefügt
    cmd = "import sys, os; sys.path.append(os.getcwd()); from src.main import main; main()"
    result = subprocess.run(["python", "-c", cmd], capture_output=True, text=True)
    
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
                    st.text_area(label="Text für deine Firmen-KI kopieren:", value=content, height=200)
    else:
        st.error("Es wurden keine Daten gefunden.")
        if result.stderr:
            st.code(result.stderr)
