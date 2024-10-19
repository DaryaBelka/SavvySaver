import csv
import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from .models import Transaction
from .forms import TransactionForm  
from django.db.models import Sum

def transaction_list(request):
    category = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    transactions = Transaction.objects.all()

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
    })

def create_transaction(request):
    if request.method == 'POST':
        if 'file' in request.FILES:  
            uploaded_file = request.FILES['file']
            handle_uploaded_file(uploaded_file)  
            return redirect('transaction_list')
        else:  
            form = TransactionForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('transaction_list')  
    else:
        form = TransactionForm()
    
    return render(request, 'transactions/create_transaction.html', {'form': form})

def edit_transaction(request, id):
    
    transaction = get_object_or_404(Transaction, id=id)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction)
    
    return render(request, 'transactions/edit_transaction.html', {'form': form, 'transaction': transaction})

def delete_transaction(request, id):
    transaction = get_object_or_404(Transaction, id=id)
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

def index(request):
    return render(request, 'transactions/index.html')
