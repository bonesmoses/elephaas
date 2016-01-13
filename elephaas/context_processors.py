from django.conf import settings

def global_settings(request):
    # return any necessary values
    return {
        'PUBLIC_KEY': settings.PUBLIC_KEY,
    }
