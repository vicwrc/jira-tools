import jira_connector
from jiralib.capacity_calculator import CapacityCalculator
from jiralib.jira_issue_wrapper import wrap_issues
from jiralib.jira_queries import search_issues
from jiralib.namedtuple_printer import write_csv


def convert(list):
    return (*list, )

def jira_to_tuple(jira, header):
    columns = []
    for col in list(header._fields):
        columns.append(getattr(jira, "get_"+col)())
    return convert(columns)


def to_tuple(jira_issues, header):
    return list(map(lambda jira: jira_to_tuple(jira, header), jira_issues))


def write_tasks(filename, query, header, capacity_calculator=CapacityCalculator()):
    jira_issues = wrap_issues(search_issues(query))
    capacity_calculator.calculate_remaining_work_days_for_tasks(jira_issues)
    issues_tuple = to_tuple(jira_issues, header)
    write_csv(filename, header, issues_tuple)