rem echo off

cd C:\Users\Owen\Google Drive\Current Work\LexiRumah\lexirumah-data

git checkout cldf/
copy /y raw\forms.csv cldf

CALL  C:\Users\Owen\Anaconda3\Scripts\activate.bat

PUSHD %1
python -m pylexirumah.import
POPD

copy /y cldf\forms.csv raw
git checkout cldf/forms.csv

echo on
pause
