from django.urls import path
from .views import (
    index,
    transaction_list,
    create_transaction,
    edit_transaction,
    delete_transaction,
    reports_view,
    advice_view
)

urlpatterns = [
    path('', index, name='index'),
    path('transactions/', transaction_list, name='transaction_list'),
    path('transactions/create/', create_transaction, name='create_transaction'),
    path('transactions/edit/<int:id>/', edit_transaction, name='edit_transaction'),
    path('transactions/delete/<int:id>/', delete_transaction, name='delete_transaction'),
    path('reports/', reports_view, name='reports'), 
    path('advice/', advice_view, name='advice'),
]
