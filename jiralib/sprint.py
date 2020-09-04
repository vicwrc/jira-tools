from collections import namedtuple
from datetime import datetime

from functools import reduce

import jira_connector
from jiralib.jira_issue_wrapper import wrap_issues, to_datetime, jql_build_encoded_url
from jiralib.jira_queries import search_issues
from jiralib.pm_calc import get_working_days

sum_operation = lambda a,b: a + b
story_points_lambda = (lambda task: task.get_story_points() or 0)
sp_8_or_bigger = (lambda task: (task.get_story_points() or 0) >= 8)
sp_5_or_bigger = (lambda task: (task.get_story_points() or 0) >= 5)
# risk rules
finished_sprint_to_be_closed = lambda sprint: sprint.days_remaining < 0
finished_sprint = lambda sprint: sprint.total_sp() > sprint.done_sp() and sprint.days_remaining <= 0
opened_sprint_not_estimated = lambda sprint: len(sprint.get_not_estimated_issues()) > 0
sprint_start_open_issues = (lambda sprint: sprint.early_sprint() and sprint.open_sp() > sprint.total_sp() * 0.50)
start_sprint_big_open = (lambda sprint: sprint.early_sprint() and len(list(filter(sp_8_or_bigger, sprint.get_open_issues()))) > 0)
mid_sprint_open_issues = (lambda sprint: sprint.mid_sprint() and sprint.open_sp() > sprint.total_sp() * 0.25)
mid_sprint_big_open = (lambda sprint: sprint.mid_sprint() and len(list(filter(sp_5_or_bigger, sprint.get_open_issues()))) > 0)
freeze_sprint_open_issues = (lambda sprint: sprint.feature_freeze() and sprint.open_sp() > 0)
freeze_closed = (lambda sprint: sprint.feature_freeze() and sprint.done_sp() < sprint.total_sp() * 0.50)

ValidationRule = namedtuple('ValidationRule', 'rule text severity')

validation_rules = [
    ValidationRule(finished_sprint_to_be_closed, 'Current sprint should be closed', 'Critical'),
    ValidationRule(finished_sprint, 'All tasks must be finished in completed sprint', 'Major'),
    ValidationRule(opened_sprint_not_estimated, 'Active sprint contains not estimated tasks', 'Major'),
    ValidationRule(sprint_start_open_issues, 'More than 50% of tasks are still not started', 'Major'),
    ValidationRule(start_sprint_big_open, 'Some big tasks(more than 8 story points) are not yet started', 'Major'),
    ValidationRule(mid_sprint_open_issues, 'More than 25% of tasks are still not started', 'Major'),
    ValidationRule(mid_sprint_big_open, 'Some medium-to-big tasks(more than 5 story points) are not yet started', 'Major'),
    ValidationRule(freeze_sprint_open_issues, 'Feature freeze is started, but still have open tasks', 'Critical'),
    ValidationRule(freeze_closed, 'Feature freeze is started, but more than 50% of scope is in work', 'Critical')
]


open_issues_jql = ' and status in ("Open", "To Do", "Reopened", "Backlog", "Ready for Development", "In Analysis")'
closed_issues_jql = ' and status in ("Done","Closed","Verified","Resolved", "Released", "Ready for Merge", "Merged")'
in_progress_jql = ' and status not in ("Open", "To Do", "Reopened", "Backlog", "Ready for Development", "In Analysis", "Done","Closed","Verified","Resolved", "Released", "Ready for Merge")'


def get_first_active_sprint(board_id):
    board = list(filter(lambda x: x.id == int(board_id), jira_connector.jira.boards(maxResults=1000, type='scrum')))[0]
    active_sprint = jira_connector.jira.sprints(board_id=int(board_id), state='active', maxResults=10000)[0]
    return Sprint(active_sprint, board.name)


class Sprint:

    def __init__(self, sprint, board_name='Unknown'):
        self.sprint_json = sprint.raw
        self.start_date = to_datetime(sprint.startDate.replace('Z',''))
        self.end_date = to_datetime(sprint.endDate.replace('Z',''))
        self.sprint_issues = wrap_issues(
            search_issues('Sprint = ' + str(sprint.id))
        )
        self.days_passed = get_working_days(self.start_date, datetime.now())
        self.days_remaining = get_working_days(datetime.now(), self.end_date)
        self.alerts = self._calculate_alerts()
        self.board_name = board_name
        self.name = sprint.name
        self.board_id = sprint.originBoardId
        self.goal = sprint.raw.get('goal') or ''
        self.open_issues_url = jql_build_encoded_url('Sprint = ' + str(sprint.id) + open_issues_jql)
        self.in_progress_issues_url = jql_build_encoded_url('Sprint = ' + str(sprint.id) + in_progress_jql)
        self.closed_issues_url = jql_build_encoded_url('Sprint = ' + str(sprint.id) + closed_issues_jql)

    def _calculate_alerts(self):
        alerts = []
        for validation_rule in validation_rules:
            if validation_rule.rule(self):
                alerts.append(validation_rule.severity + ': ' + validation_rule.text)
        return alerts

    def get_html_alerts(self):
        alerts = []
        for validation_rule in validation_rules:
            if validation_rule.rule(self):
                if validation_rule.severity == 'Critical':
                    alerts.append('<a href="#" class="text-danger">' + validation_rule.severity + ': ' + validation_rule.text + '</a>')
                else:
                    alerts.append('<a href="#" class="text-warning">' + validation_rule.severity + ': ' + validation_rule.text + '</a>')
        return alerts

    def print_stats(self):
        print('Board: ' + self.board_name)
        print('Sprint: ' + self.sprint_json['name'])
        print('-------------------------')
        print('Start date: ' + str(self.start_date))
        print('End date: ' + str(self.end_date))
        print(str(self.days_passed) + ' of ' + str(self.days_passed + self.days_remaining) + ' days passed. ' + str(self.days_remaining) + ' days remaining')
        print('-------------------------')
        print('Story points in sprint: ' + str(self.total_sp()))
        print('Open, sp: ' + str(self.open_sp()))
        print('In Progress, sp: ' + str(self.in_progress_sp()))
        print('Done, sp: ' + str(self.done_sp()))
        print('-------------------------')
        for alert in self.alerts:
            print(alert)

    def get_done_issues(self):
        return list(filter(lambda issue: issue.is_done(), self.sprint_issues))

    def get_open_issues(self):
        return list(filter(lambda issue: issue.is_open(), self.sprint_issues))

    def get_in_progress_issues(self):
        return list(filter(lambda issue: not issue.is_open() and not issue.is_done(), self.sprint_issues))

    def get_not_estimated_issues(self):
        return list(filter(lambda issue: not issue.is_estimated() and not issue.is_done(), self.sprint_issues))

    def done_sp(self):
        return reduce(sum_operation, list(map(story_points_lambda, self.get_done_issues())), 0)

    def in_progress_sp(self):
        return reduce(sum_operation, list(map(story_points_lambda, self.get_in_progress_issues())), 0)

    def open_sp(self):
        return reduce(sum_operation, list(map(story_points_lambda, self.get_open_issues())), 0)

    def total_sp(self):
        return self.open_sp() + self.in_progress_sp() + self.done_sp()

    def feature_freeze(self):
        return (self.days_passed + self.days_remaining) * 0.75 < self.days_passed

    def mid_sprint(self):
        return (self.days_passed + self.days_remaining) * 0.5 <= self.days_passed

    def early_sprint(self):
        return (self.days_passed + self.days_remaining) * 0.25 <= self.days_passed

    def done_sp_percent(self):
        if self.total_sp() == 0:
            return 100.0
        return self.done_sp() * 100.0 / self.total_sp()

    def in_progress_sp_percent(self):
        if self.total_sp() == 0:
            return 0.0
        return self.in_progress_sp() * 100.0 / self.total_sp()

    def open_sp_percent(self):
        if self.total_sp() == 0:
            return 0.0
        return self.open_sp() * 100.0 / self.total_sp()