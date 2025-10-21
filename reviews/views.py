# reviews/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from restaurants.models import Restaurant
from .models import Review, ReviewReply
from django.core.paginator import Paginator
from django.db.models import Q

@login_required
def write_review(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    # Cek apakah user sudah pernah review restoran ini
    existing_review = Review.objects.filter(user=request.user, restaurant=restaurant).first()

    if existing_review:
        messages.warning(request, 'Kamu sudah pernah memberi ulasan untuk restoran ini.')
        return redirect('restaurants:detail', restaurant_id=restaurant.id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        photo = request.FILES.get('photo')

        if not rating or not comment:
            messages.error(request, 'Rating dan komentar wajib diisi.')
        else:
            try:
                review = Review.objects.create(
                    user = request.user,
                    restaurant = restaurant,
                    rating = int(rating),
                    comment = comment,
                    photo = photo
                )
                messages.success(request, 'Terima kasih atas ulasannya! 🎉')
                return redirect('restaurants:detail', restaurant_id=restaurant.id)
            except IntegrityError:
                messages.error(request, 'Gagal menyimpan ulasan. Coba lagi.')

    return render(request, 'reviews/write_review.html', {
        'restaurant': restaurant
    })
@login_required
def edit_review(request, review_id):
    # Ambil review, pastikan user yang login adalah pemiliknya
    review = get_object_or_404(Review, id=review_id, user=request.user)
    restaurant = review.restaurant

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating or not comment:
            messages.error(request, 'Rating dan komentar wajib diisi.')
        else:
            try:
                review.rating = int(rating)
                review.comment = comment
                review.save()
                messages.success(request, 'Ulasan berhasil diperbarui! ✅')
                return redirect('restaurants:detail', restaurant_id=restaurant.id)
            except Exception as e:
                messages.error(request, 'Gagal menyimpan perubahan. Coba lagi.')

    return render(request, 'reviews/edit_review.html', {
        'review': review,
        'restaurant': restaurant
    })


@login_required
def add_reply(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    
    if request.method == 'POST':
        reply_text = request.POST.get('reply_text')
        
        if not reply_text:
            messages.error(request, 'Reply tidak boleh kosong.')
        else:
            try:
                ReviewReply.objects.create(
                    review=review,
                    user=request.user,
                    reply_text=reply_text
                )
                messages.success(request, 'Reply berhasil ditambahkan!')
            except Exception as e:
                messages.error(request, 'Gagal menambahkan reply. Coba lagi.')
    
    return redirect('restaurants:detail', restaurant_id=review.restaurant.id)

@login_required
def review_history(request):
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "latest").strip()

    reviews = (Review.objects
               .filter(user=request.user)
               .select_related("restaurant"))

    if q:
        reviews = reviews.filter(
            Q(restaurant__name__icontains=q) |
            Q(comment__icontains=q)
        )

    order_map = {
        "latest": "-created_at",
        "oldest": "created_at",
        "rating_desc": "-rating",
        "rating_asc": "rating",
    }
    reviews = reviews.order_by(order_map.get(sort, "-created_at"))

    paginator = Paginator(reviews, 10)  # 10 item per halaman
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
        "sort": sort,
        "total": reviews.count(),
    }
    return render(request, "reviews/history.html", context)