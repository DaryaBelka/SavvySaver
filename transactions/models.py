from django.db import models

class Transaction(models.Model):
    CATEGORY_CHOICES = [
        ('przelewy', 'Przelewy'),
        ('spozywcze', 'Spożywcze'),
        ('zakupy', 'Zakupy'),
        ('zdrowie', 'Zdrowie'),
        ('restauracje', 'Restauracje'),
        ('transport', 'Transport'),
        ('ogolne', 'Ogólne'),
        ('media', 'Media'),
        ('gotowka', 'Gotówka'),
    ]

    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    
    def __str__(self):
        return f"{self.title} - {self.amount} - {self.category}"
