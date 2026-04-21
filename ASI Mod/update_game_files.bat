@echo off
REM Skip everything if CI env var exists
if defined CI (
    echo CI environment detected. Skipping update.
    goto :EOF
)

set "SRC=C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\ASI Mod\x64\Release\MGS3-Community-Bugfix-Compilation.asi"
set "VORTEX_MODS=C:\Users\cmkoo\OneDrive\Vortex\metalgearsolid3mc\mods"
set "FOUND=0"

for /d %%D in ("%VORTEX_MODS%\MGS3 Community Bugfix Compilation - Base*") do (
    if exist "%%D\plugins\*.asi" (
        for %%F in ("%%D\plugins\*.asi") do (
            echo Updating: %%F
            copy /Y "%SRC%" "%%F"
            set "FOUND=1"
        )
    )
)

if "%FOUND%"=="0" (
    echo No matching ASI found in Vortex mod folders.
)
