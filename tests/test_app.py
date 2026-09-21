import io
import json
import unittest
import zipfile

from app import app, empty_report


def filled_report():
    report = empty_report()
    report["student"].update({"name":"Nikita Vlasov","student_number":"12345","class_name":"WEB3A","company":"Voorbeeldbedrijf","practice_supervisor":"Begeleider","bpv_supervisor":"BPV-begeleider"})
    report["project"].update({"title":"Voorbeeldproject","subtitle":"Examenverslag","version":"1.0","report_date":"2026-09-21","exam_name":"Softwareproject","start_date":"2026-09-01","end_date":"2026-09-21","description":"Ik ontwikkelde een lokale verslaggenerator.","introduction":"Voor dit project heb ik een lokale verslaggenerator ontworpen, gebouwd en getest.","products":["Werkende webapplicatie","Documentatie"]})
    report["activities"] = ["Eisen analyseren", "Generator bouwen", "Exports testen"]
    report["resources"] = {"materials":["Python en Flask"],"people":["Opdrachtgever"],"means":["Computer en Git"],"knowledge":["Webontwikkeling en documentgeneratie"]}
    report["scope"] = {"included":["Lokale webapp en drie exports"],"excluded":["Cloudopslag"],"provided":["Feedback en beoordelingscriteria"]}
    for phase in report["planning"]:
        phase["period"] = "week 1"
        phase["tasks"] = [f"{phase['phase']} uitvoeren en controleren"]
    for wp in report["work_processes"]:
        wp["accountability"] = "Ik heb dit werkproces uitgevoerd, mijn keuzes afgestemd, het resultaat gecontroleerd en de feedback aantoonbaar verwerkt."
        wp["evidence"] = ["Git commit en screenshot"]
    report["evaluation"] = {"professional":"Ik heb geleerd hoe ik vanuit een JSON-model consistente documenten genereer en de uitvoer controleer.","personal":"Ik heb realistischer gepland, eerder feedback gevraagd en problemen stap voor stap opgelost.","next_project":"In een volgend project wil ik automatische visuele regressietests voor documentexports toevoegen."}
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

    def test_matrijzen_import(self):
        raw = {"opleiding_id":"2","kd_id":"3","naam":"Nikita","ov":"42","klas":"WEB3A","bedrijf":"Bedrijf","praktijk":"Praktijk","bpv":"BPV","examen":"Website","ep":"EP1","omschrijving":"Projectomschrijving","products":["Website"],"werkprocessen":[{"id":"104","code":"B1-K1-W1","naam":"Plant werkzaamheden","competenties":"Plannen en organiseren, Analyseren","pi":["Bewaakt planning"],"desc":"Ik heb de planning bewaakt."}]}
        response = self.client.post("/api/normalize", json=raw)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["student"]["name"], "Nikita")
        self.assertTrue(data["work_processes"][0]["selected"])
        self.assertEqual(sum(1 for item in data["work_processes"] if item["selected"]), 1)


if __name__ == "__main__":
    unittest.main()
