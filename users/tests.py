import pytest
from django.contrib.auth.models import User
from users.models import UserProfile

@pytest.mark.django_db
def test_user_profile_signal():
    """Test that a UserProfile is created automatically when a User is created."""
    user = User.objects.create_user(username='testuser', password='password123')
    assert UserProfile.objects.filter(user=user).exists()
    assert user.userprofile.timezone == 'UTC'
    assert user.userprofile.ai_tone == 'direct'

@pytest.mark.django_db
def test_landing_page_redirect_authenticated(client):
    """Test that landing page redirects to dashboard for authenticated users."""
    user = User.objects.create_user(username='testuser', password='password123')
    client.login(username='testuser', password='password123')
    response = client.get('/')
    assert response.status_code == 302
    assert response.url == '/dashboard/'
