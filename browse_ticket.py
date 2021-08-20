import jira_connector

from jiralib.jira_issue_wrapper import wrap_issue

jira = jira_connector.jira

#jql = 'project = PR '
#issues_list = jira.search_issues(jql)
#issue = jira.issue('CFD-5792', expand='changelog,transitions,history')

# https://jira.internal-services.com/browse/BC-9696

issue = jira.issue('DEAL-4499', expand='changelog,transitions,history')
wrapped_issue = wrap_issue(issue)
print(issue)

# customfield_12000 - DEV Assignee
# customfield_11000 - QA Assignee
