from django.urls import path
from . import views
from . import api

urlpatterns = [
    path('health/', views.health, name='accounting-health'),
    path('auth/login/', api.login),
    path('dashboard/', api.dashboard),
    path('accounts/', api.accounts),
    path('periods/', api.periods),
    path('parties/', api.parties),
    path('invoices/', api.invoices),
    path('invoices/<int:pk>/post/', api.invoice_post),
    path('payments/', api.payments),
    path('payments/<int:pk>/post/', api.payment_post),
    path('allocations/', api.allocations),
    path('allocations/<int:pk>/deallocate/', api.allocation_deallocate),
    path('outstanding/', api.outstanding),
    path('ledger/<int:pk>/', api.ledger),
    path('reports/<str:name>/', api.report),
]
