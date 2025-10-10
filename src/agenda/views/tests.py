"""
date: 2024-03-02
"""
import datetime
from pathlib import Path

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone

from dev.test_utils import TestCase
from dev import test_view, test_data

import agenda.models as am
from agenda.forms.tests import create_subjects
import users.models as um

class TestYear(TestCase, test_data.CreateUserMixin):

    def setUp(self):
        # create 2 users : self.staff_user and self.user
        self.create_users()

    def test_access(self):
        url = test_view.TestURL(self, "agenda", "weeks", status=403)
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()
    
    def test_week_creation(self):
        url = test_view.TestURL(self, "agenda", "weeks", user=self.staff_user)
        url.test()
        url.method = "post"
        url.data = {
            "begin": datetime.date.today(),
            "end": datetime.date.today() + datetime.timedelta(20),
            "make_default": False
        }
        url.status = 302
        resp = url.test()
        self.assertEqual(resp.url, url.url)
        prev_count = am.Week.objects.count()
        self.assertTrue(prev_count > 0)
        self.assertTrue(am.Week.objects.active().count() == 0)
        url.data = {
            "begin": datetime.date.today()+ datetime.timedelta(28),
            "end": datetime.date.today() + datetime.timedelta(41),
            "make_default": True
        }
        resp = url.test()
        self.assertTrue(am.Week.objects.active().count() > 0)
        self.assertTrue(am.Week.objects.active().count() == am.Week.objects.count() - prev_count)
    
    def test_week_manage(self):
        url = test_view.JsonURL(self, "agenda", "weeks_update", status=403, method="post")
        url.test(forbidden=True)
        url.set_user(self.staff_user)
        url.status = 403
        url.msg = "Testing no json data"
        url.test()
        url.data = []
        url.msg = "Empty list"
        url.status = 200
        url.test(content_type="application/json")
        # test actual update
        gen = am.HolidayGenerator()
        today = datetime.date.today()
        today = datetime.date(today.year, 12, 25) # we're in holiday
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        end = today + datetime.timedelta(10)
        week1, week2 = gen.generate_between(today, end, True)
        url.data = [
            {"id": week1.id, "label": "week1", "nb": 4}
        ]
        url.test(content_type="application/json")
        week1 = am.Week.objects.get(id=week1.id)
        self.assertEqual(week1.label, "week1")
        self.assertEqual(week1.nb, 4)
        url.data = [
            {"id": week1.id + week2.id, "label": "week1", "nb": 4}
        ]
        url.status = 403 # update error
        url.msg = "No such week"
        url.test(content_type="application/json")
    
    def test_home(self):
        url = test_view.TestURL(self, "agenda", "index", status=403)
        url.test()
        url.set_user(self.users[0])
        url.status = 403
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()

class UsersAndWeeks(test_data.CreateUserMixin):

    def create_weeks(self):
        today = datetime.date.today()
        # make today a monday
        today = today + datetime.timedelta(-today.weekday())
        end = today + datetime.timedelta(50)
        self.monday = today
        self.weeks = []
        begin = today
        nb = 1
        while begin < end:
            week, _ = am.Week.objects.get_or_create(
                begin=begin, end=begin + datetime.timedelta(6),
                nb=nb, active=True)
            self.weeks.append(week)
            begin = week.end + datetime.timedelta(1)

class TestApi(TestCase, UsersAndWeeks):

    def setUp(self) -> None:
        self.create_users(2)
        return super().setUp()
    
    def test_week_api(self):
        url = test_view.TestURL(self, "agenda:api", "week_api-list", status=403)
        url.test()
        url.set_user(self.users[0])
        url.status = 200
        url.test()
        self.create_weeks()
        url.test()
        url.status = 200
        body = url.test().json()
        self.assertEqual(len(body), len(self.weeks))
        url.set_url("agenda:api", "week_api-detail", kwargs={"pk": self.weeks[0].pk})
        url.test()
        body = url.test().json()
        self.assertIn("label", body)
        self.assertIn("nb", body)
    
    def test_tt_access(self):
        url = test_view.JsonURL(self, "agenda", "user_timetable",
            kwargs={"week": 0})
        #login required
        url.status = 403
        url.test(forbidden=True)
        url.set_user(self.users[0])
        # no week
        url.status = 404 # or all except 200 here
        url.test()
        # create some weeks
        self.create_weeks()
        # still no week with pk 0
        url.test()
        url.status = 200
        url.set_url("agenda", "user_timetable", kwargs={"week": self.weeks[0].pk})
        url.test() # check access
        body = url.test().json() # if access is ok, we should get a json response
        self.assertIn("html", body)
        #self.assertIn("adj", body["week"])
        self.assertNotIn("Semaine précédente", body["html"])
        self.assertIn("Semaine suivante", body["html"])
        url.set_url("agenda", "user_timetable", kwargs={"week": self.weeks[1].pk})
        url.test() # check access
        body = url.test().json() # if access is ok, we should get a json response
        self.assertIn("html", body)
        self.assertIn("Semaine précédente", body["html"])
        self.assertIn("Semaine suivante", body["html"])
    
    def test_tt_error(self):
        self.create_weeks()
        url = test_view.JsonURL(self, "agenda", "user_timetable",
            kwargs={"week": self.weeks[0].pk})
        url.set_user(self.users[0])
        url.test()
        sunday = self.monday + datetime.timedelta(days=6)
        begin = datetime.datetime.combine(sunday, datetime.time(8))
        begin = timezone.make_aware(begin)
        end = begin + datetime.timedelta(hours=2)
        ev = am.BaseEvent.objects.create(
            label="test",
            begin=begin,
            end=end,
            classroom="A",
        )
        ev.attendants.add(self.users[0])
        url.status = 403 # json error
        with self.assertLogs(level="ERROR"):
            url.test()
    
    def test_tt_events(self):
        self.create_weeks()
        week = self.weeks[1]
        url = test_view.JsonURL(self, "agenda", "user_timetable",
            kwargs={"week": week.pk})
        url.set_user(self.users[0])
        resp = url.test()
        self.assertIn("agenda", resp.context)
        self.assertEqual(sum(len(d) for d in resp.context["agenda"].days), 0)
        # create some events
        beghour = datetime.datetime.combine(week.begin, datetime.time(8))
        beghour = timezone.make_aware(beghour)
        endhour = datetime.datetime.combine(week.begin, datetime.time(10))
        endhour = timezone.make_aware(endhour)
        ev = am.BaseEvent.objects.create(
            label="test base",
            begin=beghour,
            end=endhour,
            classroom="A",
        )
        resp = url.test()
        self.assertEqual(sum(len(d) for d in resp.context["agenda"].days), 0)
        url.data = {"all": "true"} # all events, just for staff users
        resp = url.test()
        self.assertEqual(sum(len(d) for d in resp.context["agenda"].days), 0)
        ev.attendants.add(self.users[0])
        resp = url.test()
        self.assertEqual(sum(len(d) for d in resp.context["agenda"].days), 1)
        url.set_user(self.staff_user)
        resp = url.test()
        self.assertEqual(sum(len(d) for d in resp.context["agenda"].days), 1)
        am.InscriptionEvent.objects.create(
            label="test inscription",
            begin=ev.begin + datetime.timedelta(hours=1),
            end=ev.end + datetime.timedelta(hours=1),
            max_students=2,
            teacher=self.staff_user,
        )
        qs = am.InscriptionEvent.objects.for_week(week).open()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.user_attend(self.staff_user).count(), 1)
        inscription = qs.first()
        self.assertEqual(len(inscription.to_span()), 1)
        resp = url.test()
        self.assertEqual(sum(len(d) for d in resp.context["agenda"].days), 2)
        url.set_user(self.users[0])
        resp = url.test()
        self.assertEqual(sum(len(d) for d in resp.context["agenda"].days), 1)
    
    def test_user_select(self):
        self.create_weeks()
        # still no week with pk 0
        url = test_view.JsonURL(self, "agenda", "user_timetable",
            kwargs={"week": self.weeks[0].pk})
        url.set_user(self.users[0])
        url.test() # check access
        url.set_url("agenda", "user_timetable",
            kwargs={"week": self.weeks[0].pk, "user_id": self.users[1].pk})
        resp = url.test()
        ctx = resp.context
        self.assertIn("curr_user", ctx)
        self.assertEqual(ctx["curr_user"].pk, self.users[0].pk, "no change")
        self.create_teachers(TEACHERS)
        url.set_user(self.teachers[0])
        resp = url.test()
        ctx = resp.context
        self.assertIn("curr_user", ctx)
        self.assertEqual(ctx["curr_user"].pk, self.users[1].pk, "change")
        url.set_user(self.staff_user)
        resp = url.test()
        ctx = resp.context
        self.assertIn("curr_user", ctx)
        self.assertEqual(ctx["curr_user"].pk, self.users[1].pk, "change")
    
    def test_timeline_access(self):
        url = test_view.JsonURL(self, "agenda", "timeline", status=403)
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.status = 200
        url.test()
        today = datetime.date.today() + datetime.timedelta(1)
        todo = am.ToDo.objects.create(date=today, label="test")
        resp = url.test()
        self.assertIn("timeline", resp.context)
        self.assertEqual(len(resp.context["timeline"]), 0)
        todo.attendants.add(self.users[0])
        resp = url.test()
        self.assertIn("timeline", resp.context)
        self.assertEqual(len(resp.context["timeline"]), 1)
    
    def test_timeline_render(self):
        url = test_view.JsonURL(self, "agenda", "timeline", status=200)
        url.set_user(self.users[0])
        today = datetime.date.today() + datetime.timedelta(1)
        todo = am.ToDo.objects.create(date=today, label="test")
        todo.attendants.add(self.users[0])
        # add an inscription event
        begin = datetime.datetime.combine(today, datetime.time(8))
        begin = timezone.make_aware(begin)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=begin,
            end=begin + datetime.timedelta(minutes=60),
            teacher=self.staff_user,
            max_students=1)
        inst.attendants.add(self.users[0])
        resp = url.test()
        self.assertIn("timeline", resp.context)
        self.assertEqual(sum(len(v["objects"]) for v in resp.context["timeline"]), 2)
        # others two event types are week-dependant....
        #add a Note
        week = am.Week.objects.create(
            begin=today, 
            end=today + datetime.timedelta(days=7), 
            label="test week", 
            nb=1
        )
        ev1 = am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="math",
            periodicity=2, day=0, beghour=datetime.time(8), endhour=datetime.time(10))
        ev1.attendants.add(self.users[0])
        am.Note.objects.create(target_week=week, comment="test",
            target_event=ev1, date=today)
        # add an Exam
        # import content.models as cm
        # cm.DevoirPublication.objects.create(title="DS 1", date=datetime.date.today())
        # resp = url.test()
        # self.assertIn("timeline", resp.context)
        # self.assertEqual(sum(len(v["objects"]) for v in resp.context["timeline"]), 4)
        # check all timeline events have template
        for month in resp.context["timeline"]:
            for ev in month["objects"]:
                self.assertTrue(hasattr(ev, "timeline_template"),
                    f"Event {ev} has no timeline template")
    
    def test_note_create(self):
        url = test_view.JsonURL(self, "agenda", "note_create", status=403)
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.test(forbidden=True)
        self.create_weeks()
        ev1 = am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="math",
            periodicity=2, day=0, beghour=datetime.time(8), endhour=datetime.time(10))
        url.set_user(self.staff_user)
        url.status = 200
        url.method = "post"
        url.data = {
            "target_week": self.weeks[0].pk,
            "target_event": ev1.pk,
            "comment": "test"
        }
        url.test()
        self.assertEqual(am.Note.objects.count(), 1)
    
    def test_note_details(self):
        self.create_weeks()
        ev1 = am.PeriodicEvent.objects.create(begweek=1, endweek=35, subject="math",
            periodicity=2, day=0, beghour=datetime.time(8), endhour=datetime.time(10))
        url = test_view.JsonURL(self, "agenda", "note_detail", status=403,
            kwargs={"event": ev1.pk, "week": self.weeks[0].pk})
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.status = 200
        resp = url.test()
        self.assertIn("notes", resp.context)
        self.assertEqual(len(resp.context["notes"]), 0)
        am.Note.objects.create(target_week=self.weeks[0], comment="test",
            target_event=ev1)
        am.Note.objects.create(target_week=self.weeks[0], comment="test2",
            target_event=ev1)
        resp = url.test()
        self.assertIn("notes", resp.context)
        self.assertEqual(len(resp.context["notes"]), 2)
        data = resp.json()
        self.assertTrue("html" in data)

    def test_check_agenda(self):
        # populate periodic events, code from test_import_view
        url = test_view.TestURL(
            self,
            "import",
            "edt",
            method="post",
            user=self.staff_user
        )
        self.create_teachers(TEACHERS)
        fpath = Path(__file__).parent / ".." / "fixtures" / "edt.json"
        self.assertTrue(fpath.exists())
        level = um.get_default_level(instance=True)
        with open(fpath, "rb") as upl_file:
            url.data = {
                "_encoding": "utf8",
                "_name_mapping_9": "attendance",
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "edt.json",
                    "text/plain", fpath.stat().st_size, "utf-8"
                ),
                "level": level.pk
            }
            create_subjects(level)
            # redirect
            url.test(follow=True)
            self.assertTrue(am.PeriodicEvent.objects.count() > 0)
        # check agenda
        level = um.get_default_level(instance=True)
        url = test_view.JsonURL(self, "agenda", "check_agenda", status=403,
            kwargs={"level_id": level.pk})
        url.test(forbidden=True)
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertIn("agenda", resp.context)
        self.assertTrue(resp.context["agenda"].compatible)

TEACHERS = test_data.TEACHERS

class TestEventManage(TestCase, UsersAndWeeks):

    def setUp(self) -> None:
        self.create_users()
        return super().setUp()

    def test_periodic_access(self):
        url = test_view.TestURL(self, "agenda", "manage_periodic", status=403)
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        ctx = resp.context
        self.assertIn("form", ctx)
        self.assertIn("empty_form", ctx)
        self.assertIn("agenda", ctx)

    def test_periodic_creation(self):
        url = test_view.JsonURL(self, "agenda", "manage_periodic", status=403)
        url.method = "post"
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.test(forbidden=True)
        url.set_user(self.staff_user)
        # form invalid
        url.test()
        url.status = 200
        self.create_students(3)
        level = um.get_default_level(instance=True)
        subjects = create_subjects(level)
        url.data = test_data.create_formset_data(
            [{
                "begweek": 1,
                "endweek": 25,
                "beghour": "8:0",
                "endhour": "10:0",
                "periodicity": 1,
                "label": "cours",
                "subj": subjects[0].pk,
                "day": 0,
                "_attendance_string": "all"
            },
            {
                "begweek": 1,
                "endweek": 25,
                "beghour": "10:0",
                "endhour": "12:0",
                "periodicity": 1,
                "label": "cours",
                "subj": subjects[1].pk,
                "day": 0,
                "_attendance_string": "all"
            }],
            total_form=2,
            prefix="periodic"
        )
        resp = url.test()
        resp_data = resp.json()
        self.assertIn("instances", resp_data)
        self.assertEqual(len(resp_data["instances"]), 2)
        self.assertIn("timetable", resp_data)
        self.assertEqual(am.PeriodicEvent.objects.count(), 2)
        # check access with some events
        url = test_view.TestURL(self, "agenda", "manage_periodic", status=403)
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()
    
    def test_periodic_update(self):
        url = test_view.JsonURL(self, "agenda", "manage_periodic", status=403)
        url.method = "post"
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.test(forbidden=True)
        url.set_user(self.staff_user)
        self.assertEqual(am.PeriodicEvent.objects.count(), 0)
        level = um.get_default_level(instance=True)
        subjects = create_subjects(level)
        ev = am.PeriodicEvent.objects.create(
            beghour=datetime.time(8),
            endhour=datetime.time(10),
            day=0,
            label="cours",
            subj=subjects[0],
            begweek=1,
            endweek=10,
            periodicity=1
        )
        url.set_url("agenda", "manage_periodic")
        #url.status = ERROR, form_invalid
        resp = url.test()
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Invalid Form")
        url.data = test_data.create_formset_data(
            [
            {
                "id": ev.pk,
                "begweek": 1,
                "endweek": 25,
                "beghour": "10:0",
                "endhour": "12:0",
                "periodicity": 1,
                "label": "cours",
                "subj": subjects[1].pk,
                "day": 0,
                "_attendance_string": "all"
            }],
            total_form=1,
            initial_form=1,
            prefix="periodic"
        )
        url.status = 200
        resp = url.test()
        ev.refresh_from_db()
        self.assertEqual(ev.endweek, 25)
        url.set_url("agenda", "manage_periodic")
        url.test()
    
    def test_periodic_delete(self):
        url = test_view.JsonURL(self, "agenda", "delete_periodic", status=403)
        url.method = "post"
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.test(forbidden=True)
        url.set_user(self.staff_user)
        self.assertEqual(am.PeriodicEvent.objects.count(), 0)
        ev = am.PeriodicEvent.objects.create(
            beghour=datetime.time(8),
            endhour=datetime.time(10),
            day=0,
            label="cours",
            subject="math",
            begweek=1,
            endweek=10,
            periodicity=1
        )
        url.data = {"ids": ev.pk}
        url.status = 200
        url.test()
        self.assertEqual(am.PeriodicEvent.objects.count(), 0)
        evs = [am.PeriodicEvent.objects.create(
            beghour=datetime.time(8),
            endhour=datetime.time(10),
            day=i,
            label="cours",
            subject="math",
            begweek=1,
            endweek=10,
            periodicity=1
        ) for i in range(5)]
        url.data = {"ids": ",".join([str(ev.pk) for ev in evs])}
        resp = url.test()
        data = resp.json()
        self.assertIn("deleted", data)
        self.assertEqual(data["deleted"], 5)
        self.assertEqual(am.PeriodicEvent.objects.count(), 0)
    
    def test_delete_periodic_erros(self):
        url = test_view.JsonURL(self, "agenda", "delete_periodic", status=403)
        url.method = "post"
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.test(forbidden=True)
        url.set_user(self.staff_user)
        self.assertEqual(am.PeriodicEvent.objects.count(), 0)
        am.PeriodicEvent.objects.create(
            beghour=datetime.time(8),
            endhour=datetime.time(10),
            day=0,
            label="cours",
            subject="math",
            begweek=1,
            endweek=10,
            periodicity=1
        )
        url.data = {"ids": ""}
        url.status = 200
        url.test()
        self.assertEqual(am.PeriodicEvent.objects.count(), 1)
        url.data = {"ids": "notanumber"}
        url.status = 401 # fake code, json error
        url.test()
    
    def test_import_view(self):
        # provide testing for bulkimport.views
        url = test_view.TestURL(
            self,
            "import",
            "edt",
            method="post",
            status=403
        )
        url.test()
        url.set_user(self.users[0])
        url.test(forbidden=True)
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertFalse(resp.context["form"].is_valid())
        #same code as in forms.tests
        self.create_teachers(TEACHERS)
        fpath = Path(__file__).parent / ".." / "fixtures" / "edt.json"
        self.assertTrue(fpath.exists())
        level = um.get_default_level(instance=True)
        with open(fpath, "rb") as upl_file:
            url.data = {
                "_encoding": "utf8",
                "_name_mapping_9": "attendance",
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "edt.json",
                    "text/plain", fpath.stat().st_size, "utf-8"
                ),
                "level": level.pk
            }
            create_subjects(level)
            # redirect
            resp = url.test(follow=True)
            self.assertTrue(am.PeriodicEvent.objects.count() > 0)
    
    def test_export_tt(self):
        level = um.get_default_level(instance=True)
        url = test_view.TestURL(self, "agenda", "export_timetable", status=403,
            kwargs={"level_id": level.pk})
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        resp.json()
        #same code as in forms.tests
        url2 = test_view.TestURL(
            self,
            "import",
            "edt",
            method="post",
            status=403
        )
        url2.set_user(self.users[0])
        url2.test()
        url2.set_user(self.staff_user)
        url2.status = 200
        url2.set_user(self.staff_user)
        self.create_teachers(TEACHERS)
        fpath = Path(__file__).parent / ".." / "fixtures" / "edt.json"
        self.assertTrue(fpath.exists())
        level = um.get_default_level(instance=True)
        with open(fpath, "rb") as upl_file:
            url2.data = {
                "_encoding": "utf8",
                "_name_mapping_9": "attendance",
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "edt.json",
                    "text/plain", fpath.stat().st_size, "utf-8"
                ),
                "level": level.pk
            }
            create_subjects(level)
            # redirect
            resp = url2.test(follow=True)
            self.assertTrue(am.PeriodicEvent.objects.count() > 0)
        resp = url.test()
        data = resp.json()
        self.assertEqual(len(data), am.PeriodicEvent.objects.count())
    
    def test_import_ds(self):
        url = test_view.TestURL(
            self,
            "import",
            "ds",
            method="post",
            status=403
        )
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertFalse(resp.context["form"].is_valid())
        fpath = Path(__file__).parent / ".." / "fixtures" / "ds-pt.csv"
        self.assertTrue(fpath.exists())
        #create weeks for these events
        gen = am.HolidayGenerator()
        begin = datetime.date(2024, 9, 2) # see fixtures/ds-pt.csv
        end = datetime.date(2025, 4, 1)
        gen.generate_between(begin, end, active=True)
        with open(fpath, "rb") as upl_file:
            url.data = {
                "_encoding": "utf8",
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "ds-pt.csv",
                    "text/plain", fpath.stat().st_size, "utf-8"
                )
            }
            # redirect
            resp = url.test(follow=True)
    
    def test_standalone_tt(self):
        self.create_weeks()
        url = test_view.TestURL(self, "agenda", "personal_timetable", status=403,
            tests=[test_view.CheckNs("urls", "week", "urls.initialTt")])
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()
    
    def test_manage_base_events(self):
        url = test_view.TestURL(self, "agenda", "manage_events", status=403)
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertIn("form", resp.context)
        self.create_weeks()
        url.data = {
            "week": self.weeks[0].pk,
        }
        resp = url.test()
        self.assertIn("week", resp.context)
        self.assertEqual(resp.context["week"].pk, self.weeks[0].pk)
    
    def test_update_base_events(self):
        self.create_weeks()
        beghour = datetime.datetime.combine(self.weeks[0].begin, datetime.time(8))
        beghour = timezone.make_aware(beghour)
        endhour = datetime.datetime.combine(self.weeks[0].begin, datetime.time(10))
        endhour = timezone.make_aware(endhour)
        ev = am.BaseEvent.objects.create(
            label="test",
            begin=beghour,
            end=endhour,
            classroom="A",
        )
        url = test_view.TestURL(self, "agenda", "manage_events", status=403,
            kwargs={"pk": ev.pk})
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertIn("form", resp.context)
        url.data = {
            "label": "test",
            "begin": beghour,
            "end": endhour,
            "classroom": "B",
        }
        url.method = "post"
        url.status = 302
        url.test()
        ev.refresh_from_db()
        self.assertEqual(ev.classroom, "B")

    def test_create_base_events(self):
        self.create_weeks()
        beghour = datetime.datetime.combine(self.weeks[0].begin, datetime.time(8))
        beghour = timezone.make_aware(beghour)
        endhour = datetime.datetime.combine(self.weeks[0].begin, datetime.time(10))
        endhour = timezone.make_aware(endhour)
        url = test_view.TestURL(self, "agenda", "manage_events", status=403)
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertIn("form", resp.context)
        url.data = {
            "label": "test",
            "begin": beghour,
            "end": endhour,
            "classroom": "A",
            "week": self.weeks[0].pk
        }
        url.method = "post"
        url.status = 302
        resp = url.test()
        self.assertEqual(am.BaseEvent.objects.count(), 1)
    
    def test_delete_base_events(self):
        self.create_weeks()
        beghour = datetime.datetime.combine(self.weeks[0].begin, datetime.time(8))
        beghour = timezone.make_aware(beghour)
        endhour = datetime.datetime.combine(self.weeks[0].begin, datetime.time(10))
        endhour = timezone.make_aware(endhour)
        ev = am.BaseEvent.objects.create(
            label="test",
            begin=beghour,
            end=endhour,
            classroom="A",
        )
        url = test_view.TestURL(self, "agenda", "delete_event", status=403,
            kwargs={"pk": ev.pk})
        url.method = "post"
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.set_user(self.staff_user)
        url.status = 405
        url.method = "get"
        url.test()
        url.method = "post"
        url.status = 302
        self.assertEqual(am.BaseEvent.objects.count(), 1)
        url.test()
        self.assertEqual(am.BaseEvent.objects.count(), 0)


class TestInscription(TestCase, test_data.CreateUserMixin):

    def test_inscription(self):
        self.create_users(3)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=timezone.now(),
            end=timezone.now() + datetime.timedelta(10),
            teacher=self.staff_user,
            max_students=2
        )
        url = test_view.JsonURL(self, "agenda", "inscription:add", status=403,
            kwargs={"pk": inst.pk})
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.status = 405
        url.test(forbidden=True)
        url.method = "post"
        url.status = 200
        resp = url.test()
        self.assertEqual(inst.attendants.count(), 1)
        url.status = 403 # fake status, we expect an error
        url.test() # idempotence
        self.assertEqual(inst.attendants.count(), 1)
        url.set_user(self.users[1])
        url.status = 200
        url.test()
        self.assertEqual(inst.attendants.count(), 2)
        url.set_user(self.users[2])
        url.status = 403
        url.test()
        self.assertEqual(inst.attendants.count(), 2)
    
    def test_cancel_inscription(self):
        self.create_users(2)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=timezone.now(),
            end=timezone.now() + datetime.timedelta(10),
            teacher=self.staff_user,
            max_students=2
        )
        inst.attendants.set(self.users)
        url = test_view.JsonURL(self, "agenda", "inscription:cancel", status=403,
            kwargs={"pk": inst.pk})
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.status = 405
        url.test(forbidden=True)
        url.method = "post"
        url.status = 403 # locked event
        url.test()
        self.assertEqual(inst.attendants.count(), 2)
        inst.begin = timezone.now() + datetime.timedelta(days=1, hours=1)
        inst.save()
        url.status = 200
        url.test()
        self.assertEqual(inst.attendants.count(), 1)
        url.status = 403
        url.test() # already canceled
    
    def test_manage_inscriptions(self):
        self.create_users(3)
        url = test_view.TestURL(self, "agenda", "inscription:manage", status=403)
        url.test()
        url.set_user(self.users[0])
        url.test()
        self.staff_user.teacher = True
        self.staff_user.is_staff = False
        self.staff_user.save()
        self.staff_user.refresh_from_db()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertIn("inscriptions", resp.context)
        self.assertEqual(len(resp.context["inscriptions"]), 0)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=timezone.now(),
            end=timezone.now() + datetime.timedelta(10),
            teacher=self.staff_user,
            max_students=2
        )
        inst.attendants.set(self.users)
        url.status = 200
        resp = url.test()
        self.assertEqual(len(resp.context["inscriptions"]), 1)
        url.method = "post"
        self.create_teachers(TEACHERS)
        url.data = {
            "teacher": self.teachers[0].pk,
            "begin": timezone.now(),
            "end": timezone.now() + datetime.timedelta(10),
            "max_students": 2,
            "label": "test",
            "classroom": "A",
            "attendants": [self.users[0].pk, self.users[1].pk]
        }
        url.status = 302
        resp = url.test()
        #print(resp.context["form"].errors)
        self.assertEqual(am.InscriptionEvent.objects.count(), 2)
        self.assertEqual(am.InscriptionEvent.objects.last().attendants.count(), 2)
        # check that teacher have been set to self.staff_user
        self.assertEqual(am.InscriptionEvent.objects.last().teacher, self.staff_user)
        self.staff_user.is_staff = True
        self.staff_user.save()
        self.staff_user.refresh_from_db()
        url.set_user(self.staff_user)
        url.test()
        self.assertEqual(am.InscriptionEvent.objects.count(), 3)
        self.assertEqual(am.InscriptionEvent.objects.last().attendants.count(), 2)
        # check that teacher have been honored
        self.assertEqual(am.InscriptionEvent.objects.last().teacher, self.teachers[0])
    
    def test_inscription_list(self):
        self.create_users(3)
        url = test_view.TestURL(self, "agenda", "inscription:list", status=403)
        url.test()
        url.set_user(self.users[0])
        url.status = 200
        resp = url.test()
        self.assertIn("object_list", resp.context)
        self.assertEqual(len(resp.context["object_list"]), 0)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=timezone.now() + datetime.timedelta(10),
            end=timezone.now() + datetime.timedelta(10),
            teacher=self.staff_user,
            max_students=2
        )
        inst.attendants.set(self.users)
        url.status = 200
        resp = url.test()
        self.assertEqual(am.InscriptionEvent.objects.count(), 1)
        self.assertEqual(len(resp.context["inscriptions"]), 1)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=timezone.now() - datetime.timedelta(10),
            end=timezone.now() + datetime.timedelta(10),
            teacher=self.staff_user,
            max_students=2
        )
        resp = url.test()
        self.assertEqual(am.InscriptionEvent.objects.count(), 2)
        self.assertEqual(len(resp.context["inscriptions"]), 1)
        url = test_view.JsonURL(self, "agenda", "inscription:list_passed", status=403)
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.status = 200
        resp = url.test()
        self.assertEqual(len(resp.context["inscriptions"]), 1)
    
    def test_access_rights(self):
        self.create_users(3)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=timezone.now() + datetime.timedelta(10),
            end=timezone.now() + datetime.timedelta(10),
            teacher=self.staff_user,
            max_students=2
        )
        inst.attendants.set(self.users)
        url = test_view.TestURL(self, "agenda", "inscription:manage", status=403,
            kwargs={"pk": inst.pk})
        url.test()
        url.set_user(self.users[0])
        url.test()
        self.users[0].teacher = True
        self.users[0].is_active = True
        self.users[0].save()
        url.status = 200
        resp = url.test()
        messages = list(resp.context['messages'])
        # we should get a message about no edition rights
        self.assertEqual(len(messages), 1)
        self.staff_user.teacher = True
        self.staff_user.save()
        url.set_user(self.staff_user)
        resp = url.test()
        messages = list(resp.context['messages'])
        self.assertEqual(len(messages), 0)
        # check edition mode
        url.method = "post"
        url.status = 302
        url.data = {
            "label": "test2",
            "begin": timezone.now() + datetime.timedelta(10),
            "end": timezone.now() + datetime.timedelta(10),
            "teacher": self.staff_user.pk, # must be a teacher
            "max_students": 2
        }
        resp = url.test()
        inst.refresh_from_db()
        self.assertEqual(inst.label, "test2")
        url.set_user(self.users[0])
        url.status = 200
        resp = url.test()
        messages = list(resp.context['messages'])
        # we should get a message about no edition rights
        self.assertEqual(len(messages), 1)
        # check that returned form has no instance
        self.assertIsNone(resp.context["form"].instance.pk)
    
    def test_delete_inscription(self):
        self.create_users(3)
        inst = am.InscriptionEvent.objects.create(
            label="test",
            begin=timezone.now() + datetime.timedelta(10),
            end=timezone.now() + datetime.timedelta(10),
            teacher=self.staff_user,
            max_students=2
        )
        inst.attendants.set(self.users)
        url = test_view.TestURL(self, "agenda", "inscription:delete", status=403,
            kwargs={"pk": inst.pk})
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.method = "post"
        url.status = 403
        url.test()
        url.method = "get"
        url.status = 200
        url.set_user(self.staff_user)
        url.test()
        url.method = "post"
        url.status = 302
        url.test()
        self.assertEqual(am.InscriptionEvent.objects.count(), 0)


class TestToDo(TestCase, UsersAndWeeks):
    
    def test_todo_access(self):
        self.create_users()
        url = test_view.TestURL(self, "agenda", "todo", status=403)
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()
    
    def test_todo_create(self):
        self.create_users()
        url = test_view.TestURL(self, "agenda", "todo", status=403)
        url.set_user(self.staff_user)
        url.status = 302
        url.method = "post"
        url.data = {
            "date": datetime.date.today(),
            "label": "test",
            "long_label": "test",
            "msg_level": 1
        }
        url.test()
        self.assertEqual(am.ToDo.objects.count(), 1)
    
    def test_todo_update(self):
        self.create_users()
        todo = am.ToDo.objects.create(date=datetime.date.today(), label="test",
            long_label="test")
        url = test_view.TestURL(self, "agenda", "todo", status=302,
            kwargs={"pk": todo.pk})
        url.set_user(self.staff_user)
        url.method = "post"
        url.data = {
            "id": todo.pk,
            "date": datetime.date.today(),
            "label": "test2",
            "msg_level": 2
        }
        url.test()
        todo.refresh_from_db()
        self.assertEqual(todo.label, "test2")
        self.assertEqual(todo.msg_level, 2)
    
    # def test_todo_delete(self):
    #     url = test_view.JsonURL(self, "agenda", "todo", status=403)
    #     url.test(forbidden=True)
    #     url.set_user(self.users[0])
    #     url.status = 200
    #     url.method = "post"
    #     todo = am.ToDo.objects.create(date=datetime.date.today(), label="test")
    #     url.data = {
    #         "id": todo.pk
    #     }
    #     url.test()
    #     self.assertEqual(am.ToDo.objects.count(), 0)
    #     url.status = 403
    #     url.test()
        
        