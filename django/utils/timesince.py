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

TIME_STRING_KEYS = list(TIME_STRINGS.keys())

TIME_CHUNKS = [
    60 * 60 * 24 * 7,  # week
    60 * 60 * 24,  # day
    60 * 60,  # hour
    60,  # minute
]

MONTHS_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


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

    # ignore microseconds
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return avoid_wrapping(time_strings["minute"] % {"num": 0})

    # get years and months
    total_months = (now.year - d.year) * 12 + (now.month - d.month)
    if d.day > now.day:
        total_months -= 1
    years, months = divmod(total_months, 12)
    # calculate the remaining time
    if years or months:
        pivot_month = d.month + months
        pivot_year = d.year + years
        if pivot_month > 12:
            pivot_month -= 12
            pivot_year += 1
        pivot = datetime.datetime(
            pivot_year,
            pivot_month,
            min(MONTHS_DAYS[pivot_month - 1], d.day),
            d.hour,
            d.minute,
        )
    else:
        pivot = d
    remaining_time = (now - pivot).total_seconds()
    partials = [years, months]

    for chunk in TIME_CHUNKS:
        count = remaining_time // chunk
        partials.append(count)
        remaining_time -= chunk * count

    i = 0
    for i, value in enumerate(partials):
        if value != 0:
            break
    else:
        return avoid_wrapping(time_strings["minute"] % {"num": 0})

    result = []
    current_depth = 0

    while i < len(TIME_STRING_KEYS) and current_depth < depth:
        value = partials[i]
        if value == 0:
            break
        name = TIME_STRING_KEYS[i]
        result.append(avoid_wrapping(time_strings[name] % {"num": value}))
        current_depth += 1
        i += 1

    return gettext(", ").join(result)


def timeuntil(d, now=None, time_strings=None, depth=2):
    """
    Like timesince, but return a string measuring the time until the given time.
    """
    return timesince(d, now, reversed=True, time_strings=time_strings, depth=depth)
