"""Keep event version and validity metadata required for route verification."""
import unittest
from opentransportdata import extract_basel_situations


class EventMetadataTests(unittest.TestCase):
    def test_metadata_survives_xml_extraction(self):
        payload = b'''<root><situationRecord id="event">
        <situationRecordVersionTime>2026-10-03T12:00:00Z</situationRecordVersionTime>
        <validityStatus>definedByValidityTimeSpec</validityStatus>
        <overallStartTime>2026-10-03T10:00:00Z</overallStartTime>
        <validPeriod><recurringTimePeriodOfDay/></validPeriod>
        <generalPublicComment><value>Aufgehoben: Basel road event</value></generalPublicComment>
        </situationRecord></root>'''
        event = extract_basel_situations(payload)[0]
        self.assertEqual(event["updated_at"], "2026-10-03T12:00:00Z")
        self.assertEqual(event["validity_status"], "definedByValidityTimeSpec")
        self.assertTrue(event["complex_validity"])
        self.assertTrue(event["descriptions"][0].startswith("Aufgehoben:"))
