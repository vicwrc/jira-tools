import jira_connector

from jiralib.jira_issue_wrapper import wrap_issue

jira = jira_connector.jira

#jql = 'project = PR '
#issues_list = jira.search_issues(jql)
#issue = jira.issue('CFD-5792', expand='changelog,transitions,history')

# https://jira.internal-services.com/browse/BC-9696

issue = jira.issue('BC-9696', expand='changelog,transitions,history')
wrapped_issue = wrap_issue(issue)
print(issue)