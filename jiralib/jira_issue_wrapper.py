import urllib
from datetime import datetime

import jira_connector
from jiralib.pm_calc import get_working_days

jira_datetime_tempalte = '%Y-%m-%d %H:%M:%S.%f'
jira_date_tempalte = '%Y-%m-%d'

open_statuses = ['Open', 'To Do', 'Reopened', 'Backlog', 'Ready for Development', 'In Analysis']
closed_statuses = ['Done', 'Closed', 'Verified', 'Resolved', 'Released', 'Ready for Merge', 'Merged']
qa_statuses = ['For Testing', 'Verified', 'Resolved', 'QA', 'Ready for QA', 'In QA', 'Ready for Test']

base_url = jira_connector.settings.get("common", "base_url")

def wrap_issues(issues_to_wrap):
    return list(map(lambda st: JiraIssueWrapper(st), issues_to_wrap))


def wrap_issue(issue):
    return JiraIssueWrapper(issue)


class JiraIssueWrapper:
    def __init__(self, issue):
        self.issue = issue
        self.issue_json = issue.raw
        self.remaining_md = 0
        self.full_md_estimate = 0
        self.done_md_earned = 0
        self.done_md_spent = 0
        self.not_earned_md = 0
        self.sp_velocity = 1

    def get_remaining_md(self):
        return self.remaining_md

    def get_sp_velocity(self):
        return self.sp_velocity

    def get_full_md_estimate(self):
        return self.full_md_estimate

    def get_done_md_earned(self):
        return self.done_md_earned

    def get_done_md_spent(self):
        return self.done_md_spent

    def get_not_earned_md(self):
        return self.not_earned_md

    def get_key(self):
        return self.issue_json['key']

    def get_id(self):
        return self.issue_json['id']

    def get_fields(self):
        return self.issue_json['fields']

    def get_priority(self):
        return self.issue_json['fields']['priority']

    def get_assignee_name(self):
        assignee = self.get_assignee()
        if assignee is None:
            return None
        return assignee['name']

    def get_assignee(self):
        return self.issue_json['fields']['assignee']

    def get_status(self):
        return self.issue_json['fields']['status']['name']

    def get_status_html(self):
        return '<span style="background-color:' + self.get_status_color() + ';">' + self.get_status() + '</span>'

    def get_status_category(self):
        return self.issue_json['fields']['status']['statusCategory']

    def get_status_color(self):
        return self.get_status_category()['colorName'].replace('blue-gray', 'LightGray')

    def get_duedate(self):
        duedate = self.issue_json['fields']['duedate']
        if duedate is not None:
            return to_date(duedate)
        return duedate

    def is_done(self):
        return self.get_status() in closed_statuses

    def is_open(self):
        return self.get_status() in open_statuses

    def get_story_points(self):
        if 'customfield_10002' not in self.issue_json['fields']:
            return None
        return self.issue_json['fields']['customfield_10002']

    def is_estimated(self):
        if self.get_issue_type()['name'] in ('Story', 'Task') and self.get_story_points() is None:
            return False
        return True

    def get_subtasks(self):
        return self.issue_json['fields']['subtasks']

    def get_issue_links(self):
        return self.issue_json['fields']['issuelinks']

    def get_linked_keys_inward(self, inward):
        return list(map(
            lambda li: li['inwardIssue']['key'],
            filter(lambda il: 'inwardIssue' in il and il['type']['inward'] == inward, self.get_issue_links())
        ))

    def get_linked_keys_outward(self, outward):
        return list(map(
            lambda li: li['outwardIssue']['key'],
            filter(lambda il: 'outwardIssue' in il and il['type']['outward'] == outward, self.get_issue_links())
        ))

    def get_related_keys(self):
        return self.get_linked_keys_outward('relates to')

    def get_depend_from_keys(self):
        return self.get_linked_keys_inward('depend from')

    def get_depend_to_keys(self):
        return self.get_linked_keys_outward('depend to')

    def get_part_of_keys(self):
        return self.get_linked_keys_inward('Is part of')

    def get_encorporates_keys(self):
        return self.get_linked_keys_outward('Encorporates')

    def get_issue_type(self):
        return self.issue_json['fields']['issuetype']

    def get_project(self):
        return self.issue_json['fields']['project']

    def get_project_key(self):
        return self.get_project()['key']

    def get_project_name(self):
        return self.get_project()['name']

    def get_resolutiondate(self):
        return self.issue_json['fields']['resolutiondate']

    def get_description(self):
        return self.issue_json['fields']['description']

    def get_summary(self):
        return self.issue_json['fields']['summary']

    def is_epic(self):
        return self.issue_json['fields']['issuetype']['name'] == 'Epic'

    def have_subtasks(self):
        return len(self.issue_json['fields']['subtasks']) > 0

    def get_aggregatetimeestimate(self):
        aggregatetimeestimate = self.issue_json['fields']['aggregatetimeestimate']
        if aggregatetimeestimate is None:
            return None
        return aggregatetimeestimate / 60 / 60 / 8

    def get_aggregatetimeoriginalestimate(self):
        aggregatetimeestimate = self.issue_json['fields']['aggregatetimeoriginalestimate']
        if aggregatetimeestimate is None:
            return None
        return aggregatetimeestimate / 60 / 60 / 8

    def get_progress(self):
        return self.issue_json['fields']['progress']

    def get_work_end_date(self):
        if not self.is_done():
            return None

        histories = list(self.issue_json['changelog']['histories'])
        for history in histories:
            close_history = to_close_entry(history)
            if close_history is not None:
                return to_datetime(close_history['created'])
        return None

    def get_work_start_date(self):
        histories = list(self.issue_json['changelog']['histories'])
        for history in histories:
            open_history = from_open_entry(history)
            if open_history is not None:
                return to_datetime(open_history['created'])
        return None

    def get_actual_working_days(self):
        return self.get_actual_working_days_with_gaps()

    def get_open_issue_assignee_name(self):
        if self.is_open():
            return self.get_assignee_name()
        original_assignee = self.get_assignee_name()
        histories = list(self.issue_json['changelog']['histories'])
        for history in histories:
            original_assignee = get_changed_assignee_name(history) or original_assignee
            open_history = from_open_entry(history)
            if open_history is not None:
                return original_assignee
        return original_assignee

    def get_actual_working_days_with_gaps(self):
        histories = list(self.issue_json['changelog']['histories'])
        working_days_spent = 0
        start_date = None
        for history in histories:
            if start_date is None and is_start_progress(history):
                start_date = to_datetime(history['created'])
            if start_date is not None and is_end_progress(history):
                working_days_spent = working_days_spent + get_working_days(start_date, to_datetime(history['created']))
                start_date = None
        if start_date is not None:
            working_days_spent = working_days_spent + get_working_days(start_date, datetime.now())  # still in progress
        return working_days_spent

    def get_actual_working_days_without_gaps(self):
        start_date = self.get_work_start_date()
        end_date = self.get_work_end_date()
        if start_date is None:
            return 0
        if end_date is None:
            end_date = datetime.now()
        return get_working_days(start_date, end_date)


def to_close_entry(history):
    for item in history['items']:
        if item['field'] == 'status' and item['toString'] in closed_statuses:
            return history
    return None


def is_status_changed(history):
    for item in history['items']:
        if item['field'] == 'status':
            return True
    return False


def is_in_progress_status(status):
    return status not in open_statuses and status not in closed_statuses


def get_changed_assignee_name(history):
    for item in history['items']:
        if item['field'] == 'assignee':
            return item['to']
    return None


def from_open_entry(history):
    for item in history['items']:
        if item['field'] == 'status' and item['fromString'] in open_statuses:
            return history
    return None


def is_end_progress(history):
    for item in history['items']:
        if item['field'] == 'status' and is_in_progress_status(item['fromString']) and not is_in_progress_status(
                item['toString']):
            return True
    return False


def is_start_progress(history):
    for item in history['items']:
        if item['field'] == 'status' and not is_in_progress_status(item['fromString']) and is_in_progress_status(
                item['toString']):
            return True
    return False


def to_datetime(datetimeString):
    return datetime.strptime(datetimeString.replace('T', ' ').replace('+0000', ''), jira_datetime_tempalte)


def to_date(dateString):
    return datetime.strptime(dateString, jira_date_tempalte)


def jql_build_encoded_url(jql):
    return base_url + '/issues/?jql=' + urllib.parse.quote(jql)
