from django.db import models
from django.contrib.auth.models import User
from restaurants.models import Restaurant


class UserActivity(models.Model):
    ACTIVITY_CHOICES = [
        ('view', 'View Restaurant'),
        ('search', 'Search'),
        ('bookmark', 'Bookmark'),
        ('review', 'Write Review'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True, blank=True)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    search_query = models.CharField(max_length=200, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"
    
    class Meta:
        db_table = 'user_activity'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-timestamp']
