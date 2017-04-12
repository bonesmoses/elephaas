from django.contrib import admin, messages
from django.conf.urls import url
from django.shortcuts import render

from haas.models import Instance
from haas.utility import PGUtility

__all__ = ['HAASAdmin', 'SharedInstanceAdmin',]

class HAASAdmin(admin.ModelAdmin):
    """
    Provide Help Menus in Admin Site

    The default admin site is pretty sparse. Lots of Postgres-related concepts
    should be explained for uninitiated, and yet those elements are missing 
    from the admin. This override for the base model admin class provides
    context-sensitive help to describe usage scenarios.

    Each module can have a help template located at:

      templates/admin/haas/[module]/help.html
    """

    def get_urls(self):
        urls = super(HAASAdmin, self).get_urls()
        my_urls = [
            url(r'^help/$', self.help),
        ]
        return my_urls + urls

    def help(self, request):
        """
        Display the Proper Help Template Corresponding to the Active Module
        """
        context = dict(
           self.admin_site.each_context(request),
           app_label = self.model._meta.app_label,
           opts = self.model._meta
        )
        modname = str(request.path.split('/')[-3])
        return render(request, 'admin/haas/' + modname + '/help.html', context)


class SharedInstanceAdmin(HAASAdmin):

    def rebuild_instances(self, request, queryset):
        """
        Rebuild all transmitted PostgreSQL replication instances from master
        """

        # If we should be rebuilding an instance, connect to the host,
        # ensure the instance is stopped, and sync the data directories
        # through rsync + ssh.

        if request.POST.get('post') == 'yes':

            for inst_id in request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
                inst = Instance.objects.get(pk=inst_id)

                try:
                    util = PGUtility(inst)
                    util.master_sync()

                except Exception, e:
                    self.message_user(request, "%s : %s" % (e, inst), messages.ERROR)
                    continue

                self.message_user(request, "%s rebuilt!" % inst)
            return

        # Now go to the confirmation form. It's very basic, and only serves
        # to disrupt the process and avoid accidental rebuilds.

        return render(request, 'admin/haas/shared/rebuild.html', 
                {'queryset' : queryset,
                 'opts': self.model._meta,
                 'crumb_title': self.rebuild_instances.short_description,
                 'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
                }
        )

    rebuild_instances.short_description = "Rebuild Selected Replicas"
