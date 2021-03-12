from collections import namedtuple


# jira_query = '"Epic Link" =EPIC-39 AND labels = Phase2 and key not in (BC-10479, BC-10478)'
from jiralib.jira_printer import write_tasks

#jira_query = 'project = DEAL and Sprint in openSprints() and status != open'
jira_query = 'project =B2C and statusCategory =Done and "Squad or Team" ="Product Mobiles"  and updatedDate >= 2020-06-01 and "Story Points" is not EMPTY'
# filename = "epic-22_p1.csv"
filename = "product_mobiles.csv"

# jira_query = '"Epic Link" =DEAL-4026'
# filename = "Variable spread.csv"

# write_tasks(filename, jira_query, namedtuple('TestTuple',
#                                             'key summary assignee_name status actual_working_days_with_gaps actual_working_days_without_gaps story_points remaining_md full_md_estimate done_md_earned done_md_spent not_earned_md'))

write_tasks(filename, jira_query, namedtuple('TestTuple',
                                             'key assignee_name status actual_working_days_with_gaps actual_working_days_without_gaps dev_actual_working_days_with_gaps qa_actual_working_days_with_gaps story_points sp_velocity summary'))
