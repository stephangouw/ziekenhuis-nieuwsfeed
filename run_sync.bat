@echo off
echo.
echo ========================================================
echo   Ziekenhuis Nieuwsfeed: Volledige Synchronisatie
echo ========================================================
echo.

:: Pad naar dit script
set BASE_DIR=%~dp0
cd /d %BASE_DIR%

:: venv tijdelijk uitgeschakeld omdat deze leeg is en er geen schijfruimte is om hem te vullen
:: if exist .venv\Scripts\activate (
::     call .venv\Scripts\activate
:: )

:: Run de automator met de globale python
python sync_all.py

echo.
echo Synchronisatie voltooid!
pause
