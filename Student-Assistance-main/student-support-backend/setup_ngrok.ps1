# Download and setup ngrok for Telegram webhook testing
Write-Host "Downloading ngrok..." -ForegroundColor Green

try {
    $ngrokUrl = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
    $zipPath = "$PSScriptRoot\ngrok.zip"
    $extractPath = "$PSScriptRoot\ngrok"

    # Download ngrok
    Invoke-WebRequest -Uri $ngrokUrl -OutFile $zipPath -UseBasicParsing

    # Extract ngrok
    if (!(Test-Path $extractPath)) {
        New-Item -ItemType Directory -Path $extractPath -Force
    }

    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

    Write-Host "ngrok downloaded and extracted!" -ForegroundColor Green
    Write-Host "Location: $extractPath" -ForegroundColor Cyan

    # Add to PATH for current session
    $env:PATH += ";$extractPath"

    Write-Host "Starting ngrok tunnel on port 5000..." -ForegroundColor Yellow

    # Start ngrok in background
    $ngrokProcess = Start-Process -FilePath "$extractPath\ngrok.exe" -ArgumentList "http 5000" -NoNewWindow -PassThru

    Write-Host "Waiting for ngrok to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5

    # Get ngrok URL
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 10
        $httpsTunnel = $tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1

        if ($httpsTunnel) {
            $webhookUrl = $httpsTunnel.public_url + "/api/integrations/telegram/webhook"
            Write-Host "ngrok HTTPS URL: $($httpsTunnel.public_url)" -ForegroundColor Green
            Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Green

            # Save webhook URL to a file for the Python script
            $webhookUrl | Out-File -FilePath "$PSScriptRoot\webhook_url.txt" -Encoding UTF8
            Write-Host "Webhook URL saved to webhook_url.txt" -ForegroundColor Cyan
        } else {
            Write-Host "Could not get ngrok tunnel URL" -ForegroundColor Red
        }
    } catch {
        Write-Host "Could not connect to ngrok API. Make sure ngrok is running." -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Keep this PowerShell window open (ngrok is running)" -ForegroundColor White
    Write-Host "2. Open a new terminal and run: python setup_webhook_from_file.py" -ForegroundColor White
    Write-Host "3. Start your backend: python app.py" -ForegroundColor White
    Write-Host "4. Test by sending messages to @Student_Support_231FA04G24_bot" -ForegroundColor White

    Write-Host ""
    Write-Host "Press Ctrl+C to stop ngrok when done testing" -ForegroundColor Yellow

    # Keep the script running to maintain ngrok
    try {
        Wait-Process -Id $ngrokProcess.Id
    } catch {
        Write-Host ""
        Write-Host "ngrok stopped" -ForegroundColor Cyan
    }

} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}