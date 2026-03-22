@echo off
echo 🚀 Setting up ngrok tunnel for Telegram webhook testing
echo.

REM Check if ngrok is installed
ngrok version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ngrok is not installed or not in PATH
    echo.
    echo 📥 Download ngrok from: https://ngrok.com/download
    echo 📝 Extract ngrok.exe and add it to your PATH
    echo.
    pause
    exit /b 1
)

echo ✅ ngrok found!
echo.

REM Start ngrok tunnel
echo 🌐 Starting ngrok tunnel on port 5000...
start "ngrok" cmd /c "ngrok http 5000"

echo ⏳ Waiting for ngrok to start...
timeout /t 5 /nobreak >nul

echo 🔍 Getting ngrok tunnel URL...
for /f "tokens=*" %%i in ('curl -s http://localhost:4040/api/tunnels ^| findstr "https://"') do (
    set NGROK_URL=%%i
    goto :found_url
)

:found_url
echo.
echo 🎯 Ngrok tunnel URL found!
echo %NGROK_URL%
echo.

REM Extract the URL
for /f "tokens=2 delims=:" %%a in ("%NGROK_URL%") do (
    for /f "tokens=1 delims=," %%b in ("%%a") do (
        set WEBHOOK_URL=%%b
    )
)

echo 📡 Setting up Telegram webhook...
python setup_telegram_webhook.py

echo.
echo ✅ Setup complete! Your Telegram bot should now receive messages.
echo 💬 Test by sending a message to @Student_Support_231FA04G24_bot
echo.
pause