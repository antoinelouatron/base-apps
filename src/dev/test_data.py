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
        self.staff_user = um.User.objects.create_user(username="staff", is_staff=True)
        self.admin_user = um.User.objects.create_superuser(username="admin")
        self.users = []
        for i in range(nb):
            self.users.append(
                um.User.objects.create_user(f"user{i}")
            )
    
    def create_students(self, nb=3, min=0, level=None):
        self.students = []
        for i in range(min, min+nb):
            self.students.append(
                um.User.objects.create_student(username=f"student{i}",
                    colle_group=(i+1), student=True, first_name="John",
                    last_name=f"Doe{i}", level=level)
            )
        return self.students
    
    def create_teachers(self, teach_list: list[dict]):
        self.teachers = []
        for teach_dist in teach_list:
            self.teachers.append(
                um.User.objects.create_teacher(**teach_dist)
            )

TEACHERS = [
    {"last_name": "Louatron", "first_name": "", "title": "M."},
    {"last_name": "Thibierge", "first_name": "", "title": "M."},
    {"last_name": "Agoutin", "first_name": "", "title": "Mme."},
    {"last_name": "Bourdelle", "first_name": "", "title": "M."},
    {"last_name": "Pigny", "first_name": "", "title": "M."},
    {"last_name": "Levavasseur", "first_name": "", "title": "M."},
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
