from django.urls import include, path

urlpatterns = [
    path("api/accounting/", include("apps.accounting.urls")),
]
