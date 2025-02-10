from django.db import models
from django.contrib.auth.models import User  
from decimal import Decimal

class Transaction(models.Model):
    CATEGORY_CHOICES = [
        ('transfers', 'Transfers'),
        ('groceries', 'Groceries'),
        ('shopping', 'Shopping'),
        ('health', 'Health'),
        ('restaurants', 'Restaurants'),
        ('transport', 'Transport'),
        ('general', 'General'),
        ('media', 'Media'),
        ('cash', 'Cash'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)  
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.title} - {self.amount} - {self.category} by {self.user.username if self.user else 'No User'}"

class FinancialGoal(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal_name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    saved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def progress_percentage(self):
        if self.target_amount and self.target_amount > 0:
            return (self.saved_amount / self.target_amount) * Decimal(100)  
        return Decimal(0)

    def months_to_goal(self, monthly_saving):
        remaining_amount = self.target_amount - self.saved_amount
        if monthly_saving > 0:
            return remaining_amount // monthly_saving
        return None

    def __str__(self):
        return f"{self.goal_name} ({self.user.username})"