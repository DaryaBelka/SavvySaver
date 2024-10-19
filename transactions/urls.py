from django.urls import path
from .views import transaction_list, create_transaction, edit_transaction, delete_transaction, index

urlpatterns = [
    path('', index, name='index'),  
    path('transactions/', transaction_list, name='transaction_list'),  
    path('create/', create_transaction, name='create_transaction'),  
    path('edit/<int:id>/', edit_transaction, name='edit_transaction'),  
    path('delete/<int:id>/', delete_transaction, name='delete_transaction'), 
]
