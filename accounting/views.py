from django.db.models import Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Client, Worker, Transaction, ClientDeposit
from django.contrib.auth.decorators import login_required, user_passes_test
from .receipt_utils import generate_pdf_receipt, print_to_thermal_printer, generate_receipt_response

def deposit_funds(request, client_id, amount):
    try:
        client = Client.objects.get(id=client_id)
        client.balance += Decimal(amount)
        client.save()
        messages.success(request, f"Баланс клиента {client.full_name} пополнен на {amount}.")
    except Client.DoesNotExist:
        messages.error(request, "Клиент не найден.")
    return redirect('some_redirect_page')


@transaction.atomic
def process_session_payment(request, client_id, worker_id, session_cost):
    session_cost = Decimal(session_cost)

    try:
        client = Client.objects.select_for_update().get(id=client_id)
        worker = Worker.objects.get(id=worker_id)

        if client.balance < session_cost:
            messages.error(request, f"Ошибка: Недостаточно средств на балансе клиента {client.full_name}.")
            return HttpResponse("Error: Insufficient funds", status=400)

            # taking money from balance of a client
        client.balance -= session_cost
        client.save()
        transaction_record = Transaction.objects.create(
            client=client,
            worker=worker,
            amount=session_cost,
            receipt_printed=False
        )

        messages.success(request, "Оплата сеанса прошла успешно.")

        # not implemented yet
        print_receipt_for_session(transaction_record)

        return HttpResponse("Payment successful and receipt printed", status=200)

    except Client.DoesNotExist:
        messages.error(request, "Клиент не найден.")
    except Worker.DoesNotExist:
        messages.error(request, "Сотрудник не найден.")
    except Exception as e:
        messages.error(request, f"Произошла непредвиденная ошибка: {e}")
        return HttpResponse(f"Server Error: {e}", status=500)

def print_receipt_for_session(transaction_record):
    """
    Печатает чек для транзакции на принтер и обновляет статус
    """
    try:
        # Пытаемся напечатать на термопринтер
        print_success = print_to_thermal_printer(transaction_record)
        
        if not print_success:
            # Если печать на принтер не удалась, выводим в консоль для отладки
            receipt_data = f"""
*** ПСИХОЛОГИЧЕСКИЙ ЦЕНТР ***
Дата: {transaction_record.date_time.strftime('%Y-%m-%d %H:%M:%S')}
---
Клиент: {transaction_record.client.full_name}
Сотрудник: {transaction_record.worker.user.get_full_name() or transaction_record.worker.user.username}
---
Услуга: Сеанс психолога
Сумма: {transaction_record.amount} AZN
---
Баланс клиента: {transaction_record.client.balance} AZN
---
Спасибо!
"""
            print("\n" + "=" * 40)
            print("--- ПЕЧАТЬ ЧЕКА ---")
            print(receipt_data)
            print("=" * 40 + "\n")
        
        transaction_record.receipt_printed = True
        transaction_record.save()
        
    except Exception as e:
        print(f"Ошибка при печати чека: {e}")
        # Не помечаем как напечатанный, если произошла ошибка


def is_staff_user(user):
    return user.is_staff

@login_required(login_url='/admin/login/') # Перенаправит на страницу логина админки
@user_passes_test(is_staff_user, login_url='/admin/login/')
def dashboard(request):
    client_q = request.GET.get('client_q', '').strip()
    worker_q = request.GET.get('worker_q', '').strip()

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # depositing money to balance
        if action_type == 'deposit':
            try:
                client_id = request.POST.get('client_id')
                amount_str = request.POST.get('deposit_amount')

                if not client_id or not amount_str or Decimal(amount_str) <= 0:
                    messages.error(request, "Ошибка: Клиент не выбран или сумма пополнения некорректна.")
                    return redirect('dashboard')

                client = Client.objects.get(id=client_id)
                amount = Decimal(amount_str)

                with transaction.atomic():
                    client.balance += amount
                    client.save()
                    ClientDeposit.objects.create(client=client, amount=amount)

                messages.success(request, f"Баланс клиента {client.full_name} успешно пополнен на {amount}.")

            except Client.DoesNotExist:
                messages.error(request, "Ошибка: Клиент не найден.")
            except Exception as e:
                print(f"ОШИБКА ДЕПОЗИТА: {e}")
                messages.error(request, f"Произошла непредвиденная ошибка при пополнении: {e}")

        elif action_type == 'process_session':
            try:
                client_id = request.POST.get('client_id')
                worker_id = request.POST.get('worker_id')
                cost_str = request.POST.get('session_cost')

                if not client_id or not worker_id or not cost_str or Decimal(cost_str) <= 0:
                    messages.error(request, "Ошибка сеанса: Данные некорректны.")
                    return redirect('dashboard')

                session_cost = Decimal(cost_str)

                with transaction.atomic():
                    client = Client.objects.select_for_update().get(id=client_id)
                    worker = Worker.objects.select_for_update().get(id=worker_id)

                    if client.balance < session_cost:
                        messages.error(request, f"Ошибка: Недостаточно средств на балансе клиента {client.full_name}.")
                        return redirect('dashboard')

                    client.balance -= session_cost
                    client.save()


                    transaction_record = Transaction.objects.create(
                        client=client,
                        worker=worker,
                        amount=session_cost,
                        receipt_printed=False
                    )

                    messages.success(request, "Оплата сеанса прошла успешно.")
                    print_receipt_for_session(transaction_record)

            except Client.DoesNotExist:
                messages.error(request, "Ошибка: Клиент не найден.")
            except Worker.DoesNotExist:
                messages.error(request, "Ошибка: Сотрудник не найден.")
            except Exception as e:
                messages.error(request, f"Произошла непредвиденная ошибка: {e}")


        # temprorary removed this functionality
        elif action_type == 'payout':
            messages.error(request, "Операция выплаты сотруднику отключена, так как баланс сотрудника убран.")
            return redirect(f"{request.path}?client_q={client_q}&worker_q={worker_q}")
        return redirect(f"{request.path}?client_q={client_q}&worker_q={worker_q}")
    else:
        clients_qs = Client.objects.all()
        workers_qs = Worker.objects.all()
        recent_transactions = Transaction.objects.select_related('client', 'worker__user').order_by('-date_time')[:20]

        if client_q:
            clients_qs = clients_qs.filter(full_name__icontains=client_q)
        if worker_q:
            workers_qs = workers_qs.filter(
                Q(user__username__icontains=worker_q) |  # Поиск по логину
                Q(user__first_name__icontains=worker_q) |  # Поиск по имени
                Q(user__last_name__icontains=worker_q)  # Поиск по фамилии
            )

        context = {
            'clients': clients_qs,
            'workers': workers_qs,
            'recent_transactions': recent_transactions,
            'client_q': client_q,
            'worker_q': worker_q,
        }
        return render(request, 'accounting/dashboard.html', context)

@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def reports(request):
    # all reports
    context = {
        'current_filter_desc': 'за все время',
        'start_date_input': '',
        'end_date_input': '',
    }

    # date filtration
    now = timezone.now().date()
    start_date = None
    end_date = None
    preset = request.GET.get('preset')

    if preset:
        if preset == 'today':
            start_date = now
            end_date = now
            context['current_filter_desc'] = 'за сегодня'
        elif preset == 'week':
            start_date = now - timedelta(days=now.weekday())
            end_date = now
            context['current_filter_desc'] = 'за текущую неделю'
        elif preset == 'month':
            start_date = now.replace(day=1)
            end_date = now
            context['current_filter_desc'] = 'за текущий месяц'

    custom_start_str = request.GET.get('start_date')
    custom_end_str = request.GET.get('end_date')

    if custom_start_str and custom_end_str:
        try:
            start_date = datetime.strptime(custom_start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(custom_end_str, '%Y-%m-%d').date()
            context['current_filter_desc'] = f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"
            context['start_date_input'] = custom_start_str
            context['end_date_input'] = custom_end_str
        except ValueError:
            messages.error(request, "Неверный формат даты. Используйте ГГГГ-ММ-ДД.")

    # basic QuerySets
    transactions_qs = Transaction.objects.select_related('client', 'worker__user').all()
    deposits_qs = ClientDeposit.objects.select_related('client').all()
    if start_date and end_date:
        transactions_qs = transactions_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)
        deposits_qs = deposits_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)


    selected_client_id = request.GET.get('client_id')
    selected_worker_id = request.GET.get('worker_id')

    if selected_client_id:
        try:
            transactions_qs = transactions_qs.filter(client_id=int(selected_client_id))
            deposits_qs = deposits_qs.filter(client_id=int(selected_client_id))
        except ValueError:
            messages.error(request, "Неверный идентификатор клиента.")

    if selected_worker_id:
        try:
            transactions_qs = transactions_qs.filter(worker_id=int(selected_worker_id))
        except ValueError:
            messages.error(request, "Неверный идентификатор сотрудника.")

    total_income = transactions_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_deposits = deposits_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    context['total_income'] = total_income
    context['total_payouts'] = Decimal('0.00')
    context['total_deposits'] = total_deposits
    context['net_profit'] = total_income


    unified_log = []

    for tx in transactions_qs:
        unified_log.append({
            'date_time': tx.date_time,
            'event_type': 'Сеанс (Доход)',
            'description': f"{tx.client.full_name} -> {tx.worker.user.username}",
            'amount_positive': tx.amount,
            'amount_negative': None,
            'css_class': 'income'
        })

    for deposit in deposits_qs:
        unified_log.append({
            'date_time': deposit.date_time,
            'event_type': 'Пополнение',
            'description': f"Клиент: {deposit.client.full_name}",
            'amount_positive': deposit.amount,
            'amount_negative': None,
            'css_class': 'deposit'
        })



    context['unified_log'] = sorted(unified_log, key=lambda e: e['date_time'], reverse=True)


    context['clients'] = Client.objects.all()
    context['workers'] = Worker.objects.select_related('user').all()
    context['selected_client_id'] = selected_client_id or ''
    context['selected_worker_id'] = selected_worker_id or ''

    return render(request, 'accounting/reports.html', context)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def print_receipt(request, transaction_id):
    """
    Печатает чек на принтер
    """
    transaction_record = get_object_or_404(Transaction.objects.select_related('client', 'worker__user'), id=transaction_id)
    try:
        print_receipt_for_session(transaction_record)
        messages.success(request, "Чек успешно напечатан.")
    except Exception as e:
        messages.error(request, f"Не удалось напечатать чек: {e}")
    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def view_receipt(request, transaction_id, format='html'):
    """
    Просмотр чека в браузере (HTML или PDF)
    """
    transaction_record = get_object_or_404(
        Transaction.objects.select_related('client', 'worker__user'), 
        id=transaction_id
    )
    
    if format == 'pdf':
        return generate_receipt_response(transaction_record, format='pdf', request=request)
    else:
        return generate_receipt_response(transaction_record, format='html', request=request)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def download_receipt_pdf(request, transaction_id):
    """
    Скачивание чека в формате PDF
    """
    transaction_record = get_object_or_404(
        Transaction.objects.select_related('client', 'worker__user'), 
        id=transaction_id
    )
    
    pdf = generate_pdf_receipt(transaction_record)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{transaction_record.id}.pdf"'
    return response