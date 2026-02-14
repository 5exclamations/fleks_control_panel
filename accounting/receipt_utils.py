"""
Утилиты для генерации и печати чеков
"""
import os
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
from django.utils.translation import gettext as _
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_pdf_receipt(transaction):
    """
    Генерирует PDF чек для транзакции
    """
    buffer = BytesIO()
    balance_display = transaction.balance_after if transaction.balance_after is not None else transaction.client.balance
    lessons_balance_display = transaction.lessons_balance_after if transaction.lessons_balance_after is not None else transaction.client.lessons_balance
    
    # Создаем PDF документ
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(80*mm, 200*mm),  # Размер чека (80mm ширина, 200mm высота)
        rightMargin=5*mm,
        leftMargin=5*mm,
        topMargin=5*mm,
        bottomMargin=5*mm
    )
    
    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    center_style = ParagraphStyle(
        'CustomCenter',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Содержимое чека
    story = []
    
    # Заголовок
    story.append(Paragraph("FLEKS", title_style))
    story.append(Spacer(1, 3*mm))
    
    # Дата и время
    date_str = transaction.date_time.strftime('%d.%m.%Y %H:%M:%S')
    story.append(Paragraph(f"{_('Date')}: {date_str}", normal_style))
    story.append(Spacer(1, 2*mm))
    
    # Разделитель
    story.append(Paragraph("─" * 30, center_style))
    story.append(Spacer(1, 2*mm))
    
    # Информация о клиенте
    story.append(Paragraph(f"<b>{_('Client')}:</b> {transaction.client.full_name}", normal_style))
    story.append(Spacer(1, 1*mm))
    
    # Информация о сотруднике
    worker_name = transaction.worker.user.get_full_name() or transaction.worker.user.username
    story.append(Paragraph(f"<b>{_('Worker')}:</b> {worker_name}", normal_style))
    story.append(Spacer(1, 2*mm))
    
    # Разделитель
    story.append(Paragraph("─" * 30, center_style))
    story.append(Spacer(1, 2*mm))
    
    # Сумма
    story.append(Paragraph(f"<b>{_('Amount')}:</b> {transaction.amount} AZN", normal_style))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(f"<b>{_('Lessons')}:</b> {transaction.lessons_count}", normal_style))
    story.append(Spacer(1, 2*mm))
    story.append(Spacer(1, 2*mm))
    
    # Разделитель
    story.append(Paragraph("─" * 30, center_style))
    story.append(Spacer(1, 2*mm))
    
    # Баланс клиента
    story.append(Paragraph(f"<b>{_('Balance')}:</b> {balance_display} AZN", normal_style))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(f"<b>{_('Lessons balance')}:</b> {lessons_balance_display}", normal_style))
    story.append(Spacer(1, 3*mm))
    
    # Разделитель
    story.append(Paragraph("─" * 30, center_style))
    story.append(Spacer(1, 3*mm))
    
    # Благодарность
    story.append(Paragraph(_("Thank you!"), center_style))
    story.append(Spacer(1, 2*mm))
    
    # Номер транзакции
    story.append(Paragraph(f"{_('Transaction #')}: {transaction.id}", normal_style))
    
    # Собираем PDF
    doc.build(story)
    
    # Получаем PDF данные
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf


def print_to_thermal_printer(transaction, printer_path=None):
    """
    Печатает чек на термопринтере используя python-escpos
    """
    try:
        from escpos.printer import Usb, Serial, Network, File
        
        # Определяем путь к принтеру
        if printer_path is None:
            # Пытаемся найти принтер автоматически
            # Для USB принтера (Linux)
            if os.path.exists('/dev/usb/lp0'):
                printer = File('/dev/usb/lp0')
            # Для Windows COM порт
            elif os.name == 'nt':
                # По умолчанию COM1, можно настроить в settings
                com_port = getattr(settings, 'RECEIPT_PRINTER_PORT', 'COM1')
                printer = Serial(com_port, baudrate=9600)
            # Для сетевого принтера
            elif hasattr(settings, 'RECEIPT_PRINTER_IP'):
                printer = Network(settings.RECEIPT_PRINTER_IP)
            else:
                # Файловый вывод (для тестирования)
                receipt_file = os.path.join(settings.BASE_DIR, 'receipts', f'receipt_{transaction.id}.txt')
                os.makedirs(os.path.dirname(receipt_file), exist_ok=True)
                printer = File(receipt_file)
        else:
            printer = File(printer_path)
        
        # Печать чека
        printer.set(align='center', font='a', width=1, height=2)
        printer.text("FLEKS\n")
        printer.set(align='center', font='a', width=1, height=1)
        printer.text("\n")
        
        date_str = transaction.date_time.strftime('%d.%m.%Y %H:%M:%S')
        printer.set(align='left', font='a', width=1, height=1)
        printer.text(f"{_('Date')}: {date_str}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.text(f"{_('Client')}: {transaction.client.full_name}\n")
        worker_name = transaction.worker.user.get_full_name() or transaction.worker.user.username
        printer.text(f"{_('Worker')}: {worker_name}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.text("\n")
        printer.set(align='left', font='a', width=2, height=2)
        printer.text(f"{_('Amount')}: {transaction.amount} AZN\n")
        printer.set(align='left', font='a', width=1, height=1)
        balance_display = transaction.balance_after if transaction.balance_after is not None else transaction.client.balance
        lessons_balance_display = transaction.lessons_balance_after if transaction.lessons_balance_after is not None else transaction.client.lessons_balance
        printer.text(f"{_('Lessons')}: {transaction.lessons_count}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.text(f"{_('Balance')}: {balance_display} AZN\n")
        printer.text(f"{_('Lessons balance')}: {lessons_balance_display}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.set(align='center', font='a', width=1, height=1)
        printer.text(f"{_('Thank you!')}\n\n")
        printer.text(f"{_('Transaction #')}: {transaction.id}\n\n")
        
        # Отрезка чека
        printer.cut()
        printer.close()
        
        return True
        
    except ImportError:
        # Если библиотека не установлена, просто логируем
        print(f"python-escpos не установлен. Чек не может быть напечатан на принтере.")
        return False
    except Exception as e:
        print(f"Ошибка при печати на принтер: {e}")
        return False


def generate_receipt_response(transaction, format='pdf', request=None):
    """
    Генерирует HTTP ответ с чеком в указанном формате
    """
    if format == 'pdf':
        pdf = generate_pdf_receipt(transaction)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="receipt_{transaction.id}.pdf"'
        return response
    else:
        # HTML формат для просмотра в браузере
        from django.template.loader import render_to_string
        from django.template import RequestContext
        
        context = {
            'transaction': transaction,
            'date_str': transaction.date_time.strftime('%d.%m.%Y %H:%M:%S'),
            'worker_name': transaction.worker.user.get_full_name() or transaction.worker.user.username,
        }
        
        if request:
            html = render_to_string('accounting/receipt.html', context, request=request)
        else:
            html = render_to_string('accounting/receipt.html', context)
            
        return HttpResponse(html)


def print_to_thermal_printer_deposit(deposit, printer_path=None):
    """
    Печатает чек для пополнения баланса на термопринтере используя python-escpos
    """
    try:
        from escpos.printer import Usb, Serial, Network, File
        
        # Определяем путь к принтеру
        if printer_path is None:
            # Пытаемся найти принтер автоматически
            # Для USB принтера (Linux)
            if os.path.exists('/dev/usb/lp0'):
                printer = File('/dev/usb/lp0')
            # Для Windows COM порт
            elif os.name == 'nt':
                # По умолчанию COM1, можно настроить в settings
                com_port = getattr(settings, 'RECEIPT_PRINTER_PORT', 'COM1')
                printer = Serial(com_port, baudrate=9600)
            # Для сетевого принтера
            elif hasattr(settings, 'RECEIPT_PRINTER_IP'):
                printer = Network(settings.RECEIPT_PRINTER_IP)
            else:
                # Файловый вывод (для тестирования)
                receipt_file = os.path.join(settings.BASE_DIR, 'receipts', f'deposit_{deposit.id}.txt')
                os.makedirs(os.path.dirname(receipt_file), exist_ok=True)
                printer = File(receipt_file)
        else:
            printer = File(printer_path)
        
        # Печать чека
        printer.set(align='center', font='a', width=1, height=2)
        printer.text("FLEKS\n")
        printer.set(align='center', font='a', width=1, height=1)
        printer.text("\n")
        
        date_str = deposit.date_time.strftime('%d.%m.%Y %H:%M:%S')
        printer.set(align='left', font='a', width=1, height=1)
        printer.text(f"{_('Date')}: {date_str}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.text(f"{_('Client')}: {deposit.client.full_name}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.text(f"{_('Operation type')}: {_('Top-up')}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.text("\n")
        printer.set(align='left', font='a', width=2, height=2)
        printer.text(f"{_('Amount')}: {deposit.amount} AZN\n")
        printer.set(align='left', font='a', width=1, height=1)
        printer.text(f"{_('Lessons added')}: {deposit.lessons_added}\n")
        printer.text("─" * 32 + "\n\n")
        
        balance_display = deposit.balance_after if deposit.balance_after is not None else deposit.client.balance
        lessons_balance_display = deposit.lessons_balance_after if deposit.lessons_balance_after is not None else deposit.client.lessons_balance
        printer.text(f"{_('Balance')}: {balance_display} AZN\n")
        printer.text(f"{_('Lessons balance')}: {lessons_balance_display}\n")
        printer.text("─" * 32 + "\n\n")
        
        printer.set(align='center', font='a', width=1, height=1)
        printer.text(f"{_('Thank you!')}\n\n")
        printer.text(f"{_('Deposit #')}: {deposit.id}\n\n")
        
        # Отрезка чека
        printer.cut()
        printer.close()
        
        return True
        
    except ImportError:
        # Если библиотека не установлена, просто логируем
        print(f"python-escpos не установлен. Чек не может быть напечатан на принтере.")
        return False
    except Exception as e:
        print(f"Ошибка при печати на принтер: {e}")
        return False


def print_receipt_for_deposit(deposit):
    """
    Печатает чек для пополнения баланса на принтер
    """
    try:
        # Пытаемся напечатать на термопринтер
        print_success = print_to_thermal_printer_deposit(deposit)
        
        if not print_success:
            # Если печать на принтер не удалась, выводим в консоль для отладки
            balance_display = deposit.balance_after if deposit.balance_after is not None else deposit.client.balance
            lessons_balance_display = deposit.lessons_balance_after if deposit.lessons_balance_after is not None else deposit.client.lessons_balance
            receipt_data = f"""
*** ПСИХОЛОГИЧЕСКИЙ ЦЕНТР ***
Дата: {deposit.date_time.strftime('%Y-%m-%d %H:%M:%S')}
---
Клиент: {deposit.client.full_name}
---
Операция: Пополнение баланса
Сумма: {deposit.amount} AZN
Уроки добавлено: {deposit.lessons_added}
---
Баланс клиента: {balance_display} AZN
Баланс уроков: {lessons_balance_display}
---
Спасибо!
Номер пополнения: {deposit.id}
"""
            print("\n" + "=" * 40)
            print("--- ПЕЧАТЬ ЧЕКА (ПОПОЛНЕНИЕ) ---")
            print(receipt_data)
            print("=" * 40 + "\n")
        
    except Exception as e:
        print(f"Ошибка при печати чека: {e}")

