
import jira_connector

jira = jira_connector.jira

jql = 'project = PR '
issues_list = jira.search_issues(jql)

issue = jira.issue('CFD-5792', expand='changelog,transitions,history')

print(issues_list)
print('\n')
