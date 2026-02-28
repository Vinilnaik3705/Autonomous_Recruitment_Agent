# Quick startup - Start Docker Desktop first!

Write-Host "⚠️  Docker Desktop is not running!" -ForegroundColor Red
Write-Host ""
Write-Host "PLEASE DO THIS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open Docker Desktop application" -ForegroundColor Yellow
Write-Host "   - Click Start Menu" -ForegroundColor Gray
Write-Host "   - Search 'Docker Desktop'" -ForegroundColor Gray
Write-Host "   - Click 'Docker Desktop.exe'" -ForegroundColor Gray
Write-Host "   - Wait 30 seconds for it to start" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Then run this command in PowerShell:" -ForegroundColor Yellow
Write-Host "   docker ps" -ForegroundColor White
Write-Host ""
Write-Host "3. Verify output shows: 'CONTAINER ID   IMAGE   COMMAND'" -ForegroundColor Gray
Write-Host ""
Write-Host "4. THEN run this script again:" -ForegroundColor Yellow
Write-Host "   .\START_DATABASE.ps1" -ForegroundColor White
Write-Host ""

Start-Sleep -Seconds 3
