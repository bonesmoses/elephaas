from django.shortcuts import render
from db_user.forms import DBUserPasswordForm

# Create your views here.

def index(request):
    """
    Display the index of the db_user module

    The index for the db_user module is actually a password change page. All
    of the real work is done in the Django administrative side otherwise.
    """
    if request.method == 'POST':
        form = DBUserPasswordForm(request.POST)
        if form.is_valid():
            form.save()
    else:
        form = DBUserPasswordForm()

    return render(request, 'db_user/index.html', {'form': form})
