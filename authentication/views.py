from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UserUpdateForm  


def signup_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:  # Password check
            messages.error(request, 'Passwords do not match.')
            return render(request, 'authentication/signup.html')
        
        if User.objects.filter(email=email).exists(): # Email existence check
            messages.error(request, 'Email is already registered.')
            return render(request, 'authentication/signup.html')

        user = User.objects.create_user(username=email, email=email, password=password1)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        login(request, user)
        messages.success(request, 'Registration successful. You are now logged in.')
        return redirect('index')

    return render(request, 'authentication/signup.html')

def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('index')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)      
            return redirect('index')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'authentication/login.html')


def logout_view(request):
    logout(request)

    storage = messages.get_messages(request)
    storage.used = True  

    return redirect('index')

@login_required
def profile_update(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        password_form = PasswordChangeForm(request.user, request.POST)

        if user_form.is_valid() and password_form.is_valid():
            user_form.save()  # Save user data
            user = password_form.save()  # Change user's password
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Profile updated successfully.')
            return redirect('index')

    else:
        user_form = UserUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    return render(request, 'authentication/profile_update.html', {
        'user_form': user_form,
        'password_form': password_form,
    })


@login_required
def delete_account(request):
    if request.method == 'POST':
        request.user.delete()  # Delete the user account
        messages.success(request, 'Your account has been deleted.')
        return redirect('index')

    return render(request, 'authentication/delete_account.html')  
