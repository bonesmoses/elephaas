from django.contrib import admin
from django.conf.urls import url
from django.shortcuts import render

__all__ = ['HAASAdmin']

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
