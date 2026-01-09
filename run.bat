@echo off
cd /d "C:\Users\texra\PycharmProjects\fleks_control_panel"

rem Активируем именно то виртуальное окружение, где стоят все пакеты
call "C:\Users\texra\PycharmProjects\DjangoProject1\.venv\Scripts\activate.bat"

rem Запускаем приложение
python run_app.py

rem Чтобы окно не закрывалось сразу (по желанию можно убрать)
pause