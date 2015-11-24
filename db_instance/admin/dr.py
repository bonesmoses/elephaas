import os
import dns.query
import dns.resolver
import dns.update

from time import sleep

from django.contrib import admin, messages
from django.shortcuts import render

from db_instance.models import DBDR
from db_instance.admin.base import PGUtility

__all__ = ['DBDRAdmin']

# Database DR Admin Model

class DBDRAdmin(admin.ModelAdmin):
    actions = ['failover_pair', 'rebuild_dr']
    exclude = ('created_dt', 'modified_dt')
    list_display = ('label', 'primary', 'secondary', 'vhost', 'get_sync_status')
    search_fields = ('label', 'primary__instance', 'primary__db_host',
        'secondary__instance', 'secondary__db_host', 'vhost')


    def failover_pair(self, request, queryset):
        """
        Switch to the secondary node in a DR pair
        
        This process is fairly complicated, and comes in several parts:
        
        1. Stop the current primary node. This ensures only the secondary
           can accept new data.
        2. Promote the secondary to read/write status. This essentially
           makes it the new master of the pair.
        3. Assign the secondary as the new stream source to the old primary.
           This officially swaps the roles of the two nodes. Note that the
           new secondary is still out of sync with the new master. This will
           require a separate node rebuild step to rectify.
        4. Move the declared virtual host to the secondary node.
        """

        # Go to the confirmation form. As usual, this is fairly important,
        # so make sure the template is extremely descriptive regarding the
        # failover process.

        if request.POST.get('post') != 'yes':

            return render(request, 'admin/failover.html', 
                    {'queryset' : queryset,
                     'opts': self.model._meta}
            )

        # Since the form has been submitted, start swapping DR pairs.

        for dr_id in request.POST.getlist('_selected_action'):
            dbdr = DBDR.objects.get(pk=dr_id)

            try:
                primary = PGUtility(dbdr.primary)
                secondary = PGUtility(dbdr.secondary)

                # We begin by stopping the primary and then waiting a few
                # seconds to help the secondary catch up. Then we promote
                # the secondary itself. At this point, the database is
                # available, but we need to change the old primary to use
                # the secondary as its new master when it's rebuilt.

                primary.stop()
                sleep(5)
                secondary.promote()
                primary.change_master(dbdr.secondary)

                # Now update the DNS. We'll just use the basic dnspython
                # module and load it with nameserver defaults. That should
                # be more than enough to propagate this change.

                def_dns = dns.resolver.get_default_resolver()

                new_dns = dns.update.Update(str(def_dns.domain).rstrip('.'))
                new_dns.delete(str(dbdr.vhost), 'cname')
                new_dns.add(
                    str(dbdr.vhost), '300', 'cname', str(dbdr.secondary.db_host)
                )

                for ns in def_dns.nameservers:
                    dns.query.tcp(new_dns, ns)

                # Now swap the primary and secondary within the DBDR pair
                # itself. This maintains the DR pair relationship, though
                # it has been switched for the time being.

                temp = dbdr.secondary
                dbdr.secondary = dbdr.primary
                dbdr.primary = temp
                dbdr.in_sync = False
                dbdr.save()

            except Exception, e:
                self.message_user(request,
                    "%s : %s" % (e, dbdr), messages.ERROR
                )
                continue

            self.message_user(request,
                "%s failed over to %s!" % (dbdr, dbdr.primary)
            )


    failover_pair.short_description = "Switch Selected Pairs to Secondary Node"


    def get_sync_status(self, dbdr):
        """
        Return the number of bytes DR secondary is behind the primary
        """

        master = PGUtility(dbdr.primary)
        slave = PGUtility(dbdr.secondary)
        status = slave.get_sync_lag(master.get_xlog_location())

        return status is None and 'Unknown' or "{:,}".format(status)

    get_sync_status.short_description = "Sync Delay (bytes)"


    def rebuild_dr(self, request, queryset):
        """
        Rebuild DR secondary node if it is out of sync
        """

        # Go to the confirmation form. As usual, this is fairly important,
        # so make sure the template is extremely descriptive regarding the
        # failover process.

        if request.POST.get('post') != 'yes':

            return render(request, 'admin/rebuild_dr.html', 
                    {'queryset' : queryset,
                     'opts': self.model._meta}
            )

        # Since the form has been submitted, rebuild the replica.
        # Don't forget to mark the pair as in-sync.

        for dr_id in request.POST.getlist('_selected_action'):
            dbdr = DBDR.objects.get(pk=dr_id)

            try:
                util = PGUtility(dbdr.secondary)
                util.master_sync()

                dbdr.in_sync = True
                dbdr.save()

            except Exception, e:
                self.message_user(request,
                    "%s : %s" % (e, dbdr), messages.ERROR
                )
                continue

            self.message_user(request, "%s rebuilt!" % dbdr.secondary)


    rebuild_dr.short_description = "Re-sync Secondary Node in Selected Pairs"


admin.site.register(DBDR, DBDRAdmin)
