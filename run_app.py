import os
import sys
import threading
import webbrowser
from time import sleep

import django
from django.core.management import execute_from_command_line

# Указываем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject1.settings')
django.setup()

def run_server():
    # Запускаем dev-сервер на 127.0.0.1:8000
    execute_from_command_line([sys.argv[0], 'runserver', '127.0.0.1:8000'])

if __name__ == '__main__':
    # Стартуем сервер в отдельном потоке
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    # Немного ждём, чтобы сервер поднялся, и открываем браузер
    sleep(2)
    webbrowser.open('http://127.0.0.1:8000/dashboard/')

    # Чтобы окно не закрывалось сразу (если запуск через двойной клик)
    t.join()