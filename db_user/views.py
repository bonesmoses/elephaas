from django.shortcuts import render
from db_user.forms import DBUserPasswordForm

# Create your views here.

def index(request):
    if request.method == 'POST':
        form = DBUserPasswordForm(request.POST)
        if form.is_valid():
            form.save()
    else:
        form = DBUserPasswordForm()

    return render(request, 'db_user/index.html', {'form': form})
