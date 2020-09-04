from jira import JIRA
import configparser

from jira.resources import GreenHopperResource

settings = configparser.ConfigParser()
settings._interpolation = configparser.ExtendedInterpolation()
settings.read('jira.ini')

base_url = settings.get("common", "base_url")
login = settings.get("credentials", "login")
password = settings.get("credentials", "password")

jira_options = {'server': base_url, 'agile_rest_path': GreenHopperResource.AGILE_BASE_REST_PATH }
jira = JIRA(options=jira_options, basic_auth=(login, password))
