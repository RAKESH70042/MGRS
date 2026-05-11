@echo off

IF "%1"=="run"            GOTO run
IF "%1"=="frontend"       GOTO frontend
IF "%1"=="llama-server"   GOTO llama_server
IF "%1"=="download-model" GOTO download_model

echo.
echo  Usage:
echo   make.bat run            - Start FastAPI backend (port 8000)
echo   make.bat frontend       - Start Streamlit UI
echo   make.bat llama-server   - Start local MedGemma (port 8080)
echo   make.bat download-model - Download MedGemma GGUF files
echo.
GOTO end

:run
echo Starting FastAPI backend on http://localhost:8000 ...
call venv\Scripts\activate.bat
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
GOTO end


 :frontend
echo Starting Streamlit UI...
call venv\Scripts\activate.bat
streamlit run streamlit_app.py
GOTO end


