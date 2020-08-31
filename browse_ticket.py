import jira_connector
import sys

from jiralib.csv_reader import read_csv

jira = jira_connector.jira

# https://jira.internal-services.com/browse/BC-9696

issue = jira.issue('BC-9696', expand='changelog,transitions,history')
print(issue)