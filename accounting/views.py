from django.db.models import Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, connection
from django.db.utils import ProgrammingError
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
import os
from .models import Client, Worker, Transaction, ClientDeposit, ClientBalanceAdjustment
from django.contrib.auth.decorators import login_required, user_passes_test
from .receipt_utils import generate_pdf_receipt, print_to_thermal_printer, generate_receipt_response, print_receipt_for_deposit
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _has_new_client_fields():
    """Проверяет, существуют ли новые поля в таблице Client"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='accounting_client' AND column_name='date_of_birth'
            """)
            return cursor.fetchone() is not None
    except Exception:
        return False

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
def process_session_payment(request, client_id, worker_id, session_cost, lessons_count=0):
    session_cost = Decimal(session_cost)
    lessons_count = int(lessons_count or 0)

    try:
        client = Client.objects.select_for_update().get(id=client_id)
        worker = Worker.objects.get(id=worker_id)

        if lessons_count < 0:
            messages.error(request, "Error: Lessons count cannot be negative.")
            return HttpResponse("Error: Invalid lessons count", status=400)

        if client.balance < session_cost:
            messages.error(request, f"????????????: ???????????????????????? ?????????????? ???? ?????????????? ?????????????? {client.full_name}.")
            return HttpResponse("Error: Insufficient funds", status=400)

        if client.lessons_balance < lessons_count:
            messages.error(request, f"Error: Client {client.full_name} has insufficient lessons.")
            return HttpResponse("Error: Insufficient lessons", status=400)

        # taking money from balance of a client
        client.balance -= session_cost
        client.lessons_balance -= lessons_count
        client.save()
        transaction_record = Transaction.objects.create(
            client=client,
            worker=worker,
            amount=session_cost,
            receipt_printed=False,
            lessons_count=lessons_count,
            balance_after=client.balance,
            lessons_balance_after=client.lessons_balance
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
            balance_display = transaction_record.balance_after if transaction_record.balance_after is not None else transaction_record.client.balance
            lessons_balance_display = transaction_record.lessons_balance_after if transaction_record.lessons_balance_after is not None else transaction_record.client.lessons_balance
            receipt_data = f"""
*** ПСИХОЛОГИЧЕСКИЙ ЦЕНТР ***
Дата: {transaction_record.date_time.strftime('%Y-%m-%d %H:%M:%S')}
---
Клиент: {transaction_record.client.full_name}
Сотрудник: {transaction_record.worker.user.get_full_name() or transaction_record.worker.user.username}
---
Услуга: Сеанс психолога
Сумма: {transaction_record.amount} AZN
Уроки: {transaction_record.lessons_count}
---
Баланс клиента: {balance_display} AZN
Баланс уроков: {lessons_balance_display}
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


def logout_user(request):
    """
    Выход из аккаунта из верхней панели.
    """
    if request.method == 'POST':
        logout(request)
        messages.success(request, gettext('You have been logged out.'))
    return redirect('/admin/login/')


def _get_reports_pdf_font_names():
    """
    Возвращает шрифты для PDF с поддержкой азербайджанских символов.
    """
    # Порядок важен: сначала Windows (текущий проект), затем Unix fallback.
    font_candidates = [
        {
            'normal': r'C:\Windows\Fonts\arial.ttf',
            'bold': r'C:\Windows\Fonts\arialbd.ttf',
            'normal_name': 'FleksArial',
            'bold_name': 'FleksArialBold',
        },
        {
            'normal': r'C:\Windows\Fonts\segoeui.ttf',
            'bold': r'C:\Windows\Fonts\segoeuib.ttf',
            'normal_name': 'FleksSegoeUI',
            'bold_name': 'FleksSegoeUIBold',
        },
        {
            'normal': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            'bold': '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            'normal_name': 'FleksDejaVuSans',
            'bold_name': 'FleksDejaVuSansBold',
        },
    ]

    for candidate in font_candidates:
        normal_path = candidate['normal']
        bold_path = candidate['bold']
        normal_name = candidate['normal_name']
        bold_name = candidate['bold_name']

        if not os.path.exists(normal_path):
            continue

        try:
            registered_fonts = pdfmetrics.getRegisteredFontNames()
            if normal_name not in registered_fonts:
                pdfmetrics.registerFont(TTFont(normal_name, normal_path))

            if os.path.exists(bold_path):
                if bold_name not in registered_fonts:
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                return normal_name, bold_name

            return normal_name, normal_name
        except Exception:
            continue

    # Fallback: если TTF не удалось загрузить.
    return 'Helvetica', 'Helvetica-Bold'


def _generate_reports_pdf_response(context, as_attachment=False):
    """
    Генерирует PDF-отчет на основе уже подготовленного контекста страницы отчетов.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    normal_font, bold_font = _get_reports_pdf_font_names()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName=bold_font,
        fontSize=15,
        spaceAfter=8,
    )
    normal_style = ParagraphStyle(
        'ReportNormal',
        parent=styles['Normal'],
        fontName=normal_font,
        fontSize=9,
        leading=12,
    )

    story = []
    story.append(Paragraph(gettext('Financial Reports'), title_style))
    story.append(Paragraph(f"{gettext('Period')}: {context.get('current_filter_desc', '')}", normal_style))

    selected_client_name = context.get('selected_client_name')
    selected_worker_name = context.get('selected_worker_name')
    if selected_client_name:
        story.append(Paragraph(f"{gettext('Client')}: {selected_client_name}", normal_style))
    if selected_worker_name:
        story.append(Paragraph(f"{gettext('Worker')}: {selected_worker_name}", normal_style))

    story.append(Paragraph(
        f"{gettext('Generated at')}: {timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')}",
        normal_style,
    ))
    story.append(Spacer(1, 10))

    summary_data = [
        [gettext('Metric'), gettext('Value')],
        [gettext('Total income (Sessions)'), f"{context.get('total_income', Decimal('0.00'))} AZN"],
        [gettext('Client top-ups'), f"{context.get('total_deposits', Decimal('0.00'))} AZN"],
        [gettext('Top-up cancellations'), f"{context.get('total_adjustments', Decimal('0.00'))} AZN"],
    ]

    summary_table = Table(summary_data, colWidths=[220, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), bold_font),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), normal_font),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph(gettext('Operation details'), ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName=bold_font,
        fontSize=12,
        spaceAfter=6,
    )))

    unified_log = context.get('unified_log') or []
    if unified_log:
        rows = [[gettext('Date and time'), gettext('Operation type'), gettext('Description'), gettext('Income (to cash)')]]
        for event in unified_log:
            amount_text = ''
            if event.get('amount_positive') is not None:
                amount_text = f"+ {event['amount_positive']}"
            elif event.get('amount_negative') is not None:
                amount_text = f"- {event['amount_negative']}"

            rows.append([
                event['date_time'].strftime('%d.%m.%Y %H:%M'),
                str(event.get('event_type', '')),
                str(event.get('description', '')),
                amount_text,
            ])

        operations_table = Table(rows, colWidths=[95, 110, 240, 70], repeatRows=1)
        operations_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(operations_table)
    else:
        story.append(Paragraph(gettext('No operations found for the selected period.'), normal_style))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    disposition = 'attachment' if as_attachment else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="financial_report.pdf"'
    return response

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
                # Fallback: user might type the name but not pick the datalist option
                if not client_id:
                    display_name = (request.POST.get('client_deposit_display') or '').strip()
                    if display_name:
                        # strip balance info if present e.g. "Name (10 AZN / Lessons: 3)"
                        name_only = display_name.split(' (', 1)[0].strip()
                        candidate = Client.objects.filter(full_name__iexact=name_only).first()
                        if not candidate:
                            candidates = list(Client.objects.filter(full_name__icontains=name_only))
                            if len(candidates) == 1:
                                candidate = candidates[0]
                        if candidate:
                            client_id = str(candidate.id)
                # Accept commas/whitespace and allow leaving lessons empty (treat as 0)
                amount_str = (request.POST.get('deposit_amount') or '').replace(',', '.').strip()
                lessons_count_str = (request.POST.get('deposit_lessons') or '').strip()

                if lessons_count_str == '':
                    lessons_count_str = '0'

                if not client_id or not amount_str:
                    messages.error(request, gettext("Error: Client not selected or top-up data is incorrect."))
                    return redirect('dashboard')

                try:
                    amount = Decimal(amount_str)
                    lessons_added = int(lessons_count_str)
                except (ValueError, TypeError, InvalidOperation):
                    messages.error(request, gettext("Error: Client not selected or top-up data is incorrect."))
                    return redirect('dashboard')

                if amount <= 0 or lessons_added < 0:
                    messages.error(request, gettext("Error: Client not selected or top-up data is incorrect."))
                    return redirect('dashboard')

                client = Client.objects.get(id=client_id)

                with transaction.atomic():
                    client.balance += amount
                    client.lessons_balance += lessons_added
                    client.save()
                    deposit = ClientDeposit.objects.create(
                        client=client,
                        amount=amount,
                        lessons_added=lessons_added,
                        balance_after=client.balance,
                        lessons_balance_after=client.lessons_balance
                    )
                    
                    # Печатаем чек для пополнения
                    print_receipt_for_deposit(deposit)

                messages.success(request, gettext("Client %(client_name)s balance successfully topped up by %(amount)s.") % {
                    'client_name': client.full_name,
                    'amount': amount
                })

            except Client.DoesNotExist:
                messages.error(request, gettext("Error: Client not found."))
            except Exception as e:
                print(f"ОШИБКА ДЕПОЗИТА: {e}")
                messages.error(request, gettext("An unexpected error occurred during top-up: %(error)s") % {'error': e})

        elif action_type == 'process_session':
            try:
                client_id = request.POST.get('client_id')
                worker_id = request.POST.get('worker_id')
                if not client_id:
                    display_name = (request.POST.get('client_session_display') or '').strip()
                    if display_name:
                        name_only = display_name.split(' (', 1)[0].strip()
                        candidate = Client.objects.filter(full_name__iexact=name_only).first()
                        if not candidate:
                            candidates = list(Client.objects.filter(full_name__icontains=name_only))
                            if len(candidates) == 1:
                                candidate = candidates[0]
                        if candidate:
                            client_id = str(candidate.id)

                if not worker_id:
                    worker_display = (request.POST.get('worker_session_display') or '').strip()
                    if worker_display:
                        worker_candidate = Worker.objects.filter(
                            Q(user__username__iexact=worker_display) |
                            Q(user__first_name__iexact=worker_display) |
                            Q(user__last_name__iexact=worker_display)
                        ).first()
                        if not worker_candidate:
                            workers = list(Worker.objects.filter(
                                Q(user__username__icontains=worker_display) |
                                Q(user__first_name__icontains=worker_display) |
                                Q(user__last_name__icontains=worker_display)
                            ))
                            if len(workers) == 1:
                                worker_candidate = workers[0]
                        if worker_candidate:
                            worker_id = str(worker_candidate.id)
                cost_str = request.POST.get('session_cost')
                lessons_count_str = request.POST.get('session_lessons', '').strip()

                if not client_id or not worker_id or not cost_str or lessons_count_str == '':
                    messages.error(request, gettext("Session error: Data is incorrect."))
                    return redirect('dashboard')

                try:
                    session_cost = Decimal(cost_str)
                    lessons_count = int(lessons_count_str)
                except (ValueError, TypeError):
                    messages.error(request, gettext("Session error: Data is incorrect."))
                    return redirect('dashboard')

                if session_cost <= 0 or lessons_count <= 0:
                    messages.error(request, gettext("Session error: Data is incorrect."))
                    return redirect('dashboard')

                with transaction.atomic():
                    client = Client.objects.select_for_update().get(id=client_id)
                    worker = Worker.objects.select_for_update().get(id=worker_id)

                    if client.balance < session_cost:
                        messages.error(request, gettext("Error: Client %(client_name)s has insufficient funds.") % {
                            'client_name': client.full_name
                        })
                        return redirect('dashboard')

                    if client.lessons_balance < lessons_count:
                        messages.error(request, gettext("Error: Client %(client_name)s has insufficient lessons.") % {
                            'client_name': client.full_name
                        })
                        return redirect('dashboard')

                    client.balance -= session_cost
                    client.lessons_balance -= lessons_count
                    client.save()


                    transaction_record = Transaction.objects.create(
                        client=client,
                        worker=worker,
                        amount=session_cost,
                        receipt_printed=False,
                        lessons_count=lessons_count,
                        balance_after=client.balance,
                        lessons_balance_after=client.lessons_balance
                    )

                    messages.success(request, gettext("Session payment processed successfully."))
                    print_receipt_for_session(transaction_record)

            except Client.DoesNotExist:
                messages.error(request, gettext("Error: Client not found."))
            except Worker.DoesNotExist:
                messages.error(request, gettext("Error: Worker not found."))
            except Exception as e:
                messages.error(request, gettext("An unexpected error occurred: %(error)s") % {'error': e})

        # temprorary removed this functionality
        elif action_type == 'payout':
            messages.error(request, "Операция выплаты сотруднику отключена, так как баланс сотрудника убран.")
            return redirect(f"{request.path}?client_q={client_q}&worker_q={worker_q}")
        return redirect(f"{request.path}?client_q={client_q}&worker_q={worker_q}")
    else:
        if _has_new_client_fields():
            clients_qs = Client.objects.all().order_by('full_name')
            workers_qs = Worker.objects.all().order_by('user__username')
            # Получаем последние транзакции, депозиты и отмены пополнений
            recent_transactions = Transaction.objects.select_related('client', 'worker__user').order_by('-date_time')[:20]
            recent_deposits = ClientDeposit.objects.select_related('client').order_by('-date_time')[:20]
            recent_adjustments = ClientBalanceAdjustment.objects.select_related('client').order_by('-date_time')[:20]
            
            # Объединяем в один список с пометкой типа
            recent_operations = []
            for tx in recent_transactions:
                recent_operations.append({
                    'type': 'transaction',
                    'date_time': tx.date_time,
                    'transaction': tx,
                    'deposit': None
                })
            for dep in recent_deposits:
                recent_operations.append({
                    'type': 'deposit',
                    'date_time': dep.date_time,
                    'transaction': None,
                    'deposit': dep
                })
            for adj in recent_adjustments:
                recent_operations.append({
                    'type': 'adjustment',
                    'date_time': adj.date_time,
                    'transaction': None,
                    'deposit': None,
                    'adjustment': adj
                })
            # Сортируем по дате и берем последние 20
            recent_operations = sorted(recent_operations, key=lambda x: x['date_time'], reverse=True)[:20]
        else:
            # Используем только существующие поля до применения миграции
            messages.warning(request, gettext("Database migration required. Please run: python manage.py migrate"))
            clients_qs = []
            workers_qs = Worker.objects.all().order_by('user__username')
            recent_transactions = []
            recent_operations = []

        if client_q:
            clients_qs = clients_qs.filter(full_name__icontains=client_q).order_by('full_name')
        if worker_q:
            workers_qs = workers_qs.filter(
                Q(user__username__icontains=worker_q) |  # Поиск по логину
                Q(user__first_name__icontains=worker_q) |  # Поиск по имени
                Q(user__last_name__icontains=worker_q)  # Поиск по фамилии
            ).order_by('user__username')

        context = {
            'clients': clients_qs,
            'workers': workers_qs,
            'recent_transactions': recent_transactions,
            'recent_operations': recent_operations if _has_new_client_fields() else [],
            'client_q': client_q,
            'worker_q': worker_q,
        }
        return render(request, 'accounting/dashboard.html', context)

@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def reports(request):
    # all reports
    context = {
        'current_filter_desc': gettext('all time'),
        'start_date_input': '',
        'end_date_input': '',
        'current_preset': '',
    }

    selected_client_id = request.GET.get('client_id')
    selected_worker_id = request.GET.get('worker_id')
    transaction_id_search = request.GET.get('transaction_id', '').strip()

    selected_client_name = ''
    selected_worker_name = ''

    # date filtration
    now = timezone.now().date()
    start_date = None
    end_date = None
    preset = (request.GET.get('preset') or '').strip()
    valid_presets = {'today', 'week', 'month'}
    if preset not in valid_presets:
        preset = ''
    context['current_preset'] = preset

    if preset:
        if preset == 'today':
            start_date = now
            end_date = now
            context['current_filter_desc'] = gettext('today')
        elif preset == 'week':
            start_date = now - timedelta(days=now.weekday())
            end_date = now
            context['current_filter_desc'] = gettext('this week')
        elif preset == 'month':
            start_date = now.replace(day=1)
            end_date = now
            context['current_filter_desc'] = gettext('this month')

    custom_start_str = request.GET.get('start_date')
    custom_end_str = request.GET.get('end_date')

    if custom_start_str and custom_end_str:
        try:
            start_date = datetime.strptime(custom_start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(custom_end_str, '%Y-%m-%d').date()
            context['current_filter_desc'] = gettext('from %(start)s to %(end)s') % {
                'start': start_date.strftime('%d.%m.%Y'),
                'end': end_date.strftime('%d.%m.%Y')
            }
            context['start_date_input'] = custom_start_str
            context['end_date_input'] = custom_end_str
        except ValueError:
            messages.error(request, gettext("Invalid date format. Use: YYYY-MM-DD."))

    # basic QuerySets
    if _has_new_client_fields():
        transactions_qs = Transaction.objects.select_related('client', 'worker__user').all()
        deposits_qs = ClientDeposit.objects.select_related('client').all()
        adjustments_qs = ClientBalanceAdjustment.objects.select_related('client').all()
    else:
        # Если новые поля не существуют, показываем сообщение
        messages.error(request, gettext("Database migration required. Please run: python manage.py migrate"))
        context['unified_log'] = []
        context['clients'] = []
        context['workers'] = Worker.objects.select_related('user').all()
        context['selected_client_id'] = selected_client_id or ''
        context['selected_worker_id'] = selected_worker_id or ''
        return render(request, 'accounting/reports.html', context)
    if start_date and end_date:
        transactions_qs = transactions_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)
        deposits_qs = deposits_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)
        adjustments_qs = adjustments_qs.filter(date_time__date__gte=start_date, date_time__date__lte=end_date)

    if selected_client_id:
        try:
            transactions_qs = transactions_qs.filter(client_id=int(selected_client_id))
            deposits_qs = deposits_qs.filter(client_id=int(selected_client_id))
            adjustments_qs = adjustments_qs.filter(client_id=int(selected_client_id))
            selected_client = Client.objects.filter(id=int(selected_client_id)).first()
            if selected_client:
                selected_client_name = selected_client.full_name
        except ValueError:
            messages.error(request, gettext("Invalid client identifier."))

    if selected_worker_id:
        try:
            transactions_qs = transactions_qs.filter(worker_id=int(selected_worker_id))
            # У пополнений нет привязки к сотруднику, поэтому при фильтре по сотруднику
            # показываем только сеансы конкретного сотрудника.
            deposits_qs = deposits_qs.none()
            adjustments_qs = adjustments_qs.none()
            selected_worker = Worker.objects.select_related('user').filter(id=int(selected_worker_id)).first()
            if selected_worker:
                selected_worker_name = selected_worker.user.get_full_name() or selected_worker.user.username
        except ValueError:
            messages.error(request, gettext("Invalid worker identifier."))

    # Поиск по номеру транзакции (сеансы и депозиты)
    if transaction_id_search:
        try:
            transaction_id_int = int(transaction_id_search)
            transactions_qs = transactions_qs.filter(id=transaction_id_int)
            deposits_qs = deposits_qs.filter(id=transaction_id_int)
            adjustments_qs = adjustments_qs.filter(id=transaction_id_int)
        except ValueError:
            messages.error(request, gettext("Invalid transaction number. Please enter a valid number."))

    total_income = transactions_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_deposits = deposits_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_adjustments = adjustments_qs.aggregate(Sum('amount_removed'))['amount_removed__sum'] or Decimal('0.00')

    context['total_income'] = total_income
    context['total_payouts'] = Decimal('0.00')
    context['total_deposits'] = total_deposits
    context['total_adjustments'] = total_adjustments
    context['net_profit'] = total_income + total_deposits - total_adjustments


    unified_log = []

    for tx in transactions_qs:
        unified_log.append({
            'date_time': tx.date_time,
            'event_type': gettext('Session (Income)'),
            'description': f"{tx.client.full_name} -> {tx.worker.user.username}",
            'amount_positive': tx.amount,
            'amount_negative': None,
            'css_class': 'income',
            'transaction_id': tx.id,
            'is_deposit': False
        })

    for deposit in deposits_qs:
        unified_log.append({
            'date_time': deposit.date_time,
            'event_type': gettext('Top-up'),
            'description': gettext('Client: %(client_name)s') % {'client_name': deposit.client.full_name},
            'amount_positive': deposit.amount,
            'amount_negative': None,
            'css_class': 'deposit',
            'deposit_id': deposit.id,
            'is_deposit': True,
            'is_adjustment': False
        })

    for adjustment in adjustments_qs:
        unified_log.append({
            'date_time': adjustment.date_time,
            'event_type': gettext('Top-up cancellation'),
            'description': gettext('Client: %(client_name)s') % {'client_name': adjustment.client.full_name},
            'amount_positive': None,
            'amount_negative': adjustment.amount_removed,
            'css_class': 'payout',
            'adjustment_id': adjustment.id,
            'is_deposit': False,
            'is_adjustment': True
        })



    context['unified_log'] = sorted(unified_log, key=lambda e: e['date_time'], reverse=True)


    if _has_new_client_fields():
        context['clients'] = Client.objects.all()
    else:
        context['clients'] = []
    context['workers'] = Worker.objects.select_related('user').all()
    context['selected_client_id'] = selected_client_id or ''
    context['selected_worker_id'] = selected_worker_id or ''
    context['transaction_id_search'] = transaction_id_search
    context['selected_client_name'] = selected_client_name
    context['selected_worker_name'] = selected_worker_name

    # Ссылки на пресеты с сохранением уже выбранных фильтров клиента/сотрудника
    # и без ручного ввода дат.
    preset_base_params = request.GET.copy()
    preset_base_params.pop('preset', None)
    preset_base_params.pop('start_date', None)
    preset_base_params.pop('end_date', None)
    preset_base_params.pop('export', None)
    preset_base_params.pop('download', None)

    all_time_query = preset_base_params.urlencode()
    context['all_time_query_string'] = all_time_query

    today_params = preset_base_params.copy()
    today_params['preset'] = 'today'
    context['today_query_string'] = today_params.urlencode()

    week_params = preset_base_params.copy()
    week_params['preset'] = 'week'
    context['week_query_string'] = week_params.urlencode()

    month_params = preset_base_params.copy()
    month_params['preset'] = 'month'
    context['month_query_string'] = month_params.urlencode()

    query_params = request.GET.copy()
    query_params.pop('export', None)
    query_params.pop('download', None)
    export_query = query_params.urlencode()
    export_pdf_base_query = f"{export_query}&export=pdf" if export_query else "export=pdf"
    context['export_pdf_download_query_string'] = f"{export_pdf_base_query}&download=1"
    context['export_pdf_print_query_string'] = export_pdf_base_query

    if (request.GET.get('export') or '').lower() == 'pdf':
        as_attachment = (request.GET.get('download') or '').lower() in ('1', 'true', 'yes')
        return _generate_reports_pdf_response(context, as_attachment=as_attachment)

    return render(request, 'accounting/reports.html', context)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def clients_list(request):
    """
    Отдельная страница со всеми клиентами и поиском
    """
    query = request.GET.get('q', '').strip()

    clients_qs = Client.objects.all()

    if query:
        clients_qs = clients_qs.filter(
            Q(full_name__icontains=query) |
            Q(phone__icontains=query)
        )

    clients_qs = clients_qs.order_by('full_name')

    context = {
        'clients': clients_qs,
        'query': query,
    }
    return render(request, 'accounting/clients_list.html', context)

@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def print_receipt(request, transaction_id):
    """
    Печатает чек на физический принтер (если настроен)
    """
    transaction_record = get_object_or_404(Transaction.objects.select_related('client', 'worker__user'), id=transaction_id)
    try:
        print_receipt_for_session(transaction_record)
        messages.success(request, gettext("Receipt sent to printer successfully."))
    except Exception as e:
        messages.error(request, gettext("Failed to print receipt: %(error)s") % {'error': e})
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


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def view_deposit_receipt(request, deposit_id, format='html'):
    """
    Просмотр чека пополнения баланса в браузере (HTML)
    """
    deposit = get_object_or_404(
        ClientDeposit.objects.select_related('client'), 
        id=deposit_id
    )
    
    context = {
        'deposit': deposit,
        'date_str': deposit.date_time.strftime('%d.%m.%Y %H:%M:%S'),
    }
    
    return render(request, 'accounting/deposit_receipt.html', context)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def adjust_client_balance(request, client_id):
    """
    Отмена пополнения баланса/уроков из профиля клиента.
    """
    client = get_object_or_404(Client, id=client_id)

    if request.method != 'POST':
        return redirect('view_client', client_id=client.id)

    amount_str = (request.POST.get('amount_removed') or '0').replace(',', '.').strip()
    lessons_str = (request.POST.get('lessons_removed') or '0').strip()

    try:
        amount_removed = Decimal(amount_str)
        lessons_removed = int(lessons_str)
    except (ValueError, TypeError, InvalidOperation):
        messages.error(request, gettext("Invalid data. Enter valid amount and lessons."))
        return redirect('view_client', client_id=client.id)

    if amount_removed < 0 or lessons_removed < 0:
        messages.error(request, gettext("Amount and lessons cannot be negative."))
        return redirect('view_client', client_id=client.id)

    if amount_removed == 0 and lessons_removed == 0:
        messages.error(request, gettext("Enter amount or lessons to remove."))
        return redirect('view_client', client_id=client.id)

    with transaction.atomic():
        client_locked = Client.objects.select_for_update().get(id=client.id)

        if client_locked.balance < amount_removed:
            messages.error(request, gettext("Client has insufficient balance for this cancellation."))
            return redirect('view_client', client_id=client.id)

        if client_locked.lessons_balance < lessons_removed:
            messages.error(request, gettext("Client has insufficient lessons for this cancellation."))
            return redirect('view_client', client_id=client.id)

        client_locked.balance -= amount_removed
        client_locked.lessons_balance -= lessons_removed
        client_locked.save()

        adjustment = ClientBalanceAdjustment.objects.create(
            client=client_locked,
            amount_removed=amount_removed,
            lessons_removed=lessons_removed,
            balance_after=client_locked.balance,
            lessons_balance_after=client_locked.lessons_balance,
        )

    messages.success(request, gettext("Top-up cancellation completed successfully."))
    return redirect(f"{reverse('view_adjustment_receipt', args=[adjustment.id])}?print=1")


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def view_adjustment_receipt(request, adjustment_id):
    """
    Просмотр чека отмены пополнения.
    """
    adjustment = get_object_or_404(ClientBalanceAdjustment.objects.select_related('client'), id=adjustment_id)
    context = {
        'adjustment': adjustment,
    }
    return render(request, 'accounting/adjustment_receipt.html', context)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def print_deposit_receipt(request, deposit_id):
    """
    Печатает чек пополнения на физический принтер (если настроен)
    """
    deposit = get_object_or_404(ClientDeposit.objects.select_related('client'), id=deposit_id)
    try:
        print_receipt_for_deposit(deposit)
        messages.success(request, gettext("Receipt sent to printer successfully."))
    except Exception as e:
        messages.error(request, gettext("Failed to print receipt: %(error)s") % {'error': e})
    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def create_client(request):
    """
    Создание нового клиента
    """
    if request.method == 'POST':
        try:
            full_name = request.POST.get('full_name', '').strip()
            date_of_birth_str = request.POST.get('date_of_birth', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            referral_source = request.POST.get('referral_source', '').strip()
            client_type = request.POST.get('client_type', 'adult')
            lessons_balance_str = request.POST.get('lessons_balance', '').strip()
            initial_balance_str = request.POST.get('initial_balance', '0').strip()
            initial_lessons_str = request.POST.get('initial_lessons', '0').strip()

            if not full_name:
                messages.error(request, gettext("Error: Client name is required."))
                return render(request, 'accounting/create_client.html', {
                    'client_types': Client.CLIENT_TYPE_CHOICES,
                    'form_data': request.POST
                })

            # Проверяем, нет ли уже клиента с таким именем
            if Client.objects.filter(full_name=full_name).exists():
                messages.error(request, gettext("Error: A client with this name already exists."))
                return render(request, 'accounting/create_client.html', {
                    'client_types': Client.CLIENT_TYPE_CHOICES,
                    'form_data': request.POST
                })

            # Парсим дату рождения
            date_of_birth = None
            if date_of_birth_str:
                try:
                    date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
                except ValueError:
                    messages.error(request, gettext("Invalid date format. Use: YYYY-MM-DD."))
                    return render(request, 'accounting/create_client.html', {
                        'client_types': Client.CLIENT_TYPE_CHOICES,
                        'form_data': request.POST
                    })

            initial_balance = Decimal(initial_balance_str) if initial_balance_str else Decimal('0.00')
            try:
                initial_lessons = int(initial_lessons_str) if initial_lessons_str else 0
            except (ValueError, TypeError):
                messages.error(request, gettext("Invalid lessons count. Use a whole number."))
                return render(request, 'accounting/create_client.html', {
                    'client_types': Client.CLIENT_TYPE_CHOICES,
                    'form_data': request.POST
                })

            if initial_lessons < 0:
                messages.error(request, gettext("Invalid lessons count. Use a whole number."))
                return render(request, 'accounting/create_client.html', {
                    'client_types': Client.CLIENT_TYPE_CHOICES,
                    'form_data': request.POST
                })

            # Создаем нового клиента
            new_client = Client.objects.create(
                full_name=full_name,
                date_of_birth=date_of_birth,
                address=address,
                phone=phone,
                referral_source=referral_source,
                client_type=client_type,
                balance=initial_balance,
                lessons_balance=initial_lessons
            )

            messages.success(request, gettext("Client %(client_name)s created successfully.") % {
                'client_name': new_client.full_name
            })
            return redirect('view_client', client_id=new_client.id)

        except Exception as e:
            messages.error(request, gettext("An unexpected error occurred while creating client: %(error)s") % {'error': e})
            return render(request, 'accounting/create_client.html', {
                'client_types': Client.CLIENT_TYPE_CHOICES,
                'form_data': request.POST
            })
    else:
        return render(request, 'accounting/create_client.html', {
            'client_types': Client.CLIENT_TYPE_CHOICES
        })


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def view_client(request, client_id):
    """
    Просмотр информации о клиенте
    """
    # Проверяем наличие новых полей перед загрузкой
    if _has_new_client_fields():
        client = get_object_or_404(
            Client.objects.prefetch_related('transactions_as_client', 'deposits', 'balance_adjustments'),
            id=client_id
        )
    else:
        # Если новые поля не существуют, показываем сообщение
        messages.error(request, gettext("Database migration required. Please run: python manage.py migrate"))
        return redirect('dashboard')
    
    # Получаем последние транзакции и пополнения
    recent_transactions = client.transactions_as_client.select_related('worker__user').order_by('-date_time')[:10]
    recent_deposits = client.deposits.order_by('-date_time')[:10]
    recent_adjustments = client.balance_adjustments.order_by('-date_time')[:10]
    
    # Вычисляем статистику
    total_spent = client.transactions_as_client.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_deposited = client.deposits.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_adjusted = client.balance_adjustments.aggregate(Sum('amount_removed'))['amount_removed__sum'] or Decimal('0.00')
    total_sessions = client.transactions_as_client.count()
    
    context = {
        'client': client,
        'recent_transactions': recent_transactions,
        'recent_deposits': recent_deposits,
        'recent_adjustments': recent_adjustments,
        'total_spent': total_spent,
        'total_deposited': total_deposited,
        'total_adjusted': total_adjusted,
        'total_sessions': total_sessions,
    }
    
    return render(request, 'accounting/view_client.html', context)


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def edit_client(request, client_id):
    """
    Редактирование данных клиента
    """
    client = get_object_or_404(Client, id=client_id)

    if request.method == 'POST':
        try:
            full_name = request.POST.get('full_name', '').strip()
            date_of_birth_str = request.POST.get('date_of_birth', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            referral_source = request.POST.get('referral_source', '').strip()
            client_type = request.POST.get('client_type', 'adult')
            lessons_balance_str = request.POST.get('lessons_balance', '').strip()

            if not full_name:
                messages.error(request, gettext("Error: Client name is required."))
                return render(request, 'accounting/edit_client.html', {
                    'client_types': Client.CLIENT_TYPE_CHOICES,
                    'client': client,
                    'form_data': request.POST
                })

            # Проверяем уникальность имени (кроме текущего клиента)
            if Client.objects.filter(full_name=full_name).exclude(id=client.id).exists():
                messages.error(request, gettext("Error: A client with this name already exists."))
                return render(request, 'accounting/edit_client.html', {
                    'client_types': Client.CLIENT_TYPE_CHOICES,
                    'client': client,
                    'form_data': request.POST
                })

            # Парсим дату рождения
            date_of_birth = None
            if date_of_birth_str:
                try:
                    date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
                except ValueError:
                    messages.error(request, gettext("Invalid date format. Use: YYYY-MM-DD."))
                    return render(request, 'accounting/edit_client.html', {
                        'client_types': Client.CLIENT_TYPE_CHOICES,
                        'client': client,
                        'form_data': request.POST
                    })

            # Обновляем данные клиента (баланс не трогаем здесь)
            client.full_name = full_name
            client.date_of_birth = date_of_birth
            client.address = address
            client.phone = phone
            client.referral_source = referral_source
            client.client_type = client_type
            # update lessons balance if provided
            if lessons_balance_str:
                try:
                    lessons_balance_val = int(lessons_balance_str)
                except (ValueError, TypeError):
                    messages.error(request, gettext("Invalid lessons count. Use a whole number."))
                    return render(request, 'accounting/edit_client.html', {
                        'client_types': Client.CLIENT_TYPE_CHOICES,
                        'client': client,
                        'form_data': request.POST
                    })
                if lessons_balance_val < 0:
                    messages.error(request, gettext("Invalid lessons count. Use a whole number."))
                    return render(request, 'accounting/edit_client.html', {
                        'client_types': Client.CLIENT_TYPE_CHOICES,
                        'client': client,
                        'form_data': request.POST
                    })
                client.lessons_balance = lessons_balance_val
            client.save()

            messages.success(request, gettext("Client %(client_name)s updated successfully.") % {
                'client_name': client.full_name
            })
            return redirect('view_client', client_id=client.id)

        except Exception as e:
            messages.error(request, gettext("An unexpected error occurred while updating client: %(error)s") % {'error': e})
            return render(request, 'accounting/edit_client.html', {
                'client_types': Client.CLIENT_TYPE_CHOICES,
                'client': client,
                'form_data': request.POST
            })
    else:
        return render(request, 'accounting/edit_client.html', {
            'client_types': Client.CLIENT_TYPE_CHOICES,
            'client': client
        })


@login_required(login_url='/admin/login/')
@user_passes_test(is_staff_user, login_url='/admin/login/')
def delete_client(request, client_id):
    """
    Удаление клиента (без существующих транзакций/пополнений)
    """
    client = get_object_or_404(Client, id=client_id)

    if request.method != 'POST':
        return redirect('view_client', client_id=client.id)

    # Не даём удалить клиента, если есть операции
    if client.transactions_as_client.exists() or client.deposits.exists():
        messages.error(request, gettext("Error: Cannot delete client with existing sessions or deposits."))
        return redirect('view_client', client_id=client.id)

    name = client.full_name
    client.delete()
    messages.success(request, gettext("Client %(client_name)s deleted successfully.") % {
        'client_name': name
    })
    return redirect('clients_list')
