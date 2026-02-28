Write-Host "================================" -ForegroundColor Cyan
Write-Host "📦 HR RECRUITMENT SYSTEM STARTUP" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if docker-compose is installed
Write-Host "✓ Checking Docker..." -ForegroundColor Green
docker version --format '{{.Server.Version}}' 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker Engine is not running or not installed." -ForegroundColor Red
    Write-Host "💡 Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

# Check if containers are already running
$running = docker-compose ps --services --filter "status=running" 2>$null
if ($running -like "*postgres*") {
    Write-Host "⚠️  PostgreSQL is already running. Checking database..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
} else {
    Write-Host "🚀 Starting PostgreSQL container..." -ForegroundColor Green
    docker-compose up -d postgres
    Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Verify connection
    $maxRetries = 30
    $retries = 0
    while ($retries -lt $maxRetries) {
        try {
            $result = docker exec hr_postgres psql -U hr_user -d hr_db -c "SELECT 1;" 2>$null
            if ($result) {
                Write-Host "✅ PostgreSQL is ready!" -ForegroundColor Green
                break
            }
        } catch {
            $retries++
            if ($retries -lt $maxRetries) {
                Write-Host "⏳ Waiting... ($retries/$maxRetries)" -ForegroundColor Yellow
                Start-Sleep -Seconds 1
            }
        }
    }
    
    if ($retries -ge $maxRetries) {
        Write-Host "❌ PostgreSQL failed to start. Check Docker logs:" -ForegroundColor Red
        Write-Host "   docker-compose logs postgres" -ForegroundColor Yellow
        exit 1
    }
}

# Initialize database tables if they don't exist
Write-Host "🔧 Initializing database schema..." -ForegroundColor Green
python backend/init_db_pg.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database schema initialized!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Database initialization had issues. Check if tables exist." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ DATABASE IS READY!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. In another terminal, start the backend: uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000" -ForegroundColor White
Write-Host "2. In another terminal, start frontend: cd frontend && npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "Stop everything with: docker-compose down" -ForegroundColor Gray
