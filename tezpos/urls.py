from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from orders import views as order_views
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="accounts:redirect")),
    path("accounts/", include("accounts.urls")),
    path("analytics/", include("analytics.urls")),
    path("billing/", include("billing.urls")),
    path("orders/", include("orders.urls")),
    path("kitchen/", include("kitchen.urls")),
    path("branches/", include("branches.urls")),
    path("menu/", include("menu.urls")),
    path("inventory/", include("inventory.urls")),
    path("order/table/<int:pk>/", order_views.customer_menu, name="customer_order"),
    path("order/table/<int:pk>/submit/", order_views.customer_order_create, name="customer_submit"),
    
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)