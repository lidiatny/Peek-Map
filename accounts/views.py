# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from restaurants.models import Restaurant
from .models import Bookmark
from django.contrib.auth.decorators import login_required
from .forms import ProfileForm, ProfileExtraForm
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Simpan user baru
            username = form.cleaned_data.get('username')
            messages.success(request, f'Welcome, {username}!')
            login(request, user)  # Langsung login setelah daftar
            return redirect('core:home')  # Arahkan ke halaman home
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f'Welcome back, {username}!')
                return redirect('core:home')
            else:
                messages.error(request, 'Incorrect username or password.')
        else:
            messages.error(request, 'ncorrect username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have successfully logged out.')
    return redirect('core:home')

def toggle_bookmark(request, resto_id):
    resto = get_object_or_404(Restaurant, id=resto_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, restaurant=resto)
    
    if not created:
        bookmark.delete()
        messages.info(request, 'Restaurant removed from your saved list.')
    else:
        messages.success(request, 'Restaurant saved! ❤️')
    
    # Kembali ke halaman sebelumnya
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))
def profile(request):
    # Ensure profile exists
    from .models import Profile
    profile_obj, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = ProfileForm(request.POST, instance=request.user)
        profile_form = ProfileExtraForm(request.POST, request.FILES, instance=profile_obj)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully! ✅')
            return redirect('accounts:profile')
    else:
        user_form = ProfileForm(instance=request.user)
        profile_form = ProfileExtraForm(instance=profile_obj)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })