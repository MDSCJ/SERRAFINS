from django.urls import path

from .views import about_view, dashboard_view, google_login_callback_view, google_login_start_view, home_view, login_view, logout_view, packages_view, register_view, shark_key_view, shark_cnn_view, shark_cnn_load_model_view

urlpatterns = [
    path("", home_view, name="home"),
    path("about/", about_view, name="about"),
    path("packages/", packages_view, name="packages"),
    path("shark-key/", shark_key_view, name="shark_key"),
    path("shark-cnn/", shark_cnn_view, name="shark_cnn"),
    path("shark-cnn/load-model/", shark_cnn_load_model_view, name="shark_cnn_load_model"),
    path("login/", login_view, name="login"),
    path("auth/google/start/", google_login_start_view, name="google_login_start"),
    path("auth/google/callback/", google_login_callback_view, name="google_login_callback"),
    path("register/", register_view, name="register"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("logout/", logout_view, name="logout"),
]
