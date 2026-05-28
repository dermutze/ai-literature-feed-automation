import streamlit as st
import urllib.request
import xml.etree.ElementTree as ET
import urllib.parse

st.title("🔬 Ti64 & AM Literatur-Sucher")
st.write("Dieses Tool sucht direkt auf arXiv nach Fachartikeln und bereitet den Text für deine Firmen-KI vor.")

# Suchbegriffe definieren
keywords = [
    '("additive manufacturing" AND "Ti6Al4V")',
    '("selective laser melting" AND "Ti-6Al-4V")',
    '("laser powder bed fusion" AND "Ti64")',
    '("electron beam melting" AND "Ti64")'
]

if st.button("Starte Live-Suche auf arXiv"):
    st.info("Suche läuft... Artikel werden direkt von der arXiv-Datenbank abgerufen.")
    
    # Suchanfrage für arXiv zusammenbauen
    query = " OR ".join([f'all:{k}' for k in keywords])
    encoded_query = urllib.parse.quote(query)
    url = f'http://arxiv.org{encoded_query}&max_results=5&sortBy=submittedDate&sortOrder=descending'
    
    try:
        # Daten abrufen
        response = urllib.request.urlopen(url)
        xml_data = response.read()
        
        # XML parsen
        root = ET.fromstring(xml_data)
        namespaces = {'atom': 'http://w3.org'}
        entries = root.findall('atom:entry', namespaces)
        
        if not entries:
            st.warning("Keine neuen Artikel zu diesen Begriffen gefunden.")
        else:
            st.success(f"Erfolgreich {len(entries)} aktuelle Fachartikel gefunden!")
            st.write("---")
            
            for i, entry in enumerate(entries):
                title = entry.find('atom:title', namespaces).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', namespaces).text.strip().replace('\n', ' ')
                published = entry.find('atom:published', namespaces).text[:10]
                
                # Autoren sammeln
                authors = [author.find('atom:name', namespaces).text for author in entry.findall('atom:author', namespaces)]
                authors_str = ", ".join(authors)
                
                st.subheader(f"📄 {i+1}. {title}")
                st.caption(f"📅 Veröffentlicht: {published} | ✍️ Autoren: {authors_str}")
                
                # Textbox für die Firmen-KI vorbereiten
                ki_text = f"Titel: {title}\nAutoren: {authors_str}\nVeröffentlichungsdatum: {published}\n\nAbstract:\n{summary}"
                
                st.text_area(
                    label="Kopieren für deine Firmen-KI (Strg+A -> Strg+C):", 
                    value=ki_text, 
                    height=200, 
                    key=f"txt_{i}"
                )
                st.write("---")
                
    except Exception as e:
        st.error(f"Fehler beim Abruf der Daten: {e}")
