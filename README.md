# Verslagmaker

Een lokale verslaggenerator voor ICT MBO-examens. Het concept blijft als JSON
op je eigen computer en kan worden geexporteerd naar PDF, DOCX en ODT.

## Starten

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open daarna `http://127.0.0.1:5000`.

## Belangrijkste functies

- wizard op basis van de richtlijnen voor examenverslagen;
- acht werkprocessen voor Web development C2024 (Crebo 25604ONA1);
- import van eigen JSON en concept-JSON van `matrijzen.ictmbo.nl`;
- lokale autosave in de browser;
- kwaliteitscontrole voor ontbrekende onderdelen, bewijs en toekomsttaal;
- export naar PDF, DOCX en ODT;
- geen database en geen upload naar een externe dienst.

## JSON

Gebruik **Concept opslaan** om een draagbaar JSON-bestand te downloaden. De
generator accepteert zowel zijn eigen schema (`school-verslag/1.0`) als de
velden van een concept uit de examenmatrijsgenerator.

## Tests

```powershell
python -m unittest discover -s tests -v
```

