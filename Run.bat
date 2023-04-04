@echo off
for /f "usebackq tokens=* delims= " %%x in (`chdir`) do set var=%var% %%x
cd "%var:~1%"
call activate
python Game.py
pause