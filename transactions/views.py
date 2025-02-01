import json
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from .forms import TransactionForm  
from itertools import accumulate
from datetime import datetime
from django.db.models import Sum
from django.db.models.functions import Trunc
from django.contrib.auth.decorators import login_required
from .models import Transaction

@login_required
def transaction_list(request):
    category = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

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
            handle_uploaded_file(uploaded_file, request.user)  
            return redirect('transaction_list')
        else:
            form = TransactionForm(request.POST)
            if form.is_valid():
                transaction = form.save(commit=False)  
                transaction.user = request.user  
                transaction.save()  
                return redirect('transaction_list')

    else:
        form = TransactionForm()

    return render(request, 'transactions/create_transaction.html', {'form': form})

@login_required
def edit_transaction(request, id):
    transaction = get_object_or_404(Transaction, id=id, user=request.user)  
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
    transaction = get_object_or_404(Transaction, id=id, user=request.user)
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
    current_month = datetime.now().month
    current_year = datetime.now().year

    monthly_summary = (
        Transaction.objects
        .filter(user=request.user, date__month=current_month, date__year=current_year)
        .annotate(day=Trunc('date', 'day'))
        .values('day')
        .annotate(total_amount=Sum('amount'))
        .order_by('day')
    )
    monthly_data = list(monthly_summary)

    cumulative_amounts = list(accumulate(item['total_amount'] for item in monthly_data))
    for i, amount in enumerate(cumulative_amounts):
        monthly_data[i]['cumulative_total'] = amount

    category_summary = (
        Transaction.objects
        .filter(user=request.user, date__month=current_month, date__year=current_year)
        .values('category')
        .annotate(total_amount=Sum('amount'))
        .order_by('-total_amount')
    )

    total_expenses_for_month = sum(item['total_amount'] for item in monthly_data)

    return render(request, 'reports/reports.html', {
        'category_data': json.dumps(list(category_summary), default=str),
        'monthly_data': json.dumps(monthly_data, default=str),
        'total_expenses_for_month': total_expenses_for_month,
        'amount_change': total_expenses_for_month,
    })

def index(request):
    return render(request, 'index.html')