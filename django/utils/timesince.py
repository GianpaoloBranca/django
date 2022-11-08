import calendar
import datetime

from django.utils.html import avoid_wrapping
from django.utils.timezone import is_aware
from django.utils.translation import gettext, ngettext_lazy

TIME_STRINGS = {
    "year": ngettext_lazy("%(num)d year", "%(num)d years", "num"),
    "month": ngettext_lazy("%(num)d month", "%(num)d months", "num"),
    "week": ngettext_lazy("%(num)d week", "%(num)d weeks", "num"),
    "day": ngettext_lazy("%(num)d day", "%(num)d days", "num"),
    "hour": ngettext_lazy("%(num)d hour", "%(num)d hours", "num"),
    "minute": ngettext_lazy("%(num)d minute", "%(num)d minutes", "num"),
}

TIMESINCE_CHUNKS = (
    (60 * 60 * 24 * 365, "year"),
    (60 * 60 * 24 * 30, "month"),
    (60 * 60 * 24 * 7, "week"),
    (60 * 60 * 24, "day"),
    (60 * 60, "hour"),
    (60, "minute"),
)

MONTHS_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def timesince_months(d, now):
    months = now.month - d.month
    if months > 0:
        if d.day > now.day:
            months -= 1
    elif months < 0:
        months += 12
        if d.day > now.day:
            months -= 1
    elif d.day > now.day:
        months = 11
    if months == 0:
        # doesn't matter the month avg time since there are 0
        return (0, 30 * 24 * 60 * 60)
    month = (d.month + months) % 12
    if month == 0:
        month = 12
    oneyear = datetime.timedelta(days=365)
    pivot = datetime.datetime(
        now.year, month, min(MONTHS_DAYS[month - 1], d.day), tzinfo=now.tzinfo
    )
    if pivot > now:
        pivot -= oneyear
    d_adj = datetime.datetime(now.year, d.month, d.day, tzinfo=now.tzinfo)
    if d_adj > now:
        d_adj -= oneyear
    total = (pivot - d_adj).total_seconds()
    return (months, (total / months))


def timesince(d, now=None, reversed=False, time_strings=None, depth=2):
    """
    Take two datetime objects and return the time between d and now as a nicely
    formatted string, e.g. "10 minutes". If d occurs after now, return
    "0 minutes".

    Units used are years, months, weeks, days, hours, and minutes.
    Seconds and microseconds are ignored. Up to `depth` adjacent units will be
    displayed.  For example, "2 weeks, 3 days" and "1 year, 3 months" are
    possible outputs, but "2 weeks, 3 hours" and "1 year, 5 days" are not.

    `time_strings` is an optional dict of strings to replace the default
    TIME_STRINGS dict.

    `depth` is an optional integer to control the number of adjacent time
    units returned.

    Adapted from
    https://web.archive.org/web/20060617175230/http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """
    if time_strings is None:
        time_strings = TIME_STRINGS
    if depth <= 0:
        raise ValueError("depth must be greater than 0.")
    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    now = now or datetime.datetime.now(datetime.timezone.utc if is_aware(d) else None)

    if reversed:
        d, now = now, d
    delta = now - d

    # Deal with leapyears by subtracing the number of leapdays
    leapdays = calendar.leapdays(d.year, now.year)
    if leapdays != 0:
        if calendar.isleap(d.year):
            leapdays -= 1
        elif calendar.isleap(now.year):
            leapdays += 1
    delta -= datetime.timedelta(leapdays)

    time_chunks = list(TIMESINCE_CHUNKS)
    months, avg = timesince_months(d, now)
    time_chunks[1] = (avg, "month")

    # ignore microseconds
    since = delta.days * 24 * 60 * 60 + delta.seconds

    if since <= 0:
        # d is in the future compared to now, stop processing.
        return avoid_wrapping(time_strings["minute"] % {"num": 0})

    for i, (seconds, name) in enumerate(time_chunks):
        if name == "month":
            # count might overshoot if now.month is longer than the calculated length
            count = months
        else:
            count = since // seconds
        if count != 0:
            break
    else:
        return avoid_wrapping(time_strings["minute"] % {"num": 0})

    result = []
    current_depth = 0

    while i < len(time_chunks) and current_depth < depth:
        seconds, name = time_chunks[i]
        count = since // seconds
        if name == "month":
            # count might overshoot if now.month is longer than the calculated length
            count = min(count, months)
        if count == 0:
            break
        result.append(avoid_wrapping(time_strings[name] % {"num": count}))
        since -= seconds * count
        current_depth += 1
        i += 1
    return gettext(", ").join(result)


def timeuntil(d, now=None, time_strings=None, depth=2):
    """
    Like timesince, but return a string measuring the time until the given time.
    """
    return timesince(d, now, reversed=True, time_strings=time_strings, depth=depth)
