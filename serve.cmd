@echo off
REM Local preview. Opening index.html directly (file://) will NOT work --
REM the browser blocks fetching the spec and data files.
echo Serving at http://localhost:8777  --  press Ctrl+C to stop
start "" http://localhost:8777
python -m http.server 8777 --bind 127.0.0.1
