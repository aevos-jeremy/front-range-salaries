@echo off
rem Starts the Front Range Engineering Pay app and opens it in your web browser.
rem Only this computer can connect (--server.address localhost).
rem Close this window to stop the app.
cd /d "%~dp0"
.venv\Scripts\python.exe -m streamlit run app\app.py --server.address localhost
