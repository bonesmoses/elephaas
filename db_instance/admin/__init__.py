from django.contrib import admin

# Disable the "Delete selected" action. Bad.

try:
  admin.site.disable_action('delete_selected')
except:
  pass

from db_instance.admin.instance import *
from db_instance.admin.replica import *
from db_instance.admin.dr import *
