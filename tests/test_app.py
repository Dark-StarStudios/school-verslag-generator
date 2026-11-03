import io
import json
import unittest
import zipfile
import base64

from app import app, empty_report, normalize_report, report_sections


def filled_report():
    report = empty_report()
    report["student"].update({"name":"Nikita Vlasov","student_number":"12345","class_name":"WEB3A","company":"Voorbeeldbedrijf","practice_supervisor":"Begeleider","bpv_supervisor":"BPV-begeleider"})
    report["project"].update({"title":"Voorbeeldproject","subtitle":"Examenverslag","version":"1.0","report_date":"2026-09-21","exam_name":"Softwareproject","exam_number":"EP1","start_date":"2026-09-01","end_date":"2026-09-21","description":"Ik ontwikkelde een lokale verslaggenerator.","introduction":"Voor dit project heb ik een lokale verslaggenerator ontworpen, gebouwd en getest.","products":["Werkende webapplicatie","Documentatie"]})
    report["activities"] = ["Eisen analyseren", "Generator bouwen", "Exports testen"]
    report["resources"] = {"materials":["Python en Flask"],"people":["Opdrachtgever"],"means":["Computer en Git"],"knowledge":["Webontwikkeling en documentgeneratie"]}
    report["scope"] = {"included":["Lokale webapp en drie exports"],"excluded":["Cloudopslag"],"provided":["Feedback en beoordelingscriteria"]}
    for phase in report["planning"]:
        phase["period"] = "week 1"
        phase["tasks"] = [f"{phase['phase']} uitvoeren en controleren"]
    for wp in report["work_processes"]:
        wp["accountability"] = "Ik heb dit werkproces uitgevoerd, mijn keuzes afgestemd, het resultaat gecontroleerd en de feedback aantoonbaar verwerkt."
        wp["evidence"] = ["Git commit en screenshot"]
        wp["evidence_images"] = []
    choice = report["keuzedelen"][0]
    for process in choice["work_processes"]:
        process["selected"] = True
        process["accountability"] = "Ik heb dit werkproces van het keuzedeel uitgevoerd, mijn keuzes onderbouwd en het resultaat aantoonbaar gecontroleerd."
        process["evidence"] = ["Onderbouwing en controleerbaar resultaat"]
    tiny_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode("ascii")
    report["work_processes"][0]["evidence_images"] = [{"name":"bewijs.png", "type":"image/png", "data":"data:image/png;base64," + tiny_png}]
    report["evaluation"] = {"professional":"Ik heb geleerd hoe ik vanuit een JSON-model consistente documenten genereer en de uitvoer controleer.","personal":"Ik heb realistischer gepland, eerder feedback gevraagd en problemen stap voor stap opgelost.","next_project":"In een volgend project wil ik automatische visuele regressietests voor documentexports toevoegen."}
    report["design"] = {"heading_color":"#2F5597", "heading_font":"Georgia", "body_font":"Times New Roman"}
    report["declaration_accepted"] = True
    return report


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Verslagmaker", response.data)

    def test_exports(self):
        report = filled_report()
        for kind, signature in (("pdf", b"%PDF"), ("docx", b"PK"), ("odt", b"PK")):
            response = self.client.post(f"/api/export/{kind}", json=report)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data.startswith(signature))
        docx = self.client.post("/api/export/docx", json=report).data
        with zipfile.ZipFile(io.BytesIO(docx)) as archive:
            document = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("Voorbeeldproject", document)
            self.assertIn("B1-K1-W1", document)
            self.assertIn("OV-nummer", document)
            self.assertIn("01-09-2026", document)
            self.assertIn("EP1", document)
            self.assertIn("Werkende webapplicatie", document)
            self.assertIn("K0505 - Verdieping software", document)
            self.assertIn("D1-K1-W2 - Maakt zich de software eigen", document)
            styles = archive.read("word/styles.xml").decode("utf-8")
            self.assertIn("2F5597", styles)
            self.assertIn("Georgia", styles)
            self.assertIn("Times New Roman", styles)
            self.assertTrue(any(name.startswith("word/media/") for name in archive.namelist()))

        odt = self.client.post("/api/export/odt", json=report).data
        with zipfile.ZipFile(io.BytesIO(odt)) as archive:
            document = archive.read("content.xml").decode("utf-8")
            self.assertIn("Startdatum examen: 01-09-2026", document)
            self.assertIn("Persoonlijke evaluatie", document)
            self.assertIn("K050501", document)
            self.assertIn("Maakt een keuze voor software", document)
            styles = archive.read("styles.xml").decode("utf-8")
            self.assertIn("#2F5597", styles)
            self.assertIn("Georgia", styles)
            self.assertIn("Times New Roman", styles)
            self.assertTrue(any(name.startswith("Pictures/") for name in archive.namelist()))

    def test_project_dates_and_products_are_report_sections(self):
        sections = dict(report_sections(filled_report()))
        project_data = dict(sections["Projectgegevens"])
        self.assertEqual(project_data["Startdatum examen"], "01-09-2026")
        self.assertEqual(project_data["Einddatum examen"], "21-09-2026")
        self.assertEqual(project_data["Examennummer"], "EP1")
        self.assertEqual(project_data["Op te leveren producten"], ["Werkende webapplicatie", "Documentatie"])

    def test_old_native_concept_gets_new_defaults(self):
        normalized = normalize_report({"schema":"school-verslag/1.0", "student":{"name":"Nikita"}, "project":{"title":"Test"}})
        self.assertEqual(normalized["student"]["name"], "Nikita")
        self.assertIn("start_date", normalized["project"])
        self.assertIn("resources", normalized)
        self.assertEqual(len(normalized["keuzedelen"]), 4)
        self.assertEqual(normalized["design"]["heading_color"], "#5B9BD5")

    def test_matrijzen_import(self):
        raw = {"opleiding_id":"2","kd_id":"3","naam":"Nikita","ov":"42","klas":"WEB3A","bedrijf":"Bedrijf","praktijk":"Praktijk","bpv":"BPV","examen":"Website","ep":"EP1","omschrijving":"Projectomschrijving","products":["Website"],"werkprocessen":[{"id":"104","code":"B1-K1-W1","naam":"Plant werkzaamheden","competenties":"Plannen en organiseren, Analyseren","pi":["Bewaakt planning"],"desc":"Ik heb de planning bewaakt."}]}
        response = self.client.post("/api/normalize", json=raw)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["student"]["name"], "Nikita")
        self.assertTrue(data["work_processes"][0]["selected"])
        self.assertEqual(sum(1 for item in data["work_processes"] if item["selected"]), 1)
        self.assertEqual(len(data["keuzedelen"]), 4)

    def test_keuzedelen_are_report_sections(self):
        sections = dict(report_sections(filled_report()))
        self.assertIn("Keuzedelen", sections)
        title, choice = sections["Keuzedelen"][0]
        self.assertEqual(title, "K0505 - Verdieping software")
        self.assertEqual(choice["certificate"], "K050501")
        self.assertEqual(len(choice["work_processes"]), 2)
        self.assertTrue(all(process[1]["body"] for process in choice["work_processes"]))

    def test_only_selected_keuzedeel_processes_are_exported(self):
        report = filled_report()
        report["keuzedelen"][0]["work_processes"][1]["selected"] = False

        sections = dict(report_sections(report))
        title, choice = sections["Keuzedelen"][0]

        self.assertEqual(title, "K0505 - Verdieping software")
        self.assertEqual(len(choice["work_processes"]), 1)
        self.assertEqual(choice["work_processes"][0][0], "D1-K1-W1 - Maakt een keuze voor software")

    def test_custom_cover_and_verdana_are_exported(self):
        report = filled_report()
        report["design"].update({
            "heading_font": "Verdana",
            "body_font": "Verdana",
            "cover_background_color": "#93A8EE",
            "cover_background_type": "gradient",
            "cover_gradient_end_color": "#3858E8",
            "cover_gradient_direction": "diagonal",
            "cover_text_color": "#FFFFFF",
            "declaration_color": "#D32F2F",
            "cover_logo": report["work_processes"][0]["evidence_images"][0],
        })

        docx = self.client.post("/api/export/docx", json=report)
        self.assertEqual(docx.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(docx.data)) as archive:
            document = archive.read("word/document.xml").decode("utf-8")
            styles = archive.read("word/styles.xml").decode("utf-8")
            self.assertIn("93A8EE", document)
            self.assertIn("3858E8", document)
            self.assertIn("D32F2F", document)
            self.assertIn("Verdana", styles)
            self.assertTrue(any(name.startswith("word/media/") for name in archive.namelist()))

        self.assertEqual(self.client.post("/api/export/pdf", json=report).status_code, 200)
        odt = self.client.post("/api/export/odt", json=report)
        self.assertEqual(odt.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(odt.data)) as archive:
            content = archive.read("content.xml").decode("utf-8")
            self.assertIn('draw:fill="gradient"', content)
            self.assertIn("#3858E8", content)
            self.assertIn("#D32F2F", content)


if __name__ == "__main__":
    unittest.main()
