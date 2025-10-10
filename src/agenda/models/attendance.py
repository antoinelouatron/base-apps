"""
date: 2024-03-30
"""
import collections
import re
from django.forms import ValidationError
import users.models as um

class Grouper():

    range_re = re.compile(r'([1-9][0-9]*)-([1-9][0-9]*)')

    @staticmethod
    def minify_groups(groups_list) -> str:
        """
        Returns a comma-separated range list created from an integer list.
        Each range is either a single integer or "begin-end".
        A range is of the form "a-b" where a < b are integers.
        """
        n = len(groups_list)
        if n == 0:
            return ""
        i = 0
        range_list = []
        while i < n:
            beg = groups_list[i]
            end = groups_list[i]
            i += 1
            while i < n and groups_list[i] == end + 1:
                end = groups_list[i]
                i += 1
            if beg == end:
                range_list.append(str(beg))
            else:
                range_list.append(str(beg) + "-" + str(end))
        return ",".join(range_list)

    def explode_range(self, range_str):
        """
        Converse of minify_group
        """
        match = self.range_re.match(range_str.strip())
        if match:
            beg = int(match.group(1))
            end = int(match.group(2))
            return range(beg, end + 1)
        try:
            range_str = int(range_str)
        except ValueError:
            pass
        return (range_str, )
    
    def to_list(self, att_str: str) -> list:
        L = []
        att_list = att_str.split(",")
        for compact in att_list:
            for elt in self.explode_range(compact):
                L.append(elt)
        return L

grouper = Grouper()

def create_default_dict(teachers_dict: dict) -> dict:
    d = {"all": []}
    d.update(teachers_dict)
    return d

class AttComputer():
    """
    Convert a list of comma-separated values to a User list

    values can be a teacher display_name, a colle group number or a colle_group range (begin-end)
    """
    changed_groups = False

    def __init__(self):
        """
        We sort users by level, which have a default value.
        We use defaultdict in case not group have been created for default level
        """
        colle_groups = um.StudentColleGroup.objects.filter(
            user__is_active=True).select_related("user", "group__level")
        colle_groups = colle_groups.order_by("group__level")
        teachers_obj = um.User.objects.filter(teacher=True, is_active=True)
        # convert to dict for fast access
        teachers_dict = {t.display_name: [t] for t in teachers_obj}        
        self.teachers_dict = teachers_dict
        self.att_dict = collections.defaultdict(
            lambda: create_default_dict(teachers_dict))
        all_students = {}
        for cg in colle_groups:
            att_dict = self.att_dict[cg.group.level]
            by_level = all_students.get(cg.group.level, [])
            studs = att_dict.get(cg.colle_group, [])
            studs.append(cg.user)
            att_dict[cg.colle_group] = studs
            by_level.append(cg.user)
            all_students[cg.group.level] = by_level
            self.att_dict[cg.group.level] = att_dict
        for level, att_dict in self.att_dict.items():
            att_dict["all"] = all_students[level]
            att_dict.update(teachers_dict)
        self.all_groups = {}
        for cg in um.ColleGroup.objects.order_by("level", "nb"):
            self.all_groups[cg.level] = self.all_groups.get(cg.level, [])
            self.all_groups[cg.level].append(cg.nb)
        for k,v in self.all_groups.items():
            self.all_groups[k] = grouper.minify_groups(v)

    def __call__(self, att_list, add_teachers=False, level=None) -> list[um.User]:
        if att_list == [""]:
            return []
        if level is None:
            level = um.get_default_level(instance=True)
        att_list = list(filter(lambda s: s != "", att_list))
        att = []
        if add_teachers:
            att_list += list(self.teachers_dict.keys())
        # remove duplicates
        att_list = set(att_list)
        att_dict = self.att_dict[level]
        for compact in att_list:
            for val in grouper.explode_range(compact):
                users = att_dict.get(val)
                if users is None:
                    try:  # if val is a non existent group number, just let it pass
                        int(val)
                        users = []
                    except ValueError as e:
                        raise ValidationError(
                            "Utilisateur ou groupe inconnu : '%(user)s'",
                            params={"user": val}
                            ) from e
                att.extend(users)
        return att

class AttendanceField():
    """
    Descriptor class to manage event attendance by attendance strings.

    An attendance string is a comma separated string of either:
        - an integer, representing a ColleGroup number
        - a range of such integers "a-b", both end included
        - a teacher display_name
    
    Manage attendants and attendance_string together
    """
    
    @property
    def att_computer(self):
        if not hasattr(self, "_att_computer") or AttComputer.changed_groups:
            self._att_computer = AttComputer()
            AttComputer.changed_groups = False
        return self._att_computer
    
    def __set_name__(self, owner, name):
        self.private_name = "_" + name
    
    def __get__(self, obj=None, obj_type=None):
        if obj is None:
            return self # to access att_computer by class attribute
        val = getattr(obj, self.private_name)
        level = getattr(obj, "level", um.get_default_level(instance=True))
        if "all" in val:
            all_groups = self.att_computer.all_groups.get(level, "")
            return val.replace("all", all_groups)
        return val
    
    def __set__(self, obj, value):
        att_list = value.split(",")
        setattr(obj, self.private_name, value)
        level = getattr(obj, "level", um.get_default_level(instance=True))
        att = self.att_computer(att_list, level=level)
        obj.attendants.set(att)
        # take care of cached props. 
        if hasattr(obj, "_att"):
            del obj._att
        if hasattr(obj, "_groups"): # Not used for now
            del obj._groups

