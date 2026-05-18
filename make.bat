@echo off

IF "%1"=="run"            GOTO run
IF "%1"=="frontend"       GOTO frontend
IF "%1"=="llama-server"   GOTO llama_server
IF "%1"=="llama-gpu"      GOTO llama_gpu
IF "%1"=="llama-amd"      GOTO llama_amd
IF "%1"=="check-gpu"      GOTO check_gpu
IF "%1"=="download-model" GOTO download_model

echo.
echo  Usage:
echo   make.bat run            - Start FastAPI backend (port 8000)
echo   make.bat frontend       - Start Streamlit UI
echo   make.bat llama-server   - Start local MedGemma (port 8080) [CPU only]
echo   make.bat llama-gpu      - Start MedGemma with Nvidia CUDA GPU [company PC]
echo   make.bat llama-amd      - Start MedGemma with AMD Vulkan GPU [laptop, limited]
echo   make.bat check-gpu      - Verify Vulkan sees your GPU
echo   make.bat download-model - Download MedGemma GGUF files
echo.
GOTO end


:run
echo Starting FastAPI backend on http://localhost:8000 ...
call venv\Scripts\activate.bat
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
GOTO end

:frontend
echo Starting Streamlit UI...
call venv\Scripts\activate.bat
streamlit run streamlit_app.py
GOTO end

:llama_server
echo Starting llama-server (CPU only) on http://localhost:8080 ...
call venv\Scripts\activate.bat
llama.cpp\llama-server.exe ^
  -m models\google_medgemma-4b-it-Q4_K_M.gguf ^
  --mmproj models\mmproj-medgemma-4b-it-F16.gguf ^
  --port 8080 --ctx-size 4096 ^
  -ngl 0 --threads 6
GOTO end

:llama_gpu
echo Starting llama-server with Nvidia CUDA GPU on http://localhost:8080 ...
call venv\Scripts\activate.bat
llama.cpp\llama-server.exe ^
  -m models\google_medgemma-4b-it-Q4_K_M.gguf ^
  --mmproj models\mmproj-medgemma-4b-it-F16.gguf ^
  --port 8080 --ctx-size 4096 ^
  -ngl 99 ^
  --threads 4
GOTO end

:llama_amd
echo Starting llama-server with AMD Vulkan GPU (RX 6500M) on http://localhost:8080 ...
echo NOTE: Limited by 7.5GB RAM - running reduced config
call venv\Scripts\activate.bat
llama.cpp\llama-server.exe ^
  -m models\google_medgemma-4b-it-Q4_K_M.gguf ^
  --mmproj models\mmproj-medgemma-4b-it-F16.gguf ^
  --port 8080 --ctx-size 1024 ^
  -ngl 18 ^
  --device Vulkan1 ^
  --threads 2 ^
  -np 1
GOTO end

:check_gpu
echo.
echo Checking Vulkan GPU visibility...
echo.
vulkaninfo --summary 2>nul | findstr /i "deviceName deviceType"
IF ERRORLEVEL 1 (
    echo ERROR: vulkaninfo not found.
    echo Install Vulkan SDK from: https://vulkan.lunarg.com/sdk/home
) ELSE (
    echo.
    echo If you see your GPU above, Vulkan is ready.
)
GOTO end

:download_model
echo Downloading MedGemma GGUF model files...
call venv\Scripts\activate.bat
python scripts\download_model.py
GOTO end

:end