import math
from collections import namedtuple
from datetime import timedelta, datetime
from functools import reduce

import workdays


Range = namedtuple('Range', ['start', 'end'])


def to_calendar_days(working_days):
    rest = working_days % 5
    weeks = working_days // 5
    return weeks * 7 + rest


def to_working_days(calendar_days):
    rest = calendar_days % 7
    weeks = calendar_days // 7
    return weeks * 5 + min(rest, 5)


def get_working_days(fromdate, todate):
    return workdays.networkdays( fromdate, todate )


def square_min(base_estimate):
    return base_estimate - math.sqrt(base_estimate)


def square_max(base_estimate):
    return base_estimate + math.sqrt(base_estimate)


def merge_timeranges(list_of_ranges):
    list_of_ranges.sort(key=lambda r: r.start)
    merged_ranges = []
    current = None
    for range in list_of_ranges:
        if current is None:
            current = range
        else:
            if current.end >= range.start:
                current = current._replace(end=range.end)
            else:
                merged_ranges.append(current)
                current = range
    if current is not None:
        merged_ranges.append(current)
    return merged_ranges


def get_working_days_from_intervals(list_of_ranges):
    return reduce(lambda a,b: a+b, list(
        map(lambda range: get_working_days(range.start, range.end), merge_timeranges(list_of_ranges))
    ), 0)


def get_work_days_planned(start_date, end_date):
    non_null_start_date = start_date or datetime.now()
    return get_working_days(non_null_start_date, end_date or non_null_start_date)


def get_work_days_elapsed(start_date):
    return get_working_days(start_date or datetime.now(), datetime.now())


def cv(ev, ac):
    # Cost Variance (CV) = EV - AC. Good if > 0
    return ev - ac


def sv(ev, pv):
    # Schedule Variance (SV) = EV - PV. Good if > 0
    return ev - pv


def cpi(ev, ac):
    '''
    The most commonly used cost-efficiency indicator is the cost performance index (CPI). It is calculated thus:

        CPI = EV / AC

    The sum of all individual EV budgets divided by the sum of all individual AC's is known as the cumulative CPI, and is generally used to forecast the cost to complete a project.
    '''
    if ac == 0:
        return 1
    return ev / ac


def spi(ev, pv):
    '''
    The schedule performance index (SPI), calculated thus:

        SPI = EV / PV

    is often used with the CPI to forecast overall project completion estimates.

    A negative schedule variance (SV) calculated at a given point in time means the project is behind schedule, while a negative cost variance (CV) means the project is over budget.
    '''
    if pv == 0:
        return 1
    return ev / pv


def eva_estimated_end_date(pv, ev, start_date, due_date):
    wd_planned = get_work_days_planned(start_date, due_date)

    if wd_planned == 0:
        return due_date

    return start_date + timedelta(days=to_calendar_days(round(wd_planned / spi(ev, pv))))


def eva_estimated_budget(ev, ac, max_pv):
    return (max_pv / ev) * ac
