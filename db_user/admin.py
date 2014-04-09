from django.contrib import admin
from db_user.models import DBUser
from db_user.forms import DBUserAdminForm

# Register your models here.

class DBUserAdmin(admin.ModelAdmin):
    actions = None
    form = DBUserAdminForm
    list_display = ('usename',)
    list_per_page = 20
    search_fields = ('usename',)

    def queryset(self, request):
        """
        Overridden to filer out super-users.
        """
        qs = super(DBUserAdmin, self).queryset(request)
        qs = qs.exclude(usesuper__exact = True)
        return qs

admin.site.register(DBUser, DBUserAdmin)
