@echo off
REM ============================================================
REM  AUTHORIZE GOOGLE DRIVE CHO COLAB (1 lan)
REM  - mo trinh duyet -> cap quyen Drive -> Enter
REM  - base model 18GB se duoc cache vao Drive -> session sau khong tai lai
REM ============================================================
chcp 65001 > nul
cd /d "C:\Users\Admin\Desktop\New folder"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"C:\Users\Admin\AppData\Local\Programs\Python\Python312\Scripts\colab.exe" drivemount -s orn-gpu1
echo.
echo --- xong. Neu thay "Mounting Google Drive to '/content/drive'" thi OK ---
pause
