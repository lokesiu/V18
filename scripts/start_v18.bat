@echo off
echo Starting MingZhengTai V18 Beta...
python -c "from app.main_window import main; main()"
if errorlevel 1 (
    echo Failed to start V18.
    pause
)
