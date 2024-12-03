import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from .models import Transaction
from .forms import TransactionForm  
from django.db.models import Sum
from django.db.models.functions import TruncMonth, Trunc
from django.contrib.auth.decorators import login_required

@login_required
def transaction_list(request):
    category = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Фильтруем транзакции по текущему пользователю
    transactions = Transaction.objects.filter(user=request.user)

    if category and category != "all":
        transactions = transactions.filter(category=category)

    if start_date:
        transactions = transactions.filter(date__gte=start_date)  # >=
    if end_date:
        transactions = transactions.filter(date__lte=end_date)  # <=

    total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'transactions/transaction_list.html', {
        'transactions': transactions,
        'total_amount': total_amount,
        'category': category,
        'start_date': start_date,
        'end_date': end_date,
    })

@login_required
def create_transaction(request):
    if request.method == 'POST':
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            handle_uploaded_file(uploaded_file, request.user)  # Передаем пользователя
            return redirect('transaction_list')
        else:
            form = TransactionForm(request.POST)
            if form.is_valid():
                transaction = form.save(commit=False)  # Не сохраняем еще в БД
                transaction.user = request.user  # Устанавливаем текущего пользователя
                transaction.save()  # Теперь сохраняем транзакцию с пользователем
                return redirect('transaction_list')

    else:
        form = TransactionForm()

    return render(request, 'transactions/create_transaction.html', {'form': form})

@login_required
def edit_transaction(request, id):
    transaction = get_object_or_404(Transaction, id=id, user=request.user)  # Фильтр по пользователю
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction)

    return render(request, 'transactions/edit_transaction.html', {'form': form, 'transaction': transaction})

@login_required
def delete_transaction(request, id):
    transaction = get_object_or_404(Transaction, id=id, user=request.user)  # Фильтр по пользователю
    if request.method == 'POST':
        transaction.delete()
        return redirect('transaction_list')

    return render(request, 'transactions/delete_transaction.html', {'transaction': transaction})
 
def handle_uploaded_file(uploaded_file):
    fs = FileSystemStorage()
    filename = fs.save(uploaded_file.name, uploaded_file)
    file_url = fs.url(filename)

    if uploaded_file.name.endswith('.csv'):  # cvs files
        with open(file_url, 'r', newline='') as csvfile:
            #
            #
            raise NotImplementedError("CSV file processing is under development.")

@login_required
def reports_view(request):
    # Aggregate by category for pie chart
    category_summary = (
        Transaction.objects
        .filter(user=request.user)  # Фильтр по пользователю
        .values('category')
        .annotate(total_amount=Sum('amount'))
        .order_by('-total_amount')
    )

    # Aggregate by month for monthly trend analysis
    monthly_summary = (
        Transaction.objects
        .filter(user=request.user)  # Фильтр по пользователю
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total_amount=Sum('amount'))
        .order_by('month')
    )

    # Convert querysets to JSON for use in JavaScript charts
    category_data = json.dumps(list(category_summary), default=str)
    monthly_data = json.dumps(list(monthly_summary), default=str)

    return render(request, 'reports/reports.html', {
        'category_data': category_data,
        'monthly_data': monthly_data,
    })

def index(request):
    return render(request, 'index.html')