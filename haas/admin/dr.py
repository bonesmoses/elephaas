from django.contrib import admin
from django.shortcuts import render

from haas.models import DisasterRecovery

__all__ = ['DRAdmin']

class DRAdmin(admin.ModelAdmin):
    actions = ['failover_pair',]
    list_display = ('herd', 'container', 'mb_lag', 'vhost')

    list_display_links = None
    can_delete = False


    def get_actions(self, request):
        """
        Remove Unused Actions From Master Class

        Though we inherit quite a lot from the Instance admin menu, we don't
        need most of the actions. So we'll throw away the ones we didn't
        explicitly include.
        """
        actions = super(DRAdmin, self).get_actions(request)

        for key in actions.keys():
            if key not in self.actions:
                del(actions[key])

        return actions


    def container(self, instance):
        return instance.server.hostname
    container.short_description = 'DR Container'


    def failover_pair(self, request, queryset):
        """
        Promote a Herd Follower to Leader Status

        This process is fairly complicated, and comes in several parts:

        1. Stop the current primary node. This ensures only the secondary
           can accept new data.
        2. Promote the top follower to read/write status. This essentially
           makes it the new leader of the herd.
        3. Assign the follower as the new stream source to the old primary.
           This officially swaps the roles of the two nodes. Note that the
           new follower is still out of sync with the new leader. This will
           require a separate node rebuild step to rectify.
        4. Move the declared virtual host to the new leader.
        """

        # Go to the confirmation form. As usual, this is fairly important,
        # so make sure the template is extremely descriptive regarding the
        # failover process.

        if request.POST.get('post') != 'yes':

            return render(request, 'admin/haas/dr/failover.html', 
                    {'queryset' : queryset,
                     'opts': self.model._meta,
                     'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
                    }
            )

        # Since the form has been submitted, start swapping DR pairs.

        for dr_id in request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
            dbdr = DisasterRecovery.objects.get(pk=dr_id)

            try:
                new_leader = PGUtility(dbdr.instance)

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

    failover_pair.short_description = "Fail Over to Listed Replica"

admin.site.register(DisasterRecovery, DRAdmin)
