@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0..\.."
if not exist "design\receiver\build" mkdir "design\receiver\build"
cl /nologo /EHsc /std:c++17 /W4 design\receiver\usb3_capture.cpp /Fo:design\receiver\build\usb3_capture.obj /Fe:design\receiver\build\usb3_capture.exe /link setupapi.lib
set "capture_build_exit=%errorlevel%"
popd
exit /b %capture_build_exit%
