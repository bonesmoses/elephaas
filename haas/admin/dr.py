import os
import dns.query
import dns.resolver
import dns.update

from time import sleep

from django.contrib import admin, messages
from django.shortcuts import render

from haas.models import DisasterRecovery, Instance
from haas.admin.base import HAASAdmin
from haas.utility import PGUtility

__all__ = ['DRAdmin']

class DRAdmin(HAASAdmin):
    actions = ['failover_pair',]
    list_display = ('herd', 'container', 'mb_lag', 'vhost')

    list_display_links = None
    can_delete = False


    def has_add_permission(self, request):
        return False


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
        5. Reassign all replicas to follow the new leader. We do this last
           because it relies on DNS propagation, and pushing a reload after
           that step implies a reconnection.
        """

        # Go to the confirmation form. As usual, this is fairly important,
        # so make sure the template is extremely descriptive regarding the
        # failover process.

        if request.POST.get('post') != 'yes':

            return render(request, 'admin/haas/disasterrecovery/failover.html', 
                    {'queryset' : queryset,
                     'opts': self.model._meta,
                     'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
                    }
            )

        # Since the form has been submitted, start swapping DR pairs.

        for dr_id in request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
            newb = Instance.objects.get(pk=dr_id)
            sage = newb.master

            # Start with the transfer: stop -> promote -> alter.
            # Add in a short pause between to allow xlog propagation.

            try:
                sage_util = PGUtility(sage)
                newb_util = PGUtility(newb)

                sage_util.stop()
                sleep(5)
                newb_util.promote()

                sage.master = newb
                sage.save()

            except Exception, e:
                self.message_user(request,
                    "%s : %s" % (e, newb), messages.ERROR
                )
                continue

            # Now update the DNS. We'll just use the basic dnspython
            # module and load it with nameserver defaults. That should
            # be more than enough to propagate this change.

            try:
                def_dns = dns.resolver.get_default_resolver()

                new_dns = dns.update.Update(str(def_dns.domain).rstrip('.'))
                new_dns.delete(str(newb.herd.vhost), 'cname')
                new_dns.add(
                    str(newb.herd.vhost), '300', 'cname',
                    str(newb.server.hostname)
                )

                for ns in def_dns.nameservers:
                    dns.query.tcp(new_dns, ns)

            except Exception, e:
                self.message_user(request,
                    "%s : %s" % (e, newb), messages.ERROR
                )
                continue

            # Now we should get the list of all replica instances in this
            # herd, which should include the old primary. We just need to
            # update the recovery.conf file and reload the instance.

            try:
                herd = Instance.objects.filter(
                    master_id__isnull = False,
                    herd_id = newb.herd_id
                )

                for member in herd:
                    member.master = newb
                    member.save()

                    util = PGUtility(member)
                    util.update_stream_config()
                    util.reload()                

            except Exception, e:
                self.message_user(request,
                    "%s : %s" % (e, newb), messages.ERROR
                )
                continue

            self.message_user(request,
                "%s now active on %s!" % (newb.herd, newb.server.hostname)
            )

    failover_pair.short_description = "Fail Over to Listed Replica"

admin.site.register(DisasterRecovery, DRAdmin)
