from django.urls import path
from . import views

urlpatterns = [  
   path('login/', views.login_view, name='login'),
   path('logout/', views.logout_view, name='logout'),
   path('signup/', views.signup_view, name='signup'), 
   path('profile/update/', views.profile_update, name='update_profile'),
   path('profile/delete/', views.delete_account, name='delete_account'),
]
