@echo off
rem Run the hipBLASLt tuner with the same environment tools\hip\rebuild-windows.bat sets up for the build
rem (ROCm + MSVC vcvars64).  Needed because the exe is an MSVC build: launched from git-bash alone it cannot
rem resolve the UCRT DLLs (api-ms-win-crt-*.dll).
rem
rem   tools\hip\run-tuner.bat --workspace-mib 32 --case f16,64,1280,2560,1280 --tuning-out logs\rows.txt
setlocal EnableDelayedExpansion
for %%I in ("%~dp0..\..") do set "SRC=%%~fI"
if not defined ROCM_VENV set "ROCM_VENV=%SRC%\.rocm-win"
if not defined BUILD_DIR set "BUILD_DIR=%SRC%\build-hip-win"
for /f "delims=" %%R in ('"%ROCM_VENV%\Scripts\rocm-sdk.exe" path --root') do set "ROCM=%%R"
if not exist "%ROCM%\bin" (echo ROCm not found in "%ROCM%" & exit /b 1)
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VS="
if exist "%VSWHERE%" for /f "delims=" %%V in ('"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath') do set "VS=%%V"
if not defined VS (echo Visual Studio Build Tools with the C++ workload are needed & exit /b 1)
call "%VS%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set "HIP_PLATFORM=amd"
set "HIP_PATH=%ROCM%"
set "ROCM_PATH=%ROCM%"
set "PATH=%ROCM%\bin;%ROCM%\lib\llvm\bin;%SystemRoot%\System32;%PATH%"
cd /d "%SRC%"
echo run-tuner: %*
"%BUILD_DIR%\tune_hipblaslt.exe" %*
exit /b %ERRORLEVEL%
