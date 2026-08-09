from django.urls import path

from .views import health


urlpatterns = [path("saude/", health, name="health")]
