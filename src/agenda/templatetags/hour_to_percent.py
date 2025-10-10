"""
Created on Sun Nov 22 21:48:26 2015
"""

import datetime

from django import template

register = template.Library()


def time_diff(t1, t2):
    """
    Compute the timedelta bewteen to time objects.
    """
    today = datetime.date.today()
    return datetime.datetime.combine(today, t1) - datetime.datetime.combine(today, t2)

@register.simple_tag
def to_rem(time1, time2=None):
    """
    Convention : 30 min = 2rem

    If only one time is given, compute difference to 8:00
    """
    if time2 is None:
        time2 = datetime.time(8, 0)
    return (2 * int(time_diff(time1, time2).total_seconds())) // 1800

COLORS_MAP = {
    "math": ["bg-cyan-200", "text-blue-800", "dark:bg-cyan-700", "dark:text-blue-100"],
    "physique": ["bg-amber-200", "text-amber-800", "dark:bg-amber-700", "dark:text-amber-100"],
    "anglais": ["bg-emerald-200", "text-emerald-800", "dark:bg-emerald-700", "dark:text-emerald-100"],
    "francais": ["bg-red-200", "text-red-800", "dark:bg-red-700", "dark:text-red-100"],
    "si": ["bg-indigo-200", "text-indigo-800", "dark:bg-indigo-700", "dark:text-indigo-100"],
    "info": ["bg-stone-200", "text-stone-800", "dark:bg-stone-700", "dark:text-stone-100"],
    "tipe": ["bg-rose-200", "text-rose-800", "dark:bg-rose-700", "dark:text-rose-100"],
    "inscription": ["bg-lime-200", "text-lime-800", "dark:bg-lime-700", "dark:text-lime-100"],
}

COLORS_MAP["physique-chimie"] = COLORS_MAP["physique"]
COLORS_MAP["français"] = COLORS_MAP["francais"]

@register.simple_tag
def event_classes(ev, overlap_nb=1, position=0):
    """
    Size and color classes
    """
    classes = []
    classes.extend(COLORS_MAP.get(ev.subject, []))
    ev_height = to_rem(ev.endhour, ev.beghour)
    if ev_height > 6:  # 6rem is approx 1.5H
        classes.append("pt-2 big")
    elif ev_height > 4:  # 4rem is approx 1H
        classes.append("medium") # medium
    else:
        classes.append("small")
    if overlap_nb == 1:
        classes.append("large")
    if position == 0:
        classes.append("border-l-0") # first
    if position == overlap_nb - 1:
        classes.append("border-r-0") # last
    return " ".join(classes)
