"""
date: 2024-06-18

Somme utilities to manipulate different models together.
"""

def regroup_by_month(*iters) -> dict:
    """
    Regroup a list of objects by month.
    The return value is a dict with keys "mm-yyyy" and values are
    dicts {"label": month_label, "objects": list of objects}
    where objects are sorted by date.
    """
    res = {}
    for it in iters:
        for obj in it:
            key = obj.date.strftime("%Y-%m")
            if key not in res:
                res[key] = {"month": obj.date, "objects": []}
            res[key]["objects"].append(obj)
    for key in res:
        res[key]["objects"].sort(key=lambda x: x.date)
    month = list(res.values())
    month.sort(key=lambda x: x["month"])
    return month

