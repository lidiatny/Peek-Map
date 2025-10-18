from django.db import models
from django.contrib.auth.models import User
from restaurants.models import Restaurant

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to='review_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.restaurant.name} ({self.rating}⭐)"

    class Meta:
        db_table = 'review'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
    pass


class ReviewReply(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.user.username} to {self.review}"

    class Meta:
        db_table = 'review_reply'
        verbose_name = 'Review Reply'
        verbose_name_plural = 'Review Replies'
        ordering = ['created_at']