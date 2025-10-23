from django.shortcuts import render

# Create your views here.
# accounting/views.py

from django.shortcuts import render, redirect
from django.db import transaction
from django.http import HttpResponse
from .models import Client, Worker, Transaction
from django.contrib import messages
from decimal import Decimal  # Используем Decimal для точных расчетов
from django.db.models import Sum # Для расчета суммы
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal # Убедитесь, что Decimal импортирован
from .models import Client, Worker, Transaction, ClientDeposit, WorkerPayout


# Функция для имитации пополнения баланса (нужна только для ввода денег)
def deposit_funds(request, client_id, amount):
    try:
        client = Client.objects.get(id=client_id)
        client.balance += Decimal(amount)
        client.save()
        messages.success(request, f"Баланс клиента {client.full_name} пополнен на {amount}.")
    except Client.DoesNotExist:
        messages.error(request, "Клиент не найден.")
    return redirect('some_redirect_page')  # Перенаправьте на нужную страницу


# Основная логика: оплата сеанса
@transaction.atomic
def process_session_payment(request, client_id, worker_id, session_cost):
    session_cost = Decimal(session_cost)

    try:
        client = Client.objects.select_for_update().get(id=client_id)
        worker = Worker.objects.select_for_update().get(id=worker_id)

        # 1. ПРОВЕРКА БАЛАНСА
        if client.balance < session_cost:
            messages.error(request, f"Ошибка: Недостаточно средств на балансе клиента {client.full_name}.")
            # Откат всех изменений в этой транзакции, если средств недостаточно
            return HttpResponse("Error: Insufficient funds", status=400)

            # 2. АВТОМАТИЧЕСКОЕ СНЯТИЕ С КЛИЕНТА
        client.balance -= session_cost
        client.save()

        # 3. АВТОМАТИЧЕСКОЕ ЗАЧИСЛЕНИЕ СОТРУДНИКУ
        worker.balance += session_cost
        worker.save()

        # 4. ЗАПИСЬ ТРАНЗАКЦИИ
        transaction_record = Transaction.objects.create(
            client=client,
            worker=worker,
            amount=session_cost,
            receipt_printed=False  # Отмечаем, что чек еще не распечатан
        )

        messages.success(request, "Оплата сеанса прошла успешно.")

        # 5. ПЕЧАТЬ ЧЕКА
        # Здесь должна быть логика вызова функции печати (см. раздел 3)
        # Для начала просто имитируем
        print_receipt_for_session(transaction_record)

        return HttpResponse("Payment successful and receipt printed", status=200)

    except Client.DoesNotExist:
        messages.error(request, "Клиент не найден.")
    except Worker.DoesNotExist:
        messages.error(request, "Сотрудник не найден.")
    except Exception as e:
        messages.error(request, f"Произошла непредвиденная ошибка: {e}")
        # Если произошла любая ошибка, @transaction.atomic откатит изменения
        return HttpResponse(f"Server Error: {e}", status=500)

def print_receipt_for_session(transaction_record):
        """Имитация логики печати чека."""

        # 1. ФОРМАТИРОВАНИЕ ДАННЫХ
        receipt_data = f"""
        *** ПСИХОЛОГИЧЕСКИЙ ЦЕНТР ***
        Дата: {transaction_record.date_time.strftime('%Y-%m-%d %H:%M:%S')}
        ---
        Клиент: {transaction_record.client.full_name}
        Сотрудник: {transaction_record.worker.user.get_full_name() or transaction_record.worker.user.username}
        ---
        Услуга: Сеанс психолога
        Сумма: {transaction_record.amount}
        ---
        Баланс клиента: {transaction_record.client.balance}
        ---
        Спасибо!
        """

        # 2. ОТПРАВКА НА ПРИНТЕР
        # Если вы используете python-escpos:
        # printer = Escpos(device='/dev/usb/lp0')
        # printer.text(receipt_data)
        # printer.cut()

        # Для целей разработки просто печатаем в консоль:
        print("\n" + "=" * 40)
        print("--- ПЕЧАТЬ ЧЕКА ---")
        print(receipt_data)
        print("=" * 40 + "\n")

        # 3. Обновление статуса в базе
        transaction_record.receipt_printed = True
        transaction_record.save()

        def dashboard(request):

            if request.method == 'POST':
                action_type = request.POST.get('action_type')

                # --- 1. Логика ПОПОЛНЕНИЯ БАЛАНСА (Обновлено) ---
                if action_type == 'deposit':
                    try:
                        client_id = request.POST.get('client_id')
                        amount_str = request.POST.get('amount')

                        if not client_id or not amount_str or Decimal(amount_str) <= 0:
                            messages.error(request, "Ошибка пополнения: Клиент не выбран или сумма некорректна.")
                            return redirect('dashboard')

                        client = Client.objects.get(id=client_id)
                        amount = Decimal(amount_str)

                        # Используем транзакцию для безопасности
                        with transaction.atomic():
                            client.balance += amount
                            client.save()
                            # СОЗДАЕМ ЗАПИСЬ О ПОПОЛНЕНИИ
                            ClientDeposit.objects.create(client=client, amount=amount)

                        messages.success(request, f"Баланс клиента {client.full_name} успешно пополнен на {amount}.")

                    except Client.DoesNotExist:
                        messages.error(request, "Ошибка: Клиент не найден.")
                    except Exception as e:
                        messages.error(request, f"Ошибка пополнения: {e}")

                # --- 2. Логика ОПЛАТЫ СЕАНСА (Без изменений) ---
                elif action_type == 'process_session':
                    # ... (эта часть логики остается такой же, как была) ...
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
                                messages.error(request,
                                               f"Ошибка: Недостаточно средств на балансе клиента {client.full_name}.")
                                return redirect('dashboard')

                            client.balance -= session_cost
                            client.save()

                            worker.balance += session_cost
                            worker.save()

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

                # --- 3. НОВАЯ ЛОГИКА: ВЫПЛАТА СОТРУДНИКУ ---
                elif action_type == 'payout':
                    try:
                        worker_id = request.POST.get('worker_id')
                        amount_str = request.POST.get('amount')

                        if not worker_id or not amount_str or Decimal(amount_str) <= 0:
                            messages.error(request, "Ошибка выплаты: Сотрудник не выбран или сумма некорректна.")
                            return redirect('dashboard')

                        amount = Decimal(amount_str)

                        with transaction.atomic():
                            worker = Worker.objects.select_for_update().get(id=worker_id)

                            # Проверка, хватает ли у сотрудника денег на балансе
                            if worker.balance < amount:
                                messages.error(request,
                                               f"Ошибка: На балансе сотрудника {worker.user.username} недостаточно средств для выплаты.")
                                return redirect('dashboard')

                            # Снимаем деньги с баланса сотрудника
                            worker.balance -= amount
                            worker.save()

                            # СОЗДАЕМ ЗАПИСЬ О ВЫПЛАТЕ
                            WorkerPayout.objects.create(worker=worker, amount=amount)

                        messages.success(request,
                                         f"Выплата сотруднику {worker.user.username} на сумму {amount} успешно проведена.")

                    except Worker.DoesNotExist:
                        messages.error(request, "Ошибка: Сотрудник не найден.")
                    except Exception as e:
                        messages.error(request, f"Ошибка выплаты: {e}")

                return redirect('dashboard')

                # --- GET-запрос (без изменений) ---
            else:
                clients = Client.objects.all()
                workers = Worker.objects.all()

                context = {
                    'clients': clients,
                    'workers': workers
                }
                return render(request, 'accounting/dashboard.html', context)


def dashboard(request):
    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # --- 1. Логика ПОПОЛНЕНИЯ БАЛАНСА (ОБНОВЛЕНО) ---
        if action_type == 'deposit':
            try:
                client_id = request.POST.get('client_id')
                # Читаем новое имя поля: deposit_amount
                amount_str = request.POST.get('deposit_amount')

                if not client_id or not amount_str or Decimal(amount_str) <= 0:
                    messages.error(request, "Ошибка: Клиент не выбран или сумма пополнения некорректна.")
                    return redirect('dashboard')

                client = Client.objects.get(id=client_id)
                amount = Decimal(amount_str)

                with transaction.atomic():
                    # 1. Изменение баланса
                    client.balance += amount
                    client.save()
                    # 2. Создание записи для отчета
                    ClientDeposit.objects.create(client=client, amount=amount)

                messages.success(request, f"Баланс клиента {client.full_name} успешно пополнен на {amount}.")

            except Client.DoesNotExist:
                messages.error(request, "Ошибка: Клиент не найден.")
            except Exception as e:
                # Отладочный вывод, который поможет, если проблема не в логике, а в данных
                print(f"ОШИБКА ДЕПОЗИТА: {e}")
                messages.error(request, f"Произошла непредвиденная ошибка при пополнении: {e}")

        # --- 2. Логика ОПЛАТЫ СЕАНСА (Без изменений) ---
        elif action_type == 'process_session':
            # ... (логика оплаты сеанса остается как есть) ...
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
                    worker.balance += session_cost
                    worker.save()

                    transaction_record = Transaction.objects.create(
                        client=client,
                        worker=worker,
                        amount=session_cost,
                        receipt_printed=False
                    )

                    messages.success(request, "Оплата сеанса прошла успешно.")
                    # print_receipt_for_session(transaction_record)

            except Client.DoesNotExist:
                messages.error(request, "Ошибка: Клиент не найден.")
            except Worker.DoesNotExist:
                messages.error(request, "Ошибка: Сотрудник не найден.")
            except Exception as e:
                messages.error(request, f"Произошла непредвиденная ошибка: {e}")


        # --- 3. НОВАЯ ЛОГИКА: ВЫПЛАТА СОТРУДНИКУ (ОБНОВЛЕНО) ---
        elif action_type == 'payout':
            try:
                worker_id = request.POST.get('worker_id')
                # Читаем новое имя поля: payout_amount
                amount_str = request.POST.get('payout_amount')

                if not worker_id or not amount_str or Decimal(amount_str) <= 0:
                    messages.error(request, "Ошибка: Сотрудник не выбран или сумма выплаты некорректна.")
                    return redirect('dashboard')

                amount = Decimal(amount_str)

                with transaction.atomic():
                    worker = Worker.objects.select_for_update().get(id=worker_id)

                    if worker.balance < amount:
                        messages.error(request,
                                       f"Ошибка: На балансе сотрудника {worker.user.username} недостаточно средств для выплаты.")
                        return redirect('dashboard')

                    # 1. Изменение баланса
                    worker.balance -= amount
                    worker.save()

                    # 2. Создание записи для отчета
                    WorkerPayout.objects.create(worker=worker, amount=amount)

                messages.success(request,
                                 f"Выплата сотруднику {worker.user.username} на сумму {amount} успешно проведена.")

            except Worker.DoesNotExist:
                messages.error(request, "Ошибка: Сотрудник не найден.")
            except Exception as e:
                # Отладочный вывод, который поможет, если проблема не в логике, а в данных
                print(f"ОШИБКА ВЫПЛАТЫ: {e}")
                messages.error(request, f"Произошла непредвиденная ошибка при выплате: {e}")

        return redirect('dashboard')

        # --- GET-запрос (без изменений) ---
    else:
        clients = Client.objects.all()
        workers = Worker.objects.all()

        context = {
            'clients': clients,
            'workers': workers
        }
        return render(request, 'accounting/dashboard.html', context)


# accounting/views.py

# ... (существующие функции: dashboard, process_session_payment и т.д.) ...

def reports(request):
    """
    Отображает ЕДИНЫЙ отчет по всем финансовым операциям.
    """
    context = {
        'current_filter_desc': 'за все время',
        'start_date_input': '',
        'end_date_input': '',
    }

    # --- 1. Логика фильтрации дат (такая же, как была) ---
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

    # --- 2. Получение данных из 3-х источников ---

    # Базовые QuerySets
    transactions_qs = Transaction.objects.select_related('client', 'worker__user').all()
    deposits_qs = ClientDeposit.objects.select_related('client').all()
    payouts_qs = WorkerPayout.objects.select_related('worker__user').all()

    # Применяем фильтры дат, если они есть
    if start_date and end_date:
        transactions_qs = transactions_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)
        deposits_qs = deposits_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)
        payouts_qs = payouts_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)

    # --- 3. Расчет сводки (Доход = Сеансы) ---
    total_income = transactions_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_payouts = payouts_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_deposits = deposits_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    context['total_income'] = total_income
    context['total_payouts'] = total_payouts
    context['total_deposits'] = total_deposits
    # Чистая прибыль (Доход минус Выплаты)
    context['net_profit'] = total_income - total_payouts

    # --- 4. Создание ЕДИНОГО списка событий ---
    unified_log = []

    for tx in transactions_qs:
        unified_log.append({
            'date_time': tx.date_time,
            'event_type': 'Сеанс (Доход)',
            'description': f"{tx.client.full_name} -> {tx.worker.user.username}",
            'amount_positive': tx.amount,
            'amount_negative': None,
            'css_class': 'income'  # Для стилизации
        })

    for deposit in deposits_qs:
        unified_log.append({
            'date_time': deposit.date_time,
            'event_type': 'Пополнение',
            'description': f"Клиент: {deposit.client.full_name}",
            'amount_positive': deposit.amount,
            'amount_negative': None,
            'css_class': 'deposit'  # Для стилизации
        })

    for payout in payouts_qs:
        unified_log.append({
            'date_time': payout.date_time,
            'event_type': 'Выплата (Расход)',
            'description': f"Сотрудник: {payout.worker.user.username}",
            'amount_positive': None,
            'amount_negative': payout.amount,
            'css_class': 'payout'  # Для стилизации
        })

    # --- 5. Сортировка единого списка по дате (от новых к старым) ---
    context['unified_log'] = sorted(unified_log, key=lambda e: e['date_time'], reverse=True)

    return render(request, 'accounting/reports.html', context)