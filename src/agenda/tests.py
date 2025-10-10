import datetime

from agenda.templatetags import math_tag, hour_to_percent
from dev .test_utils import TestCase


class TestTemplateTags(TestCase):
    """
    Test the template tags in agenda.templatetags.math_tag
    """

    def test_divide(self):
        self.assertTrue(len(math_tag.divide(10, 3)) > 3)
        self.assertEqual(math_tag.divide(10, 2, percent=True), "500.00%")
        with self.assertRaises(ZeroDivisionError):
            math_tag.divide(10, 0)
    
    def test_to_rem(self):
        """
        Test the to_rem template tag.
        """
        time1 = datetime.time(10, 0)
        time2 = datetime.time(8, 0)
        self.assertEqual(hour_to_percent.to_rem(time1, time2), 8)
        self.assertEqual(hour_to_percent.to_rem(time1), 8)
    
    def test_event_classes(self):
        """
        Test the event_classes template tag.
        """
        class MockEvent:
            def __init__(self, subject, beghour, endhour):
                self.subject = subject
                self.beghour = beghour
                self.endhour = endhour
        
        ev = MockEvent("math", datetime.time(8, 0), datetime.time(10, 0))
        height = hour_to_percent.to_rem(ev.endhour, ev.beghour)
        self.assertEqual(height, 8)
        classes = hour_to_percent.event_classes(ev)
        self.assertIn("large", classes)
        self.assertIn("border-l-0", classes, "first event")
        self.assertIn("border-r-0", classes, "last event")
        self.assertIn("pt-2", classes, "duration > 1.5H")
        classes = hour_to_percent.event_classes(ev, overlap_nb=2, position=1)
        self.assertNotIn("large", classes)
        self.assertNotIn("border-l-0", classes, "first event")
        self.assertIn("border-r-0", classes, "last event")
        self.assertIn("pt-2", classes, "duration > 1.5H")
        ev.endhour = datetime.time(9, 0)
        classes = hour_to_percent.event_classes(ev, overlap_nb=2, position=0)
        self.assertNotIn("large", classes)
        self.assertIn("border-l-0", classes, "first event")
        self.assertNotIn("border-r-0", classes, "last event")
        self.assertNotIn("pt-2", classes, "duration <= 1.5H")