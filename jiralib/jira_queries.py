import jira_connector

jira = jira_connector.jira


def search_issues(jql):
    issues_list = jira.search_issues(jql,expand='changelog,transitions,history',maxResults=10000)
    return issues_list


def get_project_done_tasks_with_story_points(project_name):
    return search_issues('project = ' + project_name + ' AND "Story Points"  is not empty and statusCategory = done and status !="Ready for Test" and created >= -90d')
