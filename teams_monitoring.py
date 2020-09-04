from jiralib.sprint import get_first_active_sprint


def print_board_stats(id):
    try:
        sprint = get_first_active_sprint(id)
        sprint.print_stats()
    except Exception:
        print('Error during board '+ id + ' showing')

boards = ['1','93','97', '5', '87', '103']

for board_id in boards:
    print_board_stats(board_id)
    print('')
    print('')