from collections import namedtuple
from functools import reduce

import jira_connector
from jiralib.jira_issue_wrapper import wrap_issues
from jiralib.jira_queries import get_project_done_tasks_with_story_points
from jiralib.namedtuple_printer import write_csv
from jiralib.pm_calc import Range, get_working_days_from_intervals, get_working_days

min_tasks_for_stat = int(jira_connector.settings.get("capacity", "min_tasks_for_stats", fallback='10'))

ProjectEmployeeStatistics = namedtuple('ProjectEmployeeStatistics',
                                       'name sp_done emd_done tasks_work_days_performed calendar_work_days_performed effective_work_days_performed tasks_amount sp_work_day sp_calendar_day sp_effective_work_day md_work_day md_calendar_day md_effective_work_day')

EmployeeTask = namedtuple('EmployeeTask', 'employee task sp_measure md_measure')


def collect_tasks(sp_issues, is_sp, employees_dict):
    for issue in wrap_issues(sp_issues):
        assignee = issue.get_open_issue_assignee_name()
        if assignee is not None:
            if assignee not in employees_dict:
                employees_dict[assignee] = []
            employees_dict[assignee].append(EmployeeTask(assignee, issue, is_sp, not is_sp))
    return employees_dict


def calculate_calendar_work_days(employee_tasks):
    return get_working_days(
        reduce(lambda a,b: min(a, b),
               map(lambda task: task.task.get_work_start_date(), employee_tasks)),
        reduce(lambda a,b: max(a, b),
               map(lambda task: task.task.get_work_end_date(), employee_tasks))
    )


def calculate_effective_work_days(employee_tasks):
    return get_working_days_from_intervals(
        list(
            map(
                lambda task: Range(task.task.get_work_start_date(), task.task.get_work_end_date()),
                employee_tasks)
        )
    )


def aggregate_stats(employee, employee_tasks, employee_count=1):
    project_employee = ProjectEmployeeStatistics(
        employee,
        reduce(lambda a,b: a + b,
               map(lambda task: task.task.get_story_points() or 0.0, employee_tasks)),
        reduce(lambda a,b: a + b,
               map(lambda task: task.task.get_aggregatetimeoriginalestimate() or 0.0, employee_tasks)),
        reduce(lambda a,b: a + b,
               map(lambda task: task.task.get_actual_working_days() or 0.0, employee_tasks)),
        calculate_calendar_work_days(employee_tasks),
        calculate_effective_work_days(employee_tasks),
        len(employee_tasks),
        0,
        0,
        0,
        0,
        0,
        0
    )
    if project_employee.sp_done > 0:
        project_employee = project_employee._replace(
            sp_work_day=project_employee.tasks_work_days_performed * employee_count/project_employee.sp_done,
            sp_calendar_day=project_employee.calendar_work_days_performed * employee_count/project_employee.sp_done,
            sp_effective_work_day = project_employee.effective_work_days_performed * employee_count/project_employee.sp_done
        )
    if project_employee.emd_done > 0:
        project_employee = project_employee._replace(
            md_work_day=project_employee.tasks_work_days_performed * employee_count/project_employee.emd_done,
            md_calendar_day=project_employee.calendar_work_days_performed * employee_count/project_employee.emd_done,
            md_effective_work_day = project_employee.effective_work_days_performed * employee_count/project_employee.emd_done
        )
    return project_employee


def to_project_statistics(employees_with_tasks):
    project_stats = list(
        map(lambda key: aggregate_stats(key, employees_with_tasks[key]), employees_with_tasks.keys())
    )
    if len(project_stats) > 0:
        project_stats.append(aggregate_stats('-',[val for sublist in employees_with_tasks.values() for val in sublist], len(project_stats)))
    return project_stats


def filter_not_enough_stats(employees_with_tasks):
    filtered_employees = {}
    for (key, value) in employees_with_tasks.items():
        if len(value) >= min_tasks_for_stat:
            filtered_employees[key] = value
    return filtered_employees


def calculate_capacity_by_project(project_name):
    sp_issues = get_project_done_tasks_with_story_points(project_name)
    employees_with_tasks = filter_not_enough_stats(collect_tasks(sp_issues, True, {}))
    return to_project_statistics(employees_with_tasks)


def get_issues_count(issues):
    return len(issues['issues'])


def get_median_sp(estimate):
    return estimate.sp_done / estimate.tasks_amount


def get_median_md(estimnae):
    return estimnae.emd_done / estimnae.tasks_amount


def to_capacity_map(project):
    project_capacity_list = project
    capacity_map = {}
    for project_capacity_item in project_capacity_list:
        capacity_map[project_capacity_item.name] = project_capacity_item
    return capacity_map


def get_open_task_estimate(task, estimate):
    day_estimate = 0
    if estimate is None:
        return day_estimate
    if estimate.sp_calendar_day > 0:
        day_estimate = (task.get_story_points() or get_median_sp(estimate)) * estimate.sp_effective_work_day
    if day_estimate == 0 and estimate.md_calendar_day > 0:
        day_estimate = (task.get_aggregatetimeoriginalestimate() or get_median_md(estimate)) * estimate.md_effective_work_day
    if day_estimate == 0:
        day_estimate = task.get_story_points() or task.get_aggregatetimeoriginalestimate() or 1
    return day_estimate


def get_open_task_estimate_with_default(task, estimate, default_estimate):
    open_task_estimate = get_open_task_estimate(task, estimate)
    if open_task_estimate is None :
        open_task_estimate = get_open_task_estimate(task, default_estimate)
        print(task.get_key() + ' - open_task_estimate is None')
    return open_task_estimate


def get_remaining_task_estimate(task, estimate, default_estimate):
    if task.is_done():
        return 0
    if task.is_open():
        return get_open_task_estimate(task, estimate)
    open_task_estimate = get_open_task_estimate(task, estimate)
    actual_working_days = task.get_actual_working_days()
    if open_task_estimate is None :
        open_task_estimate = get_open_task_estimate(task, default_estimate)
        print(task.get_key() + ' - open_task_estimate is None')
    if actual_working_days is None:
        actual_working_days = 0
        print(task.get_key() + ' - actual_working_days is None')
    diff = open_task_estimate - actual_working_days
    # TODO: play with rules here
    if diff <= 0:
        diff = 1
    return diff


class CapacityCalculator:
    def __init__(self):
        self.projects = {}
        self.projects_assignee_map = {}

    def add_project(self, project_name):
        project = calculate_capacity_by_project(project_name)
        self.projects[project_name] = project
        self.projects_assignee_map[project_name] = to_capacity_map(project)

    def get_project_capacity(self, project_name):
        if project_name not in self.projects:
            self.add_project(project_name)
            self.print_capacity(project_name)
        return self.projects[project_name]

    def print_capacity(self, project_name):
        if project_name not in self.projects:
            self.add_project(project_name)
        write_csv(project_name + '.csv', ProjectEmployeeStatistics, self.get_project_capacity(project_name))

    def calculate_remaining_work_days_for_tasks(self, tasks):
        for task in tasks:
            self.calculate_remaining_work_days_for_task(task)

    def calculate_remaining_work_days_for_task(self, task):
        project_name = task.get_project_key()
        # lazy init project
        project = self.get_project_capacity(project_name)
        project_capacity_map = self.projects_assignee_map[project_name]
        assignee = task.get_open_issue_assignee_name()
        estimate = project_capacity_map.get(assignee) or project_capacity_map.get('-')
        default_estimate = project_capacity_map.get('-')
        day_estimate = get_remaining_task_estimate(task, estimate, default_estimate)
        task.remaining_md = day_estimate
        task.full_md_estimate = get_open_task_estimate_with_default(task, estimate, default_estimate)
        task.done_md_earned = task.full_md_estimate if task.is_done() else 0
        task.done_md_spent = task.get_actual_working_days_without_gaps() if task.is_done() else 0
        task.not_earned_md = task.full_md_estimate if not task.is_done() else 0
        task.sp_velocity = estimate.sp_effective_work_day or 1