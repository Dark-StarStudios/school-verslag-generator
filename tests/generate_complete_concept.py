"""Build a complete local concept used for the end-to-end browser test."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import empty_report  # noqa: E402


EVIDENCE_DIR = ROOT / "output" / "test-evidence"
OUTPUT = ROOT / "output" / "complete-test-concept.json"


def image(name: str) -> dict[str, str]:
    path = EVIDENCE_DIR / name
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "name": name,
        "type": "image/jpeg",
        "data": f"data:image/jpeg;base64,{encoded}",
    }


report = empty_report()
report["student"].update(
    {
        "name": "Nikita Vlasov",
        "student_number": "40191784",
        "class_name": "WEB3A",
        "company": "Dutch Kiwi Design",
        "practice_supervisor": "Sanne de Vries",
        "bpv_supervisor": "Dhr. Jansen",
    }
)
report["project"].update(
    {
        "title": "Responsive verhuurwebsite",
        "subtitle": "Technisch examenverslag web development",
        "version": "1.0",
        "report_date": "2026-09-24",
        "exam_name": "Web development – realisatie van een verhuurplatform",
        "exam_number": "EP1",
        "start_date": "2026-09-01",
        "end_date": "2026-09-24",
        "description": "Ontwerp, realisatie en toetsing van een responsive verhuurwebsite.",
        "introduction": (
            "Voor dit examenproject heb ik voor Dutch Kiwi Design een responsive verhuurwebsite ontworpen en gerealiseerd. "
            "De opdrachtgever wilde bezoekers snel voertuigen en materieel laten vergelijken en een huurperiode laten kiezen. "
            "Mijn doel was een toegankelijke, betrouwbare en onderhoudbare webapplicatie op te leveren. Ik heb de eisen geanalyseerd, "
            "een interactief ontwerp gemaakt, de interface gebouwd, gegevens uit een API verwerkt en het resultaat op meerdere schermformaten getest."
        ),
        "products": [
            "Responsive verhuurwebsite voor desktop, tablet en mobiel",
            "Interactief ontwerp en componentoverzicht",
            "Werkende voertuig- en beschikbaarheidskoppeling",
            "Testplan, testresultaten en verbetervoorstellen",
            "Technische documentatie en overdracht",
        ],
    }
)
report["activities"] = [
    "Wensen en acceptatiecriteria met de opdrachtgever vastleggen",
    "User flows, wireframes en visueel ontwerp uitwerken",
    "Herbruikbare frontendcomponenten en responsive pagina's realiseren",
    "Voertuiggegevens en beschikbaarheid via API-koppelingen tonen",
    "Functionele, responsive en toegankelijkheidstests uitvoeren",
    "Feedback verwerken, documenteren en de applicatie presenteren",
]
report["resources"] = {
    "materials": ["Figma", "Visual Studio Code", "Git en GitHub", "HTML, CSS en JavaScript", "Browser DevTools"],
    "people": ["Opdrachtgever van Dutch Kiwi Design", "Praktijkopleider", "BPV-begeleider", "Twee testgebruikers"],
    "means": ["Ontwikkellaptop", "Testtelefoon en tablet", "Lokale ontwikkelomgeving", "Toegang tot de test-API"],
    "knowledge": ["Responsive webdesign", "Toegankelijkheid volgens WCAG", "REST-API's", "Versiebeheer", "Testmethoden"],
}
report["scope"] = {
    "included": [
        "Homepage, overzichts- en detailpagina's voor voertuigen",
        "Keuze van ophaal- en inleverdatum met prijsindicatie",
        "Responsive gedrag en basis-toegankelijkheid",
        "Technische documentatie, tests en presentatie",
    ],
    "excluded": [
        "Echte online betalingen en financiële transacties",
        "Beheer van wagenparkonderhoud",
        "Productieaccount voor externe boekhoudsoftware",
        "Native mobiele applicaties",
    ],
    "provided": [
        "Huisstijl, voorbeeldcontent en voertuiggegevens",
        "Wekelijks feedbackmoment van dertig minuten",
        "Toegang tot test-API en hostingomgeving",
        "Testapparaten en goedkeuring van het ontwerp",
    ],
}
report["planning"] = [
    {"phase": "Analyse en plan", "period": "01-09-2026 t/m 03-09-2026", "tasks": ["Eisen verzamelen", "Scope bepalen", "Risico's en planning vastleggen"]},
    {"phase": "Ontwerp en voorbereiding", "period": "04-09-2026 t/m 08-09-2026", "tasks": ["User flow tekenen", "Wireframes maken", "Ontwerp met opdrachtgever controleren"]},
    {"phase": "Realisatie", "period": "09-09-2026 t/m 17-09-2026", "tasks": ["Componenten bouwen", "API integreren", "Responsive pagina's afwerken"]},
    {"phase": "Testen en feedback", "period": "18-09-2026 t/m 21-09-2026", "tasks": ["Testgevallen uitvoeren", "WCAG-controle doen", "Feedback en fouten verwerken"]},
    {"phase": "Oplevering en afronding", "period": "22-09-2026 t/m 24-09-2026", "tasks": ["Documentatie schrijven", "Demonstratie voorbereiden", "Eindcontrole en overdracht uitvoeren"]},
]

accountability = {
    "B1-K1-W1": (
        "Ik heb de eisen vertaald naar concrete taken en acceptatiecriteria en deze verdeeld over vijf projectfasen. "
        "Per taak heb ik prioriteit, afhankelijkheden en een controlemoment vastgelegd. Tijdens de uitvoering hield ik het bord dagelijks bij. "
        "Toen de API later beschikbaar kwam, heb ik eerst de componenten met testdata afgerond en daarna de koppeling ingepland. Daardoor bleef de einddatum haalbaar."
    ),
    "B1-K1-W2": (
        "Ik heb op basis van de doelgroep een user flow, wireframes en een responsive componentontwerp gemaakt. Mijn keuzes voor duidelijke filters, grote knoppen en consistente kaarten heb ik onderbouwd met de eisen en WCAG-richtlijnen. "
        "Ik heb het ontwerp met de opdrachtgever besproken en na feedback de datumkeuze dichter bij de prijsinformatie geplaatst."
    ),
    "B1-K1-W3": (
        "Ik heb de website opgebouwd uit herbruikbare componenten voor navigatie, voertuigkaarten, filters en formulieren. Ik gebruikte semantische HTML, overzichtelijke CSS en kleine JavaScriptmodules. "
        "De API-responses worden gecontroleerd voordat gegevens worden getoond en foutmeldingen blijven begrijpelijk voor de gebruiker. Via Git-commits heb ik elke functionele stap controleerbaar vastgelegd."
    ),
    "B1-K1-W4": (
        "Ik heb een testplan uitgevoerd voor navigatie, filters, datumselectie, prijsberekening en formulierafhandeling. Daarnaast testte ik op mobiel, tablet en desktop en controleerde ik toetsenbordbediening en contrast. "
        "Een fout waarbij de einddatum vóór de startdatum kon liggen heb ik gereproduceerd, opgelost en opnieuw getest. Alle zes geautomatiseerde kerncontroles zijn daarna geslaagd."
    ),
    "B1-K1-W5": (
        "Ik heb testresultaten en gebruikersfeedback geordend op ernst, gebruiksimpact en benodigde tijd. Daaruit heb ik voorgesteld om gekozen filters zichtbaar te maken, laadstatussen toe te voegen en foutmeldingen direct naast het relevante veld te tonen. "
        "De verbeteringen met hoge impact heb ik binnen de examenperiode uitgevoerd; SEO-uitbreidingen zijn onderbouwd in de backlog geplaatst."
    ),
    "B1-K2-W1": (
        "Ik heb wekelijks voortgangsoverleg gevoerd met de opdrachtgever. Voor ieder overleg deelde ik vooraf de actuele planning, beslispunten en risico's. Tijdens het gesprek vroeg ik door naar onduidelijke feedback en legde ik afspraken direct vast. "
        "Na afloop stuurde ik een korte samenvatting en verwerkte ik goedgekeurde wijzigingen in het projectbord."
    ),
    "B1-K2-W2": (
        "Ik heb het eindproduct gepresenteerd aan de opdrachtgever met een vaste route van gebruikersprobleem naar oplossing. Ik demonstreerde zoeken, vergelijken, datumselectie en responsive gedrag en koppelde elke functie aan een acceptatiecriterium. "
        "Technische details lichtte ik alleen toe wanneer ze relevant waren en vragen beantwoordde ik met voorbeelden uit de applicatie en testresultaten."
    ),
    "B1-K2-W3": (
        "Ik heb gedurende het project actief om feedback gevraagd en mijn eigen keuzes kritisch beoordeeld. Mijn planning was duidelijk, maar ik had de beschikbaarheid van de API eerder moeten controleren. "
        "Door tijdelijk met testdata te werken voorkwam ik vertraging. In een volgend project plan ik al in de eerste fase een technische proefkoppeling en leg ik testbewijs direct per taak vast."
    ),
}

screenshots = {
    "planning": image("03-planning.jpg"),
    "result": image("01-eindresultaat.jpg"),
    "tests": image("02-testresultaten.jpg"),
}
image_map = {
    "B1-K1-W1": [screenshots["planning"]],
    "B1-K1-W2": [screenshots["result"]],
    "B1-K1-W3": [screenshots["result"]],
    "B1-K1-W4": [screenshots["tests"]],
    "B1-K1-W5": [screenshots["tests"], screenshots["planning"]],
    "B1-K2-W1": [screenshots["planning"]],
    "B1-K2-W2": [screenshots["result"], screenshots["tests"]],
    "B1-K2-W3": [screenshots["planning"]],
}

for wp in report["work_processes"]:
    code = wp["code"]
    wp["selected"] = True
    wp["accountability"] = accountability[code]
    wp["evidence"] = [
        f"Git-commitreeks en code review voor {code}",
        f"Controleerbaar resultaat en feedbacknotitie gekoppeld aan {code}",
    ]
    wp["evidence_images"] = image_map[code]

report["evaluation"] = {
    "professional": (
        "Ik wilde leren hoe ik een volledig webproject van eisen tot overdracht aantoonbaar kon uitvoeren. Ik heb geleerd om ontwerpkeuzes direct aan acceptatiecriteria te koppelen en om API-fouten en laadstatussen expliciet af te handelen. "
        "De herbruikbare componenten en de testaanpak gingen goed. De technische proefkoppeling had eerder in de planning gemoeten."
    ),
    "personal": (
        "Ik heb duidelijker gecommuniceerd over risico's en feedback sneller omgezet naar concrete taken. Tijdens drukke dagen bleef ik productief door kleine opleverbare stappen te kiezen. "
        "Ik kan nog verbeteren door eerder hulp te vragen wanneer een externe afhankelijkheid onzeker is en door na ieder overleg onmiddellijk bewijs te archiveren."
    ),
    "next_project": (
        "In mijn volgende project wil ik in de eerste week een automatische testomgeving en een technische proof-of-concept opzetten. Daarnaast wil ik toegankelijkheid structureel per component controleren in plaats van alleen aan het einde. "
        "Zo wil ik risico's eerder zichtbaar maken en de eindcontrole korter en betrouwbaarder maken."
    ),
}
report["declaration_accepted"] = True

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(OUTPUT)
