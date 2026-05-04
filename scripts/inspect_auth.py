import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartlife_project.settings")
django.setup()

from django.contrib.auth.forms import AuthenticationForm  # noqa: E402

f = AuthenticationForm()
print(list(f.fields.keys()))
for name in f.fields:
    print(name, f.fields[name].widget.input_type)
