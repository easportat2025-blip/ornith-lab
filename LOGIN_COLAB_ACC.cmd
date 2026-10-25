@echo off
REM ============================================================
REM  DANG NHAP GOOGLE COLAB ACC (buoc trinh duyet)
REM  - chay tuyet dong acc tiep theo chua co token
REM  - hoac: LOGIN_COLAB_ACC.cmd 3   (chon acc so 3)
REM  - xem trang thai: LOGIN_COLAB_ACC.cmd --status
REM ============================================================
chcp 65001 > nul
cd /d "C:\Users\Admin\Desktop\New folder"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python scripts\login_colab_acc.py %*
echo.
echo --- xem trang thai cac acc ---
python scripts\login_colab_acc.py --status
pause
