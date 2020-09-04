import jira_connector
import sys

from jiralib.csv_reader import read_csv

jira = jira_connector.jira


def create_story(issue_tuple):
    issue_dict = {
        'issuetype': {'name': 'Story'},
    }
    result_dict = {**dict(issue_tuple._asdict()), **issue_dict}
    return jira.create_issue(fields=result_dict)


issues_csv_file = sys.argv[1]
issues_content = read_csv(issues_csv_file)
for issue_content in issues_content:
    create_story(issue_content)

print('done!')
#jql = 'project = PR '
#issues_list = jira.search_issues(jql)
#issue = jira.issue('CFD-5792', expand='changelog,transitions,history')

