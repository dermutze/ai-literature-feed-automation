import streamlit as st
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

st.title("🔬 Ti64 & AM Literatur-Sucher")
st.write("Dieses Tool sucht direkt auf arXiv nach Fachartikeln und bereitet den Text für deine Firmen-KI vor.")

# Suchbegriffe sauber als eine zusammenhängende Abfrage definieren
search_query = (
    'all:"additive manufacturing" AND all:Ti6Al4V OR '
    'all:"selective laser melting" AND all:"Ti-6Al-4V" OR '
    'all:"laser powder bed fusion" AND all:Ti64 OR '
    'all:"electron beam melting" AND all:Ti64'
)

if st.button("Starte Live-Suche auf arXiv"):
    st.info("Suche läuft... Artikel werden direkt von der arXiv-Datenbank abgerufen.")
    
    # Parameter sauber über eine sichere Tabellen-Funktion codieren (verhindert den Port-Fehler)
    params = {
        "search_query": search_query,
        "max_results": 5,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    url = f"http://arxiv.org?{urllib.parse.urlencode(params)}"
    
    try:
        # Daten abrufen
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        xml_data = response.read()
        
        # XML parsen
        root = ET.fromstring(xml_data)
        namespaces = {'atom': 'http://w3.org'}
        entries = root.findall('atom:entry', namespaces)
        
        if not entries:
            st.warning("Keine neuen Artikel zu diesen Begriffen gefunden. Probiere es gleich noch einmal.")
        else:
            st.success(f"Erfolgreich {len(entries)} aktuelle Fachartikel gefunden!")
            st.write("---")
            
            for i, entry in enumerate(entries):
                title = entry.find('atom:title', namespaces).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', namespaces).text.strip().replace('\n', ' ')
                published = entry.find('atom:published', namespaces).text[:10]
                
                authors = [author.find('atom:name', namespaces).text for author in entry.findall('atom:author', namespaces)]
                authors_str = ", ".join(authors)
                
                st.subheader(f"📄 {i+1}. {title}")
                st.caption(f"📅 Veröffentlicht: {published} | ✍️ Autoren: {authors_str}")
                
                # Textbox für deine Firmen-KI
                ki_text = f"Titel: {title}\nAutoren: {authors_str}\nDatum: {published}\n\nAbstract:\n{summary}"
                
                st.text_area(
                    label="Kopieren für deine Firmen-KI (Strg+A -> Strg+C):", 
                    value=ki_text, 
                    height=200, 
                    key=f"txt_{i}"
                )
                st.write("---")
                
    except Exception as e:
        st.error(f"Fehler beim Abruf der Daten: {e}")
