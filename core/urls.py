from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import about_view, dashboard_view, home_view, login_view, packages_view, register_view, shark_key_view, shark_cnn_view

urlpatterns = [
    path("", home_view, name="home"),
    path("about/", about_view, name="about"),
    path("packages/", packages_view, name="packages"),
    path("shark-key/", shark_key_view, name="shark_key"),
    path("shark-cnn/", shark_cnn_view, name="shark_cnn"),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
