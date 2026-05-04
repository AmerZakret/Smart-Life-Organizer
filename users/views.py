from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from .tokens import account_activation_token

User = get_user_model()


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "users/landing.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # In development, automatically activate accounts to ease testing.
            if settings.DEBUG:
                user.is_active = True
            else:
                user.is_active = False  # Deactivate account until email confirmed
            user.save()
            # Create UserProfile automatically via signal or explicitly
            try:
                from .models import UserProfile

                UserProfile.objects.get_or_create(user=user)
            except Exception:
                pass

            # Send activation email when not auto-activated
            if not settings.DEBUG:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = account_activation_token.make_token(user)
                activation_link = request.build_absolute_uri(
                    f"/activate/{uid}/{token}/"
                )
                subject = "Activate your Smart Life Organizer account"
                message = render_to_string(
                    "users/activation_email.txt",
                    {
                        "user": user,
                        "activation_link": activation_link,
                    },
                )
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
                messages.success(
                    request,
                    "Account created. Check your email to activate your account.",
                )
            else:
                messages.success(
                    request, "Account created and activated (development mode)."
                )
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "users/register.html", {"form": form})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(
            request, "Your account has been activated. You can now log in."
        )
        return redirect("login")
    else:
        messages.error(request, "Activation link is invalid or has expired.")
        return redirect("landing-page")
