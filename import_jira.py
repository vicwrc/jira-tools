
import jira_connector

jira = jira_connector.jira

jql = 'project = PR '
issues_list = jira.search_issues(jql)

print(issues_list)