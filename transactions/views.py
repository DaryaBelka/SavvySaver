import json
import os
import pdfplumber
import re
from itertools import accumulate
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
from django.db.models.functions import Trunc
from django.contrib.auth.decorators import login_required
from .models import Transaction, FinancialGoal
from .forms import TransactionForm
from decimal import Decimal
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)
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

def handle_uploaded_file(uploaded_file, user):
    fs = FileSystemStorage()
    filename = fs.save(uploaded_file.name, uploaded_file)
    file_path = fs.path(filename)

    try:
        if uploaded_file.name.lower().endswith('.pdf'):
            transactions = extract_transactions_from_pdf(file_path)

            for transaction_data in transactions:
                Transaction.objects.create(
                    user=user,
                    title=transaction_data.get("title"),
                    amount=transaction_data.get("amount"),
                    date=transaction_data.get("date"),
                    category=transaction_data.get("category")
                )
    except Exception:
        pass
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def extract_transactions_from_pdf(file_path):
    transactions = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    bank_type = identify_bank(text)
                    transactions.extend(parse_pdf_text(text, bank_type))
    except Exception:
        pass
    
    return transactions

def identify_bank(text):
    text = text.lower()
    header = text[:500]  
    
    if "ing bank śląski" in text or "www.ing.pl" in text:  
        return "ing"
    elif "mbank" in header or "www.mbank.pl" in text or "mBankS.A." in text.replace(" ", ""): 
        return "mbank"
    elif "bank pekao s.a." in header or "pekao s.a." in header:
        return "pekao"
    elif "santander" in text[-500:]:
        return "santander"
    elif "revolut" in header or "revolt21" in header:
        return "revolut"
    elif "pko bp" in header or "powszechna kasa oszczędności" in header or "pkobp" in header:
        return "pko"
    elif "alior bank" in header or "alior" in header or "potwierdzenie wykonania przelewu krajowego" in text or "potwierdzenie transakcji kartą debetową" in text:
        return "alior"
    elif "millennium" in header:
        return "millennium"
    else:
        return "unknown"

def sanitize_pdf_text(text):     # delete "NUMER RACHUNKU ODBIORCY" and "TYTUŁ" in Santander.
    text = re.sub(r'NUMER RACHUNKU ODBIORCY\s+[\d\s\-]+', '', text)
    text = re.sub(r'TYTUŁ\s+', '', text)
    return text.strip()

def parse_pdf_text(text, bank_type):
    transactions = []
    
    title_match = None
    amount_match = None
    date_match = None
    recipient_match = None
    address_match = None

    title = None 

    if bank_type == "santander":
        text = sanitize_pdf_text(text)
        title_match = re.search(r'DANE ODBIORCY\s*([\w\.\-\s]+)', text)
        amount_match = re.search(r'KWOTA\s*(-?\d+,\d{2}) PLN', text)
        date_match = re.search(r'DATA OPERACJI\s*(\d{2}-\d{2}-\d{4})', text)
    
    elif bank_type == "millennium":
        if "ZAKUP - FIZ. UŻYCIE KARTY" in text:
            amount_match = re.search(r'Kwota transakcji\s*([\d,\.]+) PLN', text)
            date_match = re.search(r'Data transakcji\s*(\d{4}-\d{2}-\d{2})', text)
            title_match = re.search(r'Tytuł\s*(.+)', text)

            if title_match:
                title = title_match.group(1).strip()
            else:
                title = "Zakup kartą"

        elif "PRZELEW" in text:
            amount_match = re.search(r'Kwota\s*([\d,\.]+) PLN', text)
            date_match = re.search(r'Data transakcji\s*(\d{4}-\d{2}-\d{2})', text)
            title_match = re.search(r'Tytuł\s*(.+)', text)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title = "Przelew"

    elif bank_type == "pekao":
        amount_match = re.search(r'Kwota operacji:\s*(-?\d+,\d{2}) PLN', text)
        date_match = re.search(r'Data księgowania:\s*(\d{2}/\d{2}/\d{4})', text)
        title_match = re.search(r'Tytułem:\s*(.*?)(?=\n(?:Data księgowania|Kwota operacji|$))', text, re.DOTALL)
        recipient_match = re.search(r'Odbiorca:\s*(.*?)(?:\n|$)', text, re.DOTALL)

    elif bank_type == "revolut":
        if "Potwierdzenie przelewu" in text:
            amount_match = re.search(r'Kwota\s*([\d,\.]+) PLN', text)
            date_match = re.search(r'Data waluty\s*(\d{4}-\d{2}-\d{2})', text)
            recipient_match = re.search(r'Imię i nazwisko/nazwa\s*(.+)', text, re.DOTALL)
            title = "Przelew"
        else:
            matches = re.findall(r'(\d{1,2} \w+ \d{4}) ([\w\s]+) ([\d,\.]+) PLN', text)
            for match in matches:
                date_str, title, amount = match
                date_obj = parse_date(date_str, bank_type)
                transactions.append({
                    "title": title.strip(),
                    "amount": abs(float(amount.replace(',', '.'))),
                    "date": date_obj,
                    "category": classify_transaction(title)
                })
            return transactions

    elif bank_type == "pko":
        title_match = re.search(r'Tytuł\s*:\s*(.+)', text)
        amount_match = re.search(r'Kwota\s*(-?\d+[\.,]\d{2})\s*PLN', text)
        date_match = re.search(r'Data\s*operacji\s*:?\s*(\d{4}-\d{2}-\d{2})', text)
        address_match = re.search(r'Adres:\s*([A-Z0-9\s\.\-]+)(?:\s+(?:Data|Kraj|Miasto|Lokalizacja))?', text)

    elif bank_type == "ing":
        amount_match = re.search(r'Nr transakcji.*?([\d,\.]+) PLN', text)
        date_match = re.search(r'Data transakcji:\s*(\d{2}\.\d{2}\.\d{4})', text) 
        
        if "Przelew" in text:
            title = "Przelew "
        elif "Płatność kartą" in text:
            recipient_match = re.search(r'Nazwa i adres odbiorcy:\s*(.+)', text)
            title = recipient_match.group(1).strip() if recipient_match else "Nieznany tytuł"
        else:
            title = "Nieznany tytuł"

    elif bank_type == "mbank":
        if "OPERACJI KARTOWEJ" in text or "ZAKUPPRZYUŻYCIUKARTY" in text:
            amount_match = re.search(r'KwotaoperacjiwPLN:\s*(-?[\d,\.]+)', text) 
            date_match = re.search(r'Datatransakcji:\s*(\d{4}-\d{2}-\d{2})', text) 
            title_match = re.search(r'Miejscetransakcji:\s*(.+)', text) 

            title = title_match.group(1).strip() if title_match else "Zakup kartą"

        elif "PRZELEWZEWNĘTRZNYWYCHODZĄCY" in text or "POTWIERDZENIE WYKONANIA PRZELEWU" in text or "PRZELEW" in text:
            amount_match = re.search(r'Kwotaprzelewu:\s*([\d,\.]+)PLN', text)  
            date_match = re.search(r'Dataoperacji:\s*(\d{4}-\d{2}-\d{2})', text)  
            title_match = re.search(r'Tytułoperacji:\s*(.+)', text)  

            title = title_match.group(1).strip() if title_match else "Przelew"

            if "PRZELEWŚRODKÓW" in text:
                title = "Przelew"
            

    elif bank_type == "alior":
        if "Potwierdzenie wykonania przelewu krajowego" in text:
            amount_match = re.search(r'Kwota\s*([\d,\.]+) PLN', text)
            date_match = re.search(r'Data transakcji\s*(\d{4}-\d{2}-\d{2})', text)
            title_match = re.search(r'Tytuł płatności\s*(.+)', text)

            if title_match:
                title = title_match.group(1).strip()
            else:
                title = "Przelew"

        elif "Potwierdzenie transakcji kartą debetową" in text:
            amount_match = re.search(r'Kwota w walucie oryginalnej transakcji\s*([\d,\.]+) PLN', text)
            date_match = re.search(r'Data transakcji\s*(\d{4}-\d{2}-\d{2})', text)
            title_match = re.search(r'Miejsce operacji\s*(.+)', text)

            if title_match:
                title = title_match.group(1).strip()
            else:
                title = "Nieznany tytuł"

    if title is None:
        if bank_type == "pekao":
            if title_match:
                title = title_match.group(1).strip()
            elif recipient_match:
                title = recipient_match.group(1).strip()
            else:
                title = "Przelew bankowy"

        elif bank_type == "santander":
            if title_match:
                title = title_match.group(1).strip()

        elif bank_type == "pko":
            if address_match:
                title = address_match.group(1).rstrip("D").strip()
            elif title_match:
                title = title_match.group(1).rstrip("D").strip()

    if not title:
        title = "Nieznany tytuł"

    if amount_match and date_match:
        date_obj = parse_date(date_match.group(1), bank_type)

        if date_obj is None:
            return transactions

        amount = abs(float(amount_match.group(1).replace(',', '.')))
        transactions.append({
            "title": title,
            "amount": amount,
            "date": date_obj,
            "category": classify_transaction(title)
        })

    return transactions

def parse_date(date_str, bank_type):
    try:
        if bank_type == "santander":
            return datetime.strptime(date_str, '%d-%m-%Y').date()
        elif bank_type == "revolut":
            if "-" in date_str:  
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            else:  
                months = {
                    "sty": "01", "lut": "02", "mar": "03", "kwi": "04",
                    "maj": "05", "cze": "06", "lip": "07", "sie": "08",
                    "wrz": "09", "paź": "10", "lis": "11", "gru": "12"
                }
                day, month_str, year = date_str.split()
                month = months.get(month_str[:3].lower(), "01")
                return datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').date()
        elif bank_type == "pekao":
            return datetime.strptime(date_str, '%d/%m/%Y').date() 
        elif bank_type in ["millennium", "pko", "alior"]:
            return datetime.strptime(date_str, '%Y-%m-%d').date() 
        elif bank_type == "ing":
            return datetime.strptime(date_str, '%d.%m.%Y').date()  
        elif bank_type == "mbank":
            if "." in date_str:
                return datetime.strptime(date_str, '%d.%m.%Y').date() 
            elif "-" in date_str:
                return datetime.strptime(date_str, '%Y-%m-%d').date()  
    except ValueError as e:
        print(f"Error parsing date {date_str} for {bank_type}: {e}")
    return None

def classify_transaction(title):
    title = title.lower()

    transport_keywords = [
        "jakdojade", "uber", "mpk", "bolt", "pkp", "flixbus", "koleje", "tramwaj", "autobus", 
        "taxi", "blablacar", "shell", "orlen", "bp", "lotnisko", "paliwo", "opłata drogowa"
    ]
    restaurants_keywords = [
        "restaurant", "cafe", "restauracja", "kawiarnia", "mcdonalds", "kfc", "burger king", 
        "starbucks", "subway", "pizzeria", "bar mleczny", "sushi", "grill", "pub", "bistro"
    ]
    health_keywords = [
        "apteka", "pharmacy", "hebe", "rossmann", "zdrowie", "medicover", "luxmed", 
        "lekarz", "dentysta", "stomatolog", "okulista", "diagnostyka", "rehabilitacja"
    ]
    groceries_keywords = [
        "lewiatan", "carrefour", "sklep", "market", "zabka", "biedronka", "lidl", "auchan", 
        "delikatesy", "spożywczy"
    ]
    shopping_keywords = [
        "allegro", "amazon", "zalando", "decathlon", "ikea", "ccc", "eobuwie", "media markt", 
        "rtv euro agd", "empik", "smyk", "moda", "odzież", "buty", "zakupy", "galeria", "sklep internetowy"
    ]
    utilities_keywords = [
        "energa", "tauron", "pgnig", "veolia", "opłata", "czynsz", "gaz", "prąd", 
        "woda", "internet", "abonament", "tv", "play", "orange", "t-mobile", "plus"
    ]
    cash_keywords = [
        "bankomat", "wypłata", "gotówka", "pobrano", "cash", "wpłatomat"
    ]
    transfers_keywords = [
        "przelew", "blik", "zwrot", "rachunek", "transakcja", "płatność", "opłata bankowa", "przekaz", "oddo"
    ]

    if any(word in title for word in transport_keywords):
        return "transport"
    if any(word in title for word in restaurants_keywords):
        return "restaurants"
    if any(word in title for word in health_keywords):
        return "health"
    if any(word in title for word in groceries_keywords):
        return "groceries"
    if any(word in title for word in shopping_keywords):
        return "shopping"
    if any(word in title for word in utilities_keywords):
        return "media"
    if any(word in title for word in cash_keywords):
        return "cash"
    if any(word in title for word in transfers_keywords):
        return "transfers"
    return "general"

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
        'total_expenses_for_month': round(total_expenses_for_month, 2),
        'amount_change': round(total_expenses_for_month, 2),
    })

ADVICE_LIST = [
    "Save a small amount today - it's a step towards your big goal!",
    "Avoid unnecessary purchases – your goal is worth it!",
    "Plan your budget for the week – tracking expenses helps you reach your goal faster.",
    "Follow the 24-hour rule before making big purchases – you might not need it!",
    "Make coffee at home instead of buying it every day – the savings add up!",
    "Avoid impulse buying – always make a shopping list and stick to it.",
    "Review your subscriptions – cancel any you don't use.",
    "Cook meals at home instead of eating out – it's healthier and cheaper.",
    "Compare prices online before making purchases to find the best deals.",
    "Set a weekly spending limit and challenge yourself to stick to it.",
    "Track your expenses daily to stay aware of your spending habits.",
    "Avoid shopping when you're bored – it often leads to unnecessary spending.",
    "Turn off lights and appliances when not in use to save on electricity.",
    "Plan your grocery shopping around discounts and deals.",
    "Create a wishlist for big purchases and revisit it after a month.",
    "Borrow or rent items you rarely need instead of buying them.",
    "Review your financial goals regularly to stay motivated and adjust as needed.",
    "Avoid online shopping late at night when decision-making is less rational.",
    "Pay your bills on time to avoid late fees and extra charges.",
    "Track your impulse purchases and review them monthly to see how much you could save.",
    "Use cash instead of cards for daily expenses – it helps control spending better.",
    "Buy seasonal items off-season (e.g., winter clothes in summer) to get better deals.",
    "Avoid lifestyle inflation – don’t increase spending just because you earn more.",
    "Review and cancel automatic payments for unused apps, memberships, or services.",
    "Try the 50/30/20 budgeting rule: 50% for needs, 30% for wants, 20% for savings.",
    "Invest in quality over quantity – durable items save money in the long run.",
    "Set up separate bank accounts for savings, bills, and daily spending.",
    "Learn basic financial literacy – read books or follow reliable financial blogs.",
    "Instead of buying new clothes often, try mix-and-match outfits to refresh your style.",
    "Use cashback and rewards programs wisely, but avoid overspending to earn points.",
    "Always compare prices from different stores before making a purchase.",
]

@login_required
def advice_view(request):
    user = request.user
    goal, created = FinancialGoal.objects.get_or_create(
        user=user,
        defaults={'goal_name': "New Goal", 'target_amount': Decimal('1000.00'), 'saved_amount': Decimal('0.00')}
    )

    if created:
        messages.info(request, "A new financial goal has been created for you!")

    if request.method == 'POST':
        if 'update_goal' in request.POST:
            new_goal_name = request.POST.get('goal_name', goal.goal_name)
            new_target_amount = request.POST.get('target_amount')

            try:
                new_target_amount = Decimal(new_target_amount) if new_target_amount else goal.target_amount
            except ValueError:
                new_target_amount = goal.target_amount

            if goal.goal_name != new_goal_name or goal.target_amount != new_target_amount:
                goal.saved_amount = Decimal('0.00')

            goal.goal_name = new_goal_name
            goal.target_amount = new_target_amount
            goal.save()

        elif 'add_savings' in request.POST:
            savings = request.POST.get('savings')
            try:
                additional_savings = Decimal(savings) if savings else Decimal('0.00')
                remaining_amount = goal.target_amount - goal.saved_amount

                if additional_savings > 0 and additional_savings <= remaining_amount:
                    goal.saved_amount += additional_savings
                    goal.save()
            except ValueError:
                pass

        elif 'withdraw_savings' in request.POST:
            withdrawal = request.POST.get('withdrawal')
            try:
                withdrawal_amount = Decimal(withdrawal) if withdrawal else Decimal('0.00')
                if withdrawal_amount > 0 and withdrawal_amount <= goal.saved_amount:
                    goal.saved_amount -= withdrawal_amount
                    goal.save()
            except ValueError:
                pass

    progress = goal.progress_percentage() if goal.target_amount > Decimal('0.00') else Decimal('0.00')

    today_day = datetime.today().day

    if today_day <= len(ADVICE_LIST):
        daily_advice = ADVICE_LIST[today_day - 1] 
    else:
        daily_advice = ADVICE_LIST[-1]   

    return render(request, 'advice/advice.html', {
        'goal': goal,
        'progress': float(progress),
        'advice': daily_advice,
    })

def index(request):
    return render(request, 'index.html')

