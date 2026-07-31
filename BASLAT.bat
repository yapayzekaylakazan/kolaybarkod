@echo off
title KolayBarkod Donanim Servisleri
color 0A
echo.
echo  ========================================
echo   KolayBarkod - Donanim Servisleri
echo  ========================================
echo.

:: Python var mı kontrol et
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo python.org adresinden Python 3.10+ yukleyin.
    pause
    exit /b 1
)

:: Gerekli paketleri kur
echo [1/2] Gerekli paketler kontrol ediliyor...
pip install websockets pyserial flask flask-cors --quiet --disable-pip-version-check
echo       Tamam.
echo.

:: Terazi servisini ayrı pencerede başlat
echo [2/2] Servisler baslatiliyor...
start "KolayBarkod - Terazi Servisi" cmd /k "color 0B && echo  TERAZI SERVISI && echo  ws://localhost:8765 && echo. && python terazi_servisi.py"

:: 2 saniye bekle
timeout /t 2 /nobreak >nul

:: Yazıcı servisini ayrı pencerede başlat
start "KolayBarkod - Yazici Servisi" cmd /k "color 0D && echo  YAZICI SERVISI && echo  http://localhost:9200 && echo. && python yazici_servisi.py"

echo.
echo  ========================================
echo   Her iki servis baslatildi!
echo.
echo   Terazi : ws://localhost:8765
echo   Yazici : http://localhost:9200
echo.
echo   Tarayicida KolayBarkod'u acin.
echo   Terazi LED'i yesil yanacak.
echo  ========================================
echo.
echo  Servisleri durdurmak icin bu pencereyi
echo  ve acilan 2 pencereyi kapatin.
echo.
pause
