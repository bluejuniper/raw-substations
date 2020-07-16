if (-not (Test-Path bin)) { mkdir bin}
pyinstaller -n connectivity -F connectivity_comp.py
if (Test-Path bin\connectivity.exe) { del bin\connectivity.exe }
if (Test-Path connectivity.exe) { move connectivity.exe bin\connectivity.exe }
