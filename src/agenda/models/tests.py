"""
date: 2024-03-31
"""
import datetime
from datetime import time
import logging
from unittest import skip

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ValidationError
from django.test import tag
from django.utils import timezone

import agenda.models as am
from agenda.models import attendance, timetable as table, compatibility
from dev.test_utils import TestCase
from dev.test_data import CreateUserMixin
import users.models as um

class WithWeeks(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        gen = am.HolidayGenerator()
        today = datetime.date(datetime.date.today().year, 9, 7)
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        end = today + datetime.timedelta(100)
        cls.weeks = gen.generate_between(today, end)
        cls.monday = today

class TestYear(TestCase):

    @tag("download")
    def test_download(self):
        p = settings.AGENDA_ICAL_FILE
        p.unlink(missing_ok=True)
        with self.settings(AGENDA_OFFICIAL_ICAL_URL="https://prepa.blaise-pascal.fr"):
            with self.assertLogs(level=logging.ERROR):
                am.HolidayGenerator()
        with self.assertNoLogs():
            am.HolidayGenerator()
        self.assertTrue(p.exists())
    
    def test_generator(self):
        gen = am.HolidayGenerator()
        n = len(gen.holidays)
        self.assertTrue(n > 0)
        gen.parse_holidays() # should be a no-op
        self.assertEqual(len(gen.holidays), n)
        today = datetime.date.today()
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        self.assertEqual(today.weekday(), 0, "Monday")
        end = today + datetime.timedelta(10)
        res = gen.generate_between(today, end)
        self.assertEqual(len(res), 2, "2 weeks in a 10 days span")
        self.assertEqual(am.Week.objects.count(), 2)
        self.assertEqual(res[0].begin, today)
        self.assertEqual(res[1].begin.weekday(), 0)
        self.assertEqual(res[0].end.weekday(), 6, "Sunday")
        self.assertEqual(res[1].begin, res[0].end + datetime.timedelta(1))
        self.assertTrue(datetime.date(today.year, 12, 25) in gen.holidays)
        self.assertFalse(datetime.date(today.year, 9, 25) in gen.holidays)
    
    def test_model_methods(self):
        gen = am.HolidayGenerator()
        today = datetime.date.today()
        today = datetime.date(today.year, 12, 25) # we're in holiday
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        end = today + datetime.timedelta(10)
        week1, week2 = gen.generate_between(today, end, True)
        self.assertIsNone(week1.nb)
        self.assertEqual(len(week1.short_name()), 13, "2 dates + 2 spaces + '-'")
        self.assertTrue(week1.active)
        self.assertTrue(len(str(week1)) > 13, "2 dates + 2 spaces + '-'")
        week1.nb = 1
        
        self.assertEqual(len(week1.short_name()), 16, "2 dates + 2 spaces + '-' + nb")
        self.assertTrue(len(str(week1)) > 16, "2 dates + 2 spaces + '-'")
        adj = week1.adjacents()
        self.assertFalse("prev" in adj)
        self.assertTrue("next" in adj)
        self.assertEqual(adj["next"], week2)
        self.assertFalse("next" in week2.adjacents())
        self.assertIn(today, week1)
        self.assertNotIn(today, week2)
        dt = datetime.datetime(today.year, today.month, today.day)
        self.assertIn(dt, week1, "support datetime objects")
        with self.assertRaises(ValueError):
            self.assertIn(4, week1)
        
    def test_manager(self):
        gen = am.HolidayGenerator()
        today = datetime.date.today()
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        self.assertEqual(today.weekday(), 0, "Monday")
        end = today + datetime.timedelta(50)
        res = gen.generate_between(today, end)
        # no active week
        with self.assertRaises(ObjectDoesNotExist):
            self.assertEqual(am.Week.objects.for_today(), res[0])
        am.Week.objects.update(active=True)
        self.assertEqual(am.Week.objects.for_today(), res[0])


class TestPeriodic(WithWeeks):

    def test_manager(self):
        am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
            day=0, begweek=1, endweek=10, periodicity=2)
        am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
            day=0, begweek=2, endweek=10, periodicity=2)
        am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
            day=0, begweek=1, endweek=10, periodicity=3)
        am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
            day=0, begweek=2, endweek=10, periodicity=3)
        am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
            day=0, begweek=3, endweek=10, periodicity=3)
        for i in range(1, 10):
            with self.subTest(nb=i):
                week = am.Week.objects.get(nb=i)
                self.assertEqual(am.PeriodicEvent.objects.for_week(week).count(), 2)
        # week = am.Week(nb=0)
        # self.assertEqual(am.PeriodicEvent.objects.for_week(week).count(), 0)
        week = am.Week.objects.get(nb=11)
        self.assertEqual(am.PeriodicEvent.objects.for_week(week).count(), 0)
        am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
            day=0, begweek=0, endweek=10, periodicity=5)
        for i in range(1, 10):
            with self.subTest(nb=i):
                week = am.Week.objects.get(nb=i)
                qs = am.PeriodicEvent.objects.for_week(week)
                self.assertEqual(qs.count(), 2 if i != 5 else 3)
                for ev in qs:
                    self.assertTrue(ev.occur_in_week(week))
    
    def test_full_label(self):
        ev = am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
            day=0, begweek=1, endweek=10, periodicity=2, label="Cours",
            subject="math")
        self.assertEqual(ev.full_label, "Cours de math")
        ev.label = ev.full_label
        self.assertEqual(ev.full_label, "Cours de math")
        

class TestBaseEvent(WithWeeks):

    def test_auto_week(self):
        b = timezone.now() + datetime.timedelta(weeks=52)
        e = b + datetime.timedelta(0, 60*60*2) # 2 hours
        with self.assertRaises(ValueError):
            am.BaseEvent.objects.create(begin=b, end=e, label="")
        # make today a monday
        today = self.monday
        self.assertEqual(today.weekday(), 0, "Monday")
        b = datetime.datetime.combine(today, time(8))
        b = timezone.make_aware(b)
        e = b + datetime.timedelta(0, 60*60*2) # 2 hours
        ev = am.BaseEvent(begin=b, end=e, label="")
        ev.save()
        self.assertIsNotNone(ev.week)
        self.assertIn(ev.begin.date(), ev.week)
        self.assertIn(str(ev.begin)[:5], str(ev))
        ev.label = "Label"
        self.assertIn("Label", str(ev))
    
    def test_week_update(self):
        # week should change if begin changes
        b = datetime.datetime.combine(self.monday, time(8))
        b = timezone.make_aware(b)
        e = b + datetime.timedelta(0, 60*60*2) # 2 hours
        ev = am.BaseEvent(begin=b, end=e, label="")
        ev.save()
        self.assertIsNotNone(ev.week)
        week = ev.week
        b = b + datetime.timedelta(days=8)  # next week
        ev.begin = b
        ev.end = b + datetime.timedelta(0, 60*60*2) # 2 hours
        ev.save()
        self.assertIsNotNone(ev.week)
        self.assertNotEqual(ev.week, week, "week should change")

    def test_spans(self):
        # create some events
        beghour = datetime.datetime.combine(self.monday, datetime.time(8))
        beghour = timezone.make_aware(beghour)
        self.assertTrue(timezone.is_aware(beghour))
        endhour = beghour + datetime.timedelta(0, 60*60*2)
        ev = am.BaseEvent.objects.create(begin=beghour, end=endhour, label="")
        self.assertTrue(timezone.is_aware(ev.begin))
        spans = ev.to_span()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].beghour, time(8), "tz management")
        endhour = beghour + datetime.timedelta(0, 60*60*26)
        ev.end = endhour
        ev.save()
        self.assertEqual(len(ev.to_span()), 2)
        endhour = beghour + datetime.timedelta(0, 60*60*23) # should end before MIN_HOUR
        ev.end = endhour
        ev.save()
        self.assertEqual(len(ev.to_span()), 1)
        endhour = beghour + datetime.timedelta(3, 60*60*2)
        ev.end = endhour
        ev.save()
        self.assertEqual(len(list(ev._days())), 4)
        self.assertEqual(len(ev.to_span()), 4)
        endhour = beghour + datetime.timedelta(15, 60*60*2)
        ev.end = endhour
        ev.save()
        self.assertEqual(len(ev.to_span()), 7, "truncate to one week")

class TestAttendance(WithWeeks):

    def test_grouper(self):
        grouper = am.attendance.Grouper()
        self.assertEqual(len(grouper.explode_range('1-2')), 2)
        self.assertEqual(grouper.explode_range('all'), ('all', ))
        self.assertEqual(grouper.explode_range('M. moi'), ('M. moi', ))
        self.assertEqual(len(grouper.explode_range('1')), 1)
        self.assertEqual(list(grouper.explode_range('1-3')), [1, 2, 3])
        self.assertEqual(grouper.minify_groups([1, 2, 3, 4]),
                         '1-4', 'contiguous range')
        self.assertEqual(grouper.minify_groups([1, 2, 3, 5, 6, 7]),
                         '1-3,5-7', '2 range')
        self.assertEqual(grouper.minify_groups([1, 2, 3, 5]),
                         '1-3,5', '1 range, 1 alone')
        self.assertEqual(grouper.minify_groups([1, 2, 3, 5, 7, 8, 9]),
                         '1-3,5,7-9', '2 range, 1 alone')    
    
    def test_attendance_field(self):
        b = datetime.datetime.combine(self.monday, time(8))
        b = timezone.make_aware(b)
        ev1 = am.BaseEvent.objects.create(
            begin=b,
            end=b + datetime.timedelta(0,60*60*2),
            label=""
        )
        for i in range(1,4):
            # 3 groups
            for j in range(3):
                # of 3 students
                um.User.objects.create_student(username=f"user{3*i+j}", colle_group=i)
        um.User.objects.create_teacher(title="M.", last_name="moi", first_name="a")
        self.assertEqual(ev1.attendants.count(), 0)
        self.assertEqual(ev1._attendance_string, "")
        ev1.attendance_string = "1-3"
        self.assertEqual(ev1.attendants.count(), 9)
        self.assertEqual(ev1._attendance_string, "1-3")
        ev1.attendance_string = "2,1,M. moi"
        self.assertEqual(ev1.attendants.count(), 7)
        with self.assertRaises(ValidationError):
            ev1.attendance_string = "Unknown user"
        ev1.attendance_string = ""
        self.assertEqual(ev1.attendants.count(), 0)
    
    def test_attendance_reset(self):
        # check changing to same value trigger magic method
        b = datetime.datetime.combine(self.monday, time(8))
        b = timezone.make_aware(b)
        ev1 = am.BaseEvent.objects.create(
            begin=b,
            end=b + datetime.timedelta(0,60*60*2),
            label=""
        )
        for i in range(1,4):
            # 3 groups
            for j in range(3):
                # of 3 students
                um.User.objects.create_student(username=f"user{3*i+j}", colle_group=i)
        ev1.attendance_string = "1-3"
        self.assertEqual(ev1.attendants.count(), 9)
        self.assertEqual(ev1._attendance_string, "1-3")
        ev1._groups = [1, 2, 3]
        ev1.attendance_string = "1-3"
        self.assertEqual(ev1.attendants.count(), 9)
        self.assertFalse(hasattr(ev1, "_groups"))

class TestColle(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        gen = am.HolidayGenerator()
        today = datetime.date(datetime.date.today().year, 9, 7)
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        end = today + datetime.timedelta(50)
        cls.weeks = gen.generate_between(today, end)
        cls.monday = today

    def test_event(self):
        teacher = um.User.objects.create_teacher(username="a")
        cev = am.ColleEvent.objects.create(beghour=time(8), endhour=time(10),
            teacher=teacher, day=0, subject="Math")
        self.assertEqual(cev.short_name(), "lundi 08:00-10:00")
        self.assertEqual(len(str(cev)), len(cev.short_name()) + 1)
    
    def test_colleplanning(self):
        teacher = um.User.objects.create_teacher(username="a")
        cev = am.ColleEvent.objects.create(beghour=time(8), endhour=time(10),
            teacher=teacher, day=0, subject="Math")
        cps = []
        studs = []
        for i in range(3):
            st = um.User.objects.create_student(username=f"stud{i}", colle_group=i+1)
            cg = st.studentcollegroup.first()
            cps.append(
                am.CollePlanning.objects.create(
                    event=cev, week=self.weeks[i], group=cg.group)
            )
            studs.append(st)
        self.assertEqual(am.CollePlanning.objects.for_user(teacher).count(), 3)
        for st in studs:
            self.assertEqual(am.CollePlanning.objects.for_user(st).count(), 1)
        anon = AnonymousUser()
        self.assertEqual(am.CollePlanning.objects.for_user(anon).count(), 0)
        self.assertIn("groupe 1, semaine 1", str(cps[0]))
        self.assertEqual(cps[0].attendance_string, "1,")
        

class TestCompatibility(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        gen = am.HolidayGenerator()
        today = datetime.date(datetime.date.today().year, 9, 7)
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        end = today + datetime.timedelta(50)
        gen.generate_between(today, end)
        cls.monday = today
    
    def test_compatibility_object(self):
        c = compatibility.Compatibility(True)
        self.assertTrue(c)
        self.assertEqual(str(c), "True")
        
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        ev1 = am.BaseEvent.objects.create(
            begin=begin,
            end=begin + datetime.timedelta(0,60*60*2),
            label=""
        )
        with self.assertRaises(ValueError):
            compatibility.Compatibility(False)
        with self.assertRaises(ValueError):
            compatibility.Compatibility(False, ev1)
        with self.assertRaises(ValueError):
            compatibility.Compatibility(False, ev1, ev1)
        user=um.User.objects.create_teacher(username="a")
        c = compatibility.Compatibility(False, ev1, ev1, user=user)
        self.assertTrue(c)
        ev2 = am.BaseEvent.objects.create(
            begin=begin,
            end=begin + datetime.timedelta(0,60*60*2),
            label=""
        )
        c = compatibility.Compatibility(False, ev1, ev2, user)
        self.assertFalse(c)
        self.assertNotIn("à la date", str(c))
        c = compatibility.Compatibility(False, ev1, ev2, user, time=begin)
        self.assertIn("à la date", str(c))
    
    def test_base_compatible(self):
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        ev1 = am.BaseEvent.objects.create(
            begin=begin,
            end=begin + datetime.timedelta(0,60*60*2),
            label=""
        )
        ev2 = am.BaseEvent.objects.create(
            begin=begin+ datetime.timedelta(0,60*60),
            end=begin + datetime.timedelta(0,60*60*3),
            label=""
        )

        um.User.objects.create_student(username="user1", colle_group=1)
        um.User.objects.create_student(username="user2", colle_group=1)
        self.assertTrue(attendance.AttComputer.changed_groups)
        ev1.attendance_string = "1"
        self.assertFalse(attendance.AttComputer.changed_groups)
        um.User.objects.create_student(username="user3", colle_group=2)
        ev2.attendance_string = "2"

        self.assertTrue(ev1.compatible(ev2), msg="same time, user OK")
        self.assertTrue(ev2.compatible(ev1), msg="same time, user OK")
        ev2.attendance_string = "1,2"
        self.assertEqual(ev2.attendants.count(), 3)
        #ev2 = am.BaseEvent.objects.get(pk=ev2.pk)  # account for attendance_list cached property
        self.assertEqual(ev1.attendants.filter(pk__in=ev2.attendants.all()).count(), 2,
                         msg="user intersection check")
        self.assertFalse(ev1.compatible(ev2), msg="same time, user intersection")
        self.assertFalse(ev2.compatible(ev1), msg="same time, user intersection")
        # test "all" attendance
        ev2.attendance_string = "all"
        #ev2 = am.BaseEvent.objects.get(pk=ev2.pk)  # account for attendance_list cached property
        self.assertEqual(ev2.attendants.count(), 3)
        
        self.assertEqual(ev1.attendants.filter(pk__in=ev2.attendants.all()).count(), 2,
                         msg="user intersection check")
        self.assertFalse(ev1.compatible(ev2), msg="same time, user intersection")
        self.assertFalse(ev2.compatible(ev1), msg="same time, user intersection")

        ev3 = am.BaseEvent.objects.create(
            begin=begin + datetime.timedelta(1,60*60),
            end=begin + datetime.timedelta(1,60*60*3),
            label=""
        )

        ev3.attendance_string = "1,2"
        self.assertTrue(ev1.compatible(ev3), msg="different dates")
        self.assertTrue(ev3.compatible(ev2), msg='different dates')
        ev2.begin = begin + datetime.timedelta(0,2*60*60)
        ev2.end = begin + datetime.timedelta(0,4*60*60)
        self.assertTrue(ev1.compatible(ev3), msg="adjacents")
        self.assertTrue(ev3.compatible(ev2), msg="adjacents")
    
    def test_comparisons(self):
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        ev1 = am.BaseEvent.objects.create(
            begin=begin,
            end=begin + datetime.timedelta(0,60*60*2),
            label=""
        )
        ev2 = am.BaseEvent.objects.create(
            begin=begin+ datetime.timedelta(0,60*60),
            end=begin + datetime.timedelta(0,60*60*3),
            label=""
        )

        self.assertTrue(ev1 < ev2)
        self.assertTrue(ev1 <= ev2)
        self.assertTrue(ev2 > ev1)
        self.assertTrue(ev2 >= ev1)
        self.assertNotEqual(ev1, ev2)
        self.assertEqual(ev1, ev1)

        # periodic comparison
        ev1 = am.PeriodicEvent.objects.create(begweek=0, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev2 = am.PeriodicEvent.objects.create(begweek=0, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(9), endhour=time(10))
        self.assertTrue(ev1 < ev2)
        self.assertTrue(ev1 <= ev2)
        self.assertTrue(ev2 > ev1)
        self.assertTrue(ev2 >= ev1)
        self.assertNotEqual(ev1, ev2)
        self.assertEqual(ev1, ev1)
    
    def test_periodic_compatible(self):
        ev1 = am.PeriodicEvent.objects.create(begweek=0, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev1.save()
        self.assertIn(ev1.day_label, str(ev1))
        users = [
            um.User.objects.create_student(username=str(i), colle_group=1)
            for i in range(3)]
        ev1.attendance_string = "1"
        ev2 = am.PeriodicEvent.objects.create(begweek=0, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev2.save()
        ev2.attendance_string = "1"
        self.assertFalse(ev1.compatible(ev2), "same event incompatible")
        self.assertFalse(ev2.compatible(ev1), "same event incompatible")
        ev2.beghour = time(10)
        ev2.endhour = time(12)
        self.assertTrue(ev1.compatible(ev2), "compatible hours")
        self.assertTrue(ev2.compatible(ev1), "compatible hours")
        ev2.beghour = time(8)
        ev2.endhour = time(10)
        ev2.begweek = 1
        self.assertTrue(ev1.compatible(ev2), "compatible weeks")
        self.assertTrue(ev2.compatible(ev1), "compatible weeks")
        ev2.begweek = 0
        ev2.day = 1
        self.assertTrue(ev1.compatible(ev2), "compatible days")
        self.assertTrue(ev2.compatible(ev1), "compatible days")
        ev2.day = 0
        with self.assertRaises(ValidationError):
            ev2.attendance_string = "M. moi"
        um.User.objects.create_teacher(title="M.", last_name="moi", first_name="M")
        ev2.attendance_string = "M. moi"
        #ev2 = am.PeriodicEvent.objects.get(pk=ev2.pk)  # account for cached property
        self.assertTrue(ev2.compatible(ev1, [u.pk for u in users[1:]]),
            "compatible attendance")

        # more complex periodicity check
        ev1.attendants.set(users)
        ev2.attendants.set(users)
        ev1 = am.PeriodicEvent.objects.get(pk=ev1.pk)
        ev2 = am.PeriodicEvent.objects.get(pk=ev2.pk)
        ev1.periodicity = 5
        ev1.begweek = 1
        self.assertFalse(ev1.compatible(ev2), "intersection in week 6")
        self.assertFalse(ev2.compatible(ev1), "intersection in week 6")
        ev1.endweek = 5
        self.assertTrue(ev1.compatible(ev2), "intersection outside ev1 week range")
        self.assertTrue(ev2.compatible(ev1), "intersection outside ev1 week range")
        ev1.endweek = 35
        ev1.begweek = 1
        ev1.periodicity = 7
        self.assertFalse(ev1.compatible(ev2), "intersection in week 35")
        self.assertFalse(ev2.compatible(ev1), "intersection in week 35")
        ev2.endweek = 7
        self.assertTrue(ev1.compatible(ev2), "intersection outside ev2 week range")
        self.assertTrue(ev2.compatible(ev1), "intersection outside ev2 week range")
    
    def test_mixte_compatibe(self):
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        ev1 = am.BaseEvent.objects.create(
            begin=begin,  # monday
            end=begin + datetime.timedelta(0,2*60*60),
            label="")
        self.assertIsNotNone(ev1.week)
        self.assertEqual(ev1.week.nb, 1)
        users = [um.User.objects.create(username=str(i)) for i in range(4)]
        ev1.attendants.set(users)
        ev2 = am.PeriodicEvent.objects.create(
            begweek=1, endweek=35, subject="subject", periodicity=2,
            day=0, beghour=time(8), endhour=time(10))
        ev2.attendants.set(users)
        occ = ev2.get_for_week(ev1.week)
        self.assertIsNotNone(occ)
        self.assertEqual(occ.week, ev1.week)
        self.assertEqual(occ.begin, ev1.begin)
        self.assertFalse(occ.time_compatible(ev1))
        self.assertEqual(type(occ), type(ev1))
        self.assertFalse(occ.compatible(ev1))
        self.assertFalse(ev1.compatible_other(ev2))

        self.assertFalse(ev2.compatible_other(ev1), "incompatible")
        self.assertFalse(ev2.compatible(ev1), "incompatible other")
        ev1.override = True
        self.assertTrue(ev2.compatible(ev1), "override")

        ev1.override = False
        id2 = ev2.id
        ev2 = am.PeriodicEvent.objects.get(pk=id2)
        ev2.begweek = 0

        self.assertTrue(ev1.compatible(ev2), "compatible weeks")
        ev2.begweek = 1
        ev2.beghour = time(10)
        ev2.endhour = time(12)
        self.assertTrue(ev1.compatible(ev2), "compatible hour")
        ev2.beghour = time(8)
        ev2.endhour = time(10)
        ev2.day = 1
        self.assertTrue(ev1.compatible(ev2), "compatible day")
    
    def test_colleplanning(self):
        teacher = um.User.objects.create_teacher(title="M.", last_name="moi", first_name="moi")
        for i in range(3):
            um.User.objects.create_student(username=str(i), colle_group=1)
            
        self.assertTrue(attendance.AttComputer.changed_groups)
        cev = am.ColleEvent.objects.create(beghour=time(8), endhour=time(10),
            teacher=teacher, day=0, subject="Math")
        week = am.Week.objects.filter(nb__gte=1).order_by("nb").first()
        self.assertEqual(week.nb, 1)
        cp = am.CollePlanning.objects.create(
            event=cev, week=week,
            group= um.ColleGroup.objects.get(nb=1)
        )
        self.assertEqual(cp.colle_group, 1)
        pev = am.PeriodicEvent.objects.create(
            begweek=1, endweek=35, subject="subject", periodicity=1,
            day=0, beghour=time(8), endhour=time(10))
        pev.attendance_string = "M. moi"
        self.assertFalse(cp.compatible(pev))
        self.assertFalse(pev.compatible(cp))
        pev.attendance_string = "2-3"
        self.assertTrue(cp.compatible(pev))
        self.assertTrue(pev.compatible(cp))
        pev.attendance_string = "1-3"
        self.assertFalse(cp.compatible(pev))
        self.assertFalse(pev.compatible(cp))
        pev.begweek = 2
        self.assertTrue(cp.compatible(pev))
        self.assertTrue(pev.compatible(cp))
        pev.begweek = 1
        cev.day = 1
        self.assertTrue(cp.compatible(pev))
        self.assertTrue(pev.compatible(cp))
        cev.day = 0
        pev.day = 1
        self.assertTrue(cp.compatible(pev))
        self.assertTrue(pev.compatible(cp))

        # test with baseEvent
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        ev1 = am.BaseEvent.objects.create(
            begin=begin,  # monday
            end=begin + datetime.timedelta(0,2*60*60),
            label="")
        self.assertEqual(ev1.week, week)
        ev1.attendance_string = "M. moi"
        self.assertFalse(cp.compatible(ev1))
        self.assertFalse(ev1.compatible(cp))
        cev.day = 1
        self.assertTrue(cp.compatible(ev1))
        self.assertTrue(ev1.compatible(cp))
        cev.day = 0
        ev1.attendance_string = "2"
        self.assertTrue(cp.compatible(ev1))
        self.assertTrue(ev1.compatible(cp))
        ev1.attendance_string = "M. moi"
        cev.beghour = time(10)
        cev.endhour = time(12)
        self.assertTrue(cp.compatible(ev1))
        self.assertTrue(ev1.compatible(cp))

class TestSortedList(TestCase):

    def test_base(self):
        L = table.SortedList()
        self.assertEqual(L.insert_index(0), 0)
        L.insert(0)
        L.append(1)
        with self.assertRaises(table.SortError):
            L.append(0)
        L2 = table.SortedList([2,3,4])
        L.extend(L2)
        self.assertEqual(L.insert_index(2.5), 3)
        self.assertEqual(L.insert(2.5), 3)
        self.assertEqual(L.insert_index(5), 6)
        self.assertEqual(L.insert(5), 6)
        with self.assertRaises(table.SortError):
            L.reverse()
        self.assertEqual(L.insert_index(5), 6)
        self.assertEqual(L.insert(5), 6)
        self.assertEqual(L.insert_index(6), 8)
        self.assertEqual(L.insert(6), 8)
        self.assertEqual(L.insert_index(5.5), 8)
        self.assertEqual(L.insert(5.5), 8)

    def test_insert_at(self):
        L = table.SortedList()
        L.append(1)
        with self.assertRaises(table.SortError):
            L.insert_at(0,4)
        with self.assertRaises(table.SortError):
            L.insert_at(1,-1)
        L.insert_at(1, 4)
        with self.assertRaises(table.SortError):
            L.insert_at(1,5)
        with self.assertRaises(table.SortError):
            L.insert_at(1,-1)
    
    def test_insert_index(self):
        L = table.SortedList()
        self.assertEqual(L.insert_index(1), 0)
        L.append(1)
        self.assertEqual(L.insert_index(1), 0)
        L.append(1)
        self.assertEqual(L.insert_index(0.5), 0, "insert before")
        self.assertEqual(L.insert_index(2), 2)
        L.insert_at(2, 2)
        self.assertEqual(L.insert_index(1.5), 2)
        L.insert(1.5)
        self.assertEqual(L.insert_index(1.6), 3)
        L = table.SortedList()
        # make sure if we want to insert equal elements, the inserted index is before
        # if all elements are distincts before insertion
        for i in range(7):
            self.assertEqual(L.insert_index(i), i)
            L.append(i)

    def test_extend(self):
        L = table.SortedList()
        with self.assertRaises(table.SortError):
            L.extend([2,3,4])
        L.append(1)
        with self.assertRaises(table.SortError):
            L.extend(table.SortedList([0]))
        L.extend(table.SortedList([2,3,4]))
        with self.assertRaises(table.SortError):
            L.extend([3,5,7])
    
    def test_agendaDay(self):
        L = table.AgendaDay(1)
        self.assertEqual(L.label, "mardi")
        ts1 = am.TimeSpan(time(8), time(10), 1)
        ts2 = am.TimeSpan(time(10), time(10), 1)
        self.assertEqual(ts2.length, 0)
        L.insert(ts1)
        L.insert(ts2)
        self.assertEqual(L[0], ts1)
        self.assertEqual(L[1], ts2)
        self.assertEqual(len([_ for _ in L]), 1, "No empty span")
        self.assertEqual(len(list(L)), 1, "No empty span")

class TestTimeTables(WithWeeks):
    
    def test_compat_tt(self):
        # we want to test numbers of incompatibilities found
        # + stress test for performance check
        pevs = []
        attendance.AttComputer.changed_groups = True # clear cache
        # first create some users
        teachers = [
            um.User.objects.create_teacher(username=f"teach{i}", title="M.",
                first_name=f"{i}", last_name=f"{i}")
            for i in (1,2)
        ]
        for i in (1,2):
            um.User.objects.create_student(username=f"stud{i}", colle_group=i)
        # attendance all
        for d in range(5):
            ev = am.PeriodicEvent.objects.create(beghour=time(8+d), endhour=time(10+d),
                day=d, begweek=1, endweek=10, periodicity=2)
            ev.attendance_string = "all"
            ev2 = am.PeriodicEvent.objects.create(beghour=time(8+d), endhour=time(10+d),
                day=d, begweek=2, endweek=10, periodicity=2)
            ev2.attendance_string = "all"
            this_day = [ev, ev2]
            pevs.extend(this_day)
        for ev in pevs:
            self.assertEqual(len(ev.attendance_list), 2, "all = 2 groups")
        tt = table.CompatTimetable.construct(pevs, [], [])
        self.assertTrue(tt.compatible)
        for d in range(5):
            self.assertEqual(len(tt.periodics[d]), 2)
        # add incompatible periodics
        pev2 = []
        for d in range(5):
            ev = am.PeriodicEvent.objects.create(beghour=time(8), endhour=time(10),
                day=d, begweek=1, endweek=10, periodicity=1)
            ev.attendance_string = "all"
            pev2.append(ev)
        tt = table.CompatTimetable.construct(pevs + pev2, [], [])
        self.assertFalse(tt.compatible)
        self.assertEqual(len(tt.incomp), 2, "two first day")
        for d in range(5):
            self.assertEqual(len(tt.periodics[d]), 2 + int(d >= 2))
        # with some ColleEvents
        colle_evs = [am.ColleEvent.objects.create(
            teacher=teachers[0],
            beghour=time(10),
            endhour=time(11),
            day=1,
            subject="math"
        ),
        am.ColleEvent.objects.create(
            teacher=teachers[1],
            beghour=time(10),
            endhour=time(11),
            day=1,
            subject="math"
        )]
        groups = [um.ColleGroup.objects.get(nb=i) for i in (1,2)]
        cps = [
            am.CollePlanning.objects.create(
                event=colle_evs[i],
                week=self.weeks[0],
                group=groups[i]
            )
            for i in (0,1)
        ]
        tt = table.CompatTimetable.construct(pevs, cps, [])
        self.assertFalse(tt.compatible)
        self.assertEqual(len(tt.incomp), 2)
        tt = table.CompatTimetable.construct(pev2, cps, [])
        self.assertTrue(tt.compatible)
        colle_evs[1].teacher = teachers[0]
        cps[1].event = colle_evs[1]
        #del cps[1]._att # reset attendance_list cache
        tt = table.CompatTimetable.construct(pev2, cps, [])
        self.assertFalse(tt.compatible)

        # test attendance
        pev3 = []
        for d in range(5):
            ev = am.PeriodicEvent.objects.create(beghour=time(14), endhour=time(16),
                day=d, begweek=1, endweek=10, periodicity=2)
            ev.attendance_string = "1,M. 1"
            ev2 = am.PeriodicEvent.objects.create(beghour=time(14), endhour=time(16),
                day=d, begweek=2, endweek=10, periodicity=2)
            ev2.attendance_string = "2,M. 1"
            ev3 = am.PeriodicEvent.objects.create(beghour=time(14), endhour=time(15),
                day=d, begweek=2, endweek=10, periodicity=2)
            ev3.attendance_string = "1,M. 2"
            ev4 = am.PeriodicEvent.objects.create(beghour=time(14), endhour=time(15),
                day=d, begweek=1, endweek=10, periodicity=2)
            ev4.attendance_string = "2,M. 2"
            this_day = [ev, ev2, ev3, ev4]
            pev3.extend(this_day)
        tt = table.CompatTimetable.construct(pevs + pev3, [], [])
        
        self.assertTrue(tt.compatible)
        colle_evs = [am.ColleEvent.objects.create(
            teacher=teachers[0],
            beghour=time(16),
            endhour=time(17),
            day=1,
            subject="math"
        ),
        am.ColleEvent.objects.create(
            teacher=teachers[1],
            beghour=time(16),
            endhour=time(17),
            day=1,
            subject="math"
        ),
        am.ColleEvent.objects.create(
            teacher=teachers[0],
            beghour=time(15),
            endhour=time(16),
            day=2,
            subject="math"
        ),
        am.ColleEvent.objects.create(
            teacher=teachers[1],
            beghour=time(15),
            endhour=time(16),
            day=2,
            subject="math"
        )]
        cps = []
        for ev in colle_evs:
            cps.append(am.CollePlanning.objects.create(
                week=self.weeks[0],
                event=ev,
                group=groups[0])
            )
            cps.append(am.CollePlanning.objects.create(
                week=self.weeks[1],
                event=ev,
                group=groups[1])
            )
            cps.append(am.CollePlanning.objects.create(
                week=self.weeks[2],
                event=ev,
                group=groups[0])
            )
            cps.append(am.CollePlanning.objects.create(
                week=self.weeks[3],
                event=ev,
                group=groups[1])
            )
        tt = table.CompatTimetable.construct(pevs + pev3, cps, [])
        self.assertFalse(tt.compatible)
        self.assertEqual(len(tt.incomp), 12, "8 same group for teachers + 4 time")
        self.assertEqual(sum(len(d) for d in tt.periodics), len(pevs) + len(pev3) + 4)
        # add some base events on top of it
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        bev1 = am.BaseEvent.objects.create(
            begin=begin,
            end=begin + datetime.timedelta(0,60*60*2),
            label="",
            override=True
        )
        bev1.attendance_string = "all"
        bev2 = am.BaseEvent.objects.create(
            begin=begin+ datetime.timedelta(0,60*60),
            end=begin + datetime.timedelta(0,60*60*3),
            label=""
        )
        bev2.attendance_string = "all"
        bev3 = am.BaseEvent.objects.create(
            begin=begin+ datetime.timedelta(5),
            end=begin + datetime.timedelta(5,60*60*2),
            label="",
        )
        bev3.attendance_string = "all"
        bev4 = am.BaseEvent.objects.create(
            begin=begin+ datetime.timedelta(5,60*60),
            end=begin + datetime.timedelta(5,60*60*3),
            label=""
        )
        bev4.attendance_string = "all"
        # one incompatible base event
        self.assertEqual(bev2.week.nb, 1)
        self.assertFalse(bev2.compatible(pevs[0]))
        tt = table.CompatTimetable.construct(pevs, [], [bev2])
        self.assertFalse(tt.compatible)
        self.assertEqual(len(tt.incomp), 1)
        # all together
        tt = table.CompatTimetable.construct(pevs + pev3, cps, [bev1, bev2, bev3, bev4])
        self.assertFalse(tt.compatible)
        self.assertEqual(len(tt.incomp), 14, "same + one periodic incomp + 1 bev")
    
    def test_display_tt(self):
        ev1 = am.PeriodicEvent(begweek=0, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev1.save()
        for i in range(3):
            um.User.objects.create_student(username=str(i), colle_group=1)
        ev1.attendance_string = "1"
        tt = table.DisplayTimeTable([ev1])
        self.assertEqual(len(tt.days[0]), 1)
        # no override
        ts = am.TimeSpan(beghour=time(10), endhour=time(12), day=0)
        tt.add_span(ts)
        self.assertEqual(len(tt.days[0]), 2)
        teacher = um.User.objects.create_teacher(title="M.", last_name="moi", first_name="moi")
           
        self.assertTrue(attendance.AttComputer.changed_groups)
        cev = am.ColleEvent.objects.create(beghour=time(15), endhour=time(16),
            teacher=teacher, day=0, subject="Math")
        self.assertEqual(self.weeks[0].nb, 1)
        cp = am.CollePlanning.objects.create(
            event=cev, week=self.weeks[0],
            group= um.ColleGroup.objects.get(nb=1)
        )
        self.assertEqual(cp.colle_group, 1)
        tt.add_ev(cp)
        self.assertEqual(len(tt.days[0]), 3)
        tt.add_ev(cp)
        self.assertEqual(len(tt.days[0]), 3, "same span, just override")
        cev.beghour = time(8,30)
        cev.endhour = time(9,30)
        cp.event = cev
        tt.add_ev(cp)
        self.assertEqual(len(tt.days[0]), 4, "override one half")
        cev.beghour = time(15,30)
        cev.endhour = time(16,30)
        cp.event = cev
        tt.add_ev(cp)
        self.assertEqual(len(tt.days[0]), 5, "override one half")
        self.assertEqual(tt.days[0][-1].beghour, tt.days[0][-2].endhour)
        # test base events
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        bev1 = am.BaseEvent.objects.create(
            begin=begin + datetime.timedelta(1),  # monday
            end=begin + datetime.timedelta(1, 2*60*60),
            label="")
        tt.add_base_ev(bev1)
        self.assertEqual(len(tt.days[0]), 5, "no override")
        self.assertEqual(len(tt.days[1]), 1, "no override")
        bev2 = am.BaseEvent.objects.create(
            begin=begin,  # monday
            end=begin + datetime.timedelta(1, 1*60*60),
            label="")
        tt.add_base_ev(bev2)
        self.assertEqual(len(tt.days[0]), 1, "full override")
        self.assertEqual(len(tt.days[1]), 2, "half override")
        tt = table.DisplayTimeTable()
        tt.add_span(ev1.to_span())
        tt.add_base_ev(bev2)
        self.assertEqual(len(tt.days[0]), 1, "full override")
        self.assertEqual(tt.days[0][0].type, "base")
        self.assertEqual(len(tt.days[1]), 1, "new event")
        # full include
        bev3 = am.BaseEvent.objects.create(
            begin=begin + datetime.timedelta(1, 60*60),  # monday
            end=begin + datetime.timedelta(1, 90*60),
            label="")
        tt = table.DisplayTimeTable()
        tt.add_base_ev(bev3)
        self.assertEqual(len(tt.days[0]), 0, "tuesday")
        self.assertEqual(len(tt.days[1]), 1, "new event")
        tt.add_base_ev(bev1)
        self.assertEqual(len(tt.days[0]), 0, "tuesday")
        self.assertEqual(len(tt.days[1]), 1, "complete include")
    
    def test_current_day(self):
        tt = table.DisplayTimeTable()
        day = tt.get_current_day(self.monday, self.weeks[0])
        self.assertEqual(day, 0)
        day = tt.get_current_day(self.monday + datetime.timedelta(days=1), self.weeks[0])
        self.assertEqual(day, 1)
        day = tt.get_current_day(self.monday + datetime.timedelta(days=1), self.weeks[1])
        self.assertEqual(day, 0)
        day = tt.get_current_day(self.monday + datetime.timedelta(days=15), self.weeks[0])
        self.assertEqual(day, 4)
    
    def test_span(self):
        ev1 = am.PeriodicEvent(begweek=0, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev1.save()
        for i in range(3):
            um.User.objects.create_student(username=str(i), colle_group=1)
        ev1.attendance_string = "1"
        span = ev1.to_span()
        self.assertEqual(span.teachers, [])
        self.assertNotEqual(span.groups, "")
        self.assertEqual(span.beghour, time(8))
        self.assertEqual(span.endhour, time(10))
        self.assertEqual(span.day, 0)
        um.User.objects.create_teacher(title="M.", last_name="a", first_name="a")
        #ev1 = am.PeriodicEvent.objects.last()
        ev1.attendance_string = "1,M. a"
        span = ev1.to_span()
        self.assertNotEqual(span.teachers, [])
        self.assertNotEqual(span.groups, "")
    
    def test_ev_occurences(self):
        occ = am.EventOccurences(begweek=1, endweek=35, periodicity=1,
            groups="1-8", id=1)
        self.assertEqual(str(occ), "1-8")
        occ.periodicity = 2
        self.assertEqual(str(occ), "impaire 1-8")
        occ.begweek = 2
        self.assertEqual(str(occ), "paire 1-8")
    
    def test_mergeable(self):
        ev1 = am.PeriodicEvent(begweek=0, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev1.save()
        for i in range(3):
            um.User.objects.create_student(username=str(i), colle_group=i+1)
        ev1.attendance_string = "1"
        ev2 = am.PeriodicEvent(begweek=1, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev2.save()
        ev2.attendance_string = "2"
        ms1 = table.MergeableSpan.from_ev(ev1)
        ms2 = table.MergeableSpan.from_ev(ev2)
        self.assertTrue(ms1.is_similar(ms2))
        self.assertTrue(ms2.is_similar(ms1))
        self.assertEqual(len(ms1.occurences), 1)
        self.assertEqual(len(ms1.attendances()), 1)
        self.assertIn("paire", ms1.attendances()[0])
        self.assertIn("impaire", ms2.attendances()[0])
        ms1.merge(ms2)
        self.assertEqual(len(ms1.attendances()), 2)
        self.assertIn("paire", ms1.attendances()[1])
        self.assertIn("impaire", ms1.attendances()[0])
        um.User.objects.create_teacher(title="M.", last_name="a", first_name="a")
        ev1.attendance_string = "1,M. a"
        ms1 = table.MergeableSpan.from_ev(ev1)
        self.assertFalse(ms1.is_similar(ms2))
        self.assertFalse(ms2.is_similar(ms1))
        # test other periodicity
        ev1.periodicity = 1
        ms1 = table.MergeableSpan.from_ev(ev1)
        self.assertFalse(ms1.is_similar(ms2))
        self.assertEqual(len(ms1.attendances()), 0)
        ev1.periodicity = 3
        ms1 = table.MergeableSpan.from_ev(ev1)
        self.assertFalse(ms1.is_similar(ms2))
        att = ms1.attendances()
        self.assertEqual(len(att), 1)
        self.assertIn("C", att[0])
    
    def test_periodic_construction(self):
        for i in range(4):
            um.User.objects.create_student(username=str(i), colle_group=i+1)
        # same events on 3 weeks rotation
        triple = []
        for i in range(3):
            ev = am.PeriodicEvent.objects.create(begweek=i+1, endweek=35, subject="math",
                periodicity=3, day=0, beghour=time(8), endhour=time(10))
            ev.attendance_string = "1" if i % 2 else "2"
            triple.append(ev)
            ms = table.MergeableSpan.from_ev(ev)
            for j in range(i):
                msj = table.MergeableSpan.from_ev(triple[j])
                self.assertTrue(msj.is_similar(ms))
                self.assertTrue(ms.is_similar(msj))
        # 2 similar events, same time span as triple
        double = [
            am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="math",
                periodicity=2, day=0, beghour=time(8), endhour=time(10)),
            am.PeriodicEvent.objects.create(begweek=2, endweek=35, subject="math",
                periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ]
        double[0].attendance_string = "3"
        double[1].attendance_string = "4"
        tt = table.PeriodicConstruction([triple[0]])
        self.assertEqual(len(tt.days[0]), 1)
        tt.add_ev(double[0])
        self.assertEqual(len(tt.days[0]), 2)
        tt.add_ev(triple[1])
        self.assertEqual(len(tt.days[0]), 2)
        tt.add_ev(double[1])
        self.assertEqual(len(tt.days[0]), 2)
        tt.add_ev(triple[2])
        self.assertEqual(len(tt.days[0]), 2)
        for i in range(2):
            self.assertEqual(len(tt.days[0][i].occurences), tt.days[0][i].periodicity)
    
    def test_overlap_hours(self):
        ev1 = am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        ev2 = am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="physique",
            periodicity=2, day=0, beghour=time(8), endhour=time(10))
        tt = table.PeriodicConstruction([ev1, ev2]) # overlaping
        self.assertEqual(len(tt.days[0]), 2)
        tt.update_overlaps()
        for i in range(2):
            self.assertEqual(tt.days[0][i].overlap_nb, 2)
            self.assertEqual(tt.days[0][i].position, i)
        ev3 = am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(9,30), endhour=time(11,30))
        ev4 = am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="math",
            periodicity=2, day=0, beghour=time(10,30), endhour=time(12, 30))
        tt.add_evs([ev3, ev4])
        self.assertEqual(len(tt.days[0]), 4, "not similar")
        tt.update_overlaps()
        for i in range(3):
            with self.subTest(i=i):
                self.assertEqual(tt.days[0][i].overlap_nb, 3)
                self.assertEqual(tt.days[0][i].position, i)
        self.assertEqual(tt.days[0][3].position, 0)
        self.assertEqual(tt.days[0][3].overlap_nb, 3)
        # test get_hours
        hours = tt.get_hours()
        for h in range(9, 13):
            self.assertIn(time(h, 30), hours)


class TestInscription(WithWeeks, CreateUserMixin):


    def test_locked(self):
        self.create_users()
        inst = am.InscriptionEvent.objects.create(
            begin=timezone.now(),
            end=timezone.now() + datetime.timedelta(0, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2
        )
        self.assertTrue(inst.locked())
        inst.end = timezone.now() + datetime.timedelta(days=2, hours=2)
        inst.begin = timezone.now() + datetime.timedelta(days=2)
        inst.save()
        self.assertFalse(inst.locked())
        inst.begin = timezone.now() + datetime.timedelta(days=1, minutes=1)
        inst.save()
        self.assertFalse(inst.locked())
        inst.begin = timezone.now() + datetime.timedelta(hours=23)
        inst.save()
        self.assertTrue(inst.locked())
    
    def test_manager(self):
        self.create_users()
        am.InscriptionEvent.objects.create(
            begin=timezone.now()+ datetime.timedelta(0, 60*60*1),
            end=timezone.now() + datetime.timedelta(0, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2
        )
        self.assertEqual(am.InscriptionEvent.objects.open().count(), 1)
        am.InscriptionEvent.objects.create(
            begin=timezone.now() - datetime.timedelta(0, 60*60*1),
            end=timezone.now() + datetime.timedelta(0, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2
        )
        self.assertEqual(am.InscriptionEvent.objects.open().count(), 1)
        self.assertEqual(am.InscriptionEvent.objects.closed().count(), 1)
    
    def test_for_week(self):
        self.create_users()
        begin = timezone.make_aware(datetime.datetime.combine(self.monday, time(8)))
        am.InscriptionEvent.objects.create(
            begin=begin + datetime.timedelta(0, 60*60*1),
            end=begin + datetime.timedelta(0, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2
        )
        self.assertEqual(am.InscriptionEvent.objects.for_week(self.weeks[0]).count(), 1)
        am.InscriptionEvent.objects.create(
            begin=begin + datetime.timedelta(7, 60*60*1),
            end=begin + datetime.timedelta(7, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2
        )
        self.assertEqual(am.InscriptionEvent.objects.for_week(self.weeks[0]).count(), 1)
    
    def test_user_attend(self):
        self.create_users()
        self.create_students()
        am.InscriptionEvent.objects.create(
            begin=timezone.now()+ datetime.timedelta(0, 60*60*1),
            end=timezone.now() + datetime.timedelta(0, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2
        )
        self.assertEqual(am.InscriptionEvent.objects.user_attend(self.staff_user).count(), 1)
        self.assertEqual(am.InscriptionEvent.objects.user_attend(self.students[0]).count(), 0)
        inscr = am.InscriptionEvent.objects.create(
            begin=timezone.now() - datetime.timedelta(0, 60*60*1),
            end=timezone.now() + datetime.timedelta(0, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2
        )
        self.assertEqual(am.InscriptionEvent.objects.user_attend(self.staff_user).count(), 2)
        self.assertEqual(am.InscriptionEvent.objects.user_attend(self.students[0]).count(), 0)
        inscr.attendants.add(self.students[0])
        self.assertEqual(am.InscriptionEvent.objects.user_attend(self.staff_user).count(), 2)
        self.assertEqual(am.InscriptionEvent.objects.user_attend(self.students[0]).count(), 1)
    
    def test_manager_compat(self):
        self.create_users()
        self.create_students()
        self.staff_user.teacher = True
        am.InscriptionEvent.objects.create(
            begin=timezone.now()+ datetime.timedelta(0, 60*60*1),
            end=timezone.now() + datetime.timedelta(0, 60*60*2),
            label="",
            teacher=self.staff_user,
            max_students=2,
            is_full=True
        )
        self.assertEqual(am.InscriptionEvent.objects.open().count(), 1)
        self.assertEqual(am.InscriptionEvent.objects.closed().count(), 0)
        # self.assertEqual(am.InscriptionEvent.objects.open(self.students[0]).count(), 0)
        # self.assertEqual(am.InscriptionEvent.objects.closed(self.students[0]).count(), 1)
        import random
        # test all Inscription can be retrieved by excactly one custom method
        for _ in range(10):
            am.InscriptionEvent.objects.create(
                begin=timezone.now()+ datetime.timedelta(0, 60*60*(2*random.randint(0, 1) - 1)),
                end=timezone.now() + datetime.timedelta(0, 60*60*2),
                label="",
                teacher=self.staff_user,
                max_students=2,
                is_full=bool(random.randint(0,1))
            )
            self.assertEqual(
                am.InscriptionEvent.objects.open().count() +
                    am.InscriptionEvent.objects.closed().count(),
                am.InscriptionEvent.objects.all().count()
            )
            self.assertEqual(
                am.InscriptionEvent.objects.open().count() +
                    am.InscriptionEvent.objects.closed().count(),
                am.InscriptionEvent.objects.all().count()
            )