"""
Usage : subclass one of the above mixin and use corresponding method
in setUp method of a TestCase class.
"""

import users.models as um

class CreateUserMixin():

    def create_users(self, nb=1):
        """
        create self.staff_user, self.admin_user and self.users : list
        """
        self.staff_user = um.User.objects.create_user(username="staff", is_staff=True,
            email="staff@example.com")
        self.admin_user = um.User.objects.create_superuser(username="admin",
            email="admin@example.com")
        self.users = []
        for i in range(nb):
            self.users.append(
                um.User.objects.create_user(f"user{i}", email=f"user{i}@example.com")
            )
    
    def create_students(self, nb=3, min=0, level=None):
        self.students = []
        for i in range(min, min+nb):
            self.students.append(
                um.User.objects.create_student(username=f"student{i}",
                    colle_group=(i+1), first_name="John",
                    last_name=f"Doe{i}", level=level,
                    email=f"student{i}_{level}@example.com")
            )
        return self.students
    
    def create_teachers(self, teach_list: list[dict], level=None):
        self.teachers = []
        if level is None:
            level = um.get_default_level(instance=True)
        for teach_dict in teach_list:
            if "subject" in teach_dict:
                subj = teach_dict["subject"]
                if not isinstance(subj, um.Subject):
                    teach_dict["subject"] = um.Subject.objects.get_or_create(
                        level=level, name=subj
                    )[0]  # get_or_create returns a tuple (obj, created), we only want the obj, so
            if "email" not in teach_dict:
                parts = [teach_dict["last_name"], level.name]
                if teach_dict.get("subject") is not None:
                    parts.append(teach_dict["subject"].name)
                teach_dict["email"] = "_".join(p.lower() for p in parts) + "@example.com"
            self.teachers.append(
                um.User.objects.create_teacher(**teach_dict)
            )

TEACHERS = [
    {"last_name": "Teacher1", "first_name": "", "title": "M.", "subject": "Mathématiques"},
    {"last_name": "Teacher2", "first_name": "", "title": "M.", "subject": "Physique"},
    {"last_name": "Teacher3", "first_name": "", "title": "Mme.", "subject": "Anglais"},
    {"last_name": "Teacher4", "first_name": "", "title": "M.", "subject": "Français"},
    {"last_name": "Teacher5", "first_name": "", "title": "M.", "subject": "SII"},
    {"last_name": "Teacher6", "first_name": "", "title": "M.", "subject": "SII"},
]

def create_formset_data(
        atomic_data: list[dict], total_form=0, initial_form=0, prefix="form") -> dict:
    """
    returns a dict with suitable data to POST to a formset view
    """
    data = {
        f"{prefix}-TOTAL_FORMS": total_form,
        f"{prefix}-INITIAL_FORMS": initial_form
    }
    for i, d in enumerate(atomic_data):
        data.update({
            f"{prefix}-{i}-{k}": v for k, v in d.items()
        })
    return data
