@echo off
REM One-click Windows launcher for Docker Desktop
REM Double-click to run the OpenRefine Reconciliation service.

setlocal ENABLEDELAYEDEXPANSION

REM === CONFIG ===
set IMAGE=ghcr.io/post45-data-collective/openrefine-reconciliation-service:main
set PORT=5001
set NAME=openrefine-recon

REM === Locate docker CLI ===
set "DOCKER_EXE=docker"
where %DOCKER_EXE% >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
    set "DOCKER_EXE=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
  ) else (
    echo Docker Desktop is required. Please install & open Docker Desktop, then try again.
    pause
    exit /b 1
  )
)

REM === Ensure Docker Desktop app is running (launch if not) ===
tasklist /FI "IMAGENAME eq Docker Desktop.exe" | find /I "Docker Desktop.exe" >nul || (
  if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  )
)

REM === Use Docker Desktop's named pipe ===
set "DOCKER_HOST=npipe:////./pipe/docker_engine"

REM === Wait up to 180s for engine ===
set /a tries=0
:wait_engine
"%DOCKER_EXE%" info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  set /a tries+=1
  if %tries% GTR 180 (
    echo Docker appears open but the engine isn't ready.
    echo Open Docker Desktop and wait until it shows "Running", then try again.
    pause
    exit /b 1
  )
  timeout /t 1 >nul
  goto :wait_engine
)

echo Pulling %IMAGE% ...
"%DOCKER_EXE%" pull %IMAGE%
if %ERRORLEVEL% NEQ 0 (
  echo Could not pull image: %IMAGE%
  echo - Is the image public?
  echo - Is the name spelled correctly?
  pause
  exit /b 1
)

REM Stop existing container (if any)
"%DOCKER_EXE%" rm -f %NAME% >nul 2>nul

echo Starting container "%NAME%" on port %PORT% ...
"%DOCKER_EXE%" run -d --name %NAME% -p %PORT%:5001 %IMAGE% >nul
if %ERRORLEVEL% NEQ 0 (
  echo Failed to start container. Is port %PORT% already in use?
  echo Edit this file and change: set PORT=5050
  pause
  exit /b 1
)

start http://localhost:%PORT%
echo Running at http://localhost:%PORT%
echo You can close this window.
