import streamlit as st
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# 1. Titel der App
st.set_page_config(page_title="Ti64 & AM Literatur-Sucher", page_icon="🔬")
st.title("🔬 Ti64 & AM Literatur-Sucher")
st.write("Dieses Tool sucht live auf arXiv nach Fachartikeln und bereitet den Text für deine Firmen-KI vor.")

st.write("---")

# 2. Einstellungen für die Suche
st.subheader("🔍 Deine Suchbegriffe")

# Vereinfachte, robuste Suchanfrage ohne komplizierte all:-Präfixe
default_search = 'Ti6Al4V AND "additive manufacturing"'
user_query = st.text_input("Suchanfrage an die arXiv-Datenbank:", value=default_search)

# Neues Auswahlmenü für die Sortierung (behebt das Zeitraum-Problem!)
sort_by_choice = st.selectbox(
    "Wie sollen die Artikel sortiert werden?",
    options=["Beste Treffer (Relevanz)", "Neueste zuerst (Datum)"]
)

# Übersetzung für die arXiv-API
sort_by_api = "relevance" if "Relevanz" in sort_by_choice else "submittedDate"

# Schieberegler für die Anzahl der Ergebnisse
max_results = st.slider("Wie viele Artikel möchtest du finden?", min_value=1, max_value=10, value=5)

st.write("---")

# 3. Der Start-Button und die Suchlogik
if st.button("🚀 Starte Live-Suche auf arXiv"):
    st.info("Suche läuft... Artikel werden direkt von der arXiv-Datenbank abgerufen.")
    
    # Parameter für die API zusammenbauen
    params = {
        "search_query": user_query,
        "max_results": max_results,
        "sortBy": sort_by_api,
        "sortOrder": "descending"
    }
    
    url = f"http://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
    
    try:
        # Daten von arXiv abrufen
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        xml_data = response.read()
        
        # XML-Daten auswerten
        root = ET.fromstring(xml_data)
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', namespaces)
        
        if not entries:
            st.warning("Keine Artikel gefunden. Tipp: Versuche die Suche noch einfacher zu gestalten, z. B. nur 'Ti6Al4V'.")
        else:
            st.success(f"Erfolgreich {len(entries)} Fachartikel gefunden!")
            st.write("---")
            
            # Jeden gefundenen Artikel anzeigen
            for i, entry in enumerate(entries):
                title = entry.find('atom:title', namespaces).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', namespaces).text.strip().replace('\n', ' ')
                published = entry.find('atom:published', namespaces).text[:10]
                
                # Autoren sammeln
                authors = [author.find('atom:name', namespaces).text for author in entry.findall('atom:author', namespaces)]
                authors_str = ", ".join(authors)
                
                # Artikel auf der Webseite darstellen
                st.subheader(f"📄 {i+1}. {title}")
                st.caption(f"📅 Veröffentlicht: {published} | ✍️ Autoren: {authors_str}")
                
                # Textbox für deine Firmen-KI vorbereiten
                ki_text = f"Titel: {title}\nAutoren: {authors_str}\nDatum: {published}\n\nAbstract:\n{summary}"
                
                st.text_area(
                    label="Kopieren für deine Firmen-KI (Klicke hinein -> Strg+A -> Strg+C):", 
                    value=ki_text, 
                    height=220, 
                    key=f"txt_{i}"
                )
                st.write("---")
                
    except Exception as e:
        st.error(f"Fehler beim Abruf der Daten: {e}")
