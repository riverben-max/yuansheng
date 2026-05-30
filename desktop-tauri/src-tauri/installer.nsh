; Yuansheng Data Assistant - NSIS installer hooks
; Auto-kill running instances and clean legacy 1.0.0 artifacts before install.

!macro NSIS_HOOK_PREINSTALL
  DetailPrint "Stopping previous version (if running)..."
  nsExec::ExecToLog 'taskkill /F /IM "yuansheng-data-assistant.exe" /T'
  nsExec::ExecToLog 'taskkill /F /IM "yuansheng-sidecar.exe" /T'
  Sleep 1500

  ; Clean up legacy 1.0.0 artifact: the old broken installer wrote sidecar.exe
  ; directly as a file named "binaries" (no extension) instead of as
  ; "binaries\yuansheng-sidecar.exe". This blocks new installs from creating
  ; the "binaries" directory. Delete only deletes files, not directories,
  ; so this is safe even when "binaries" is already a proper directory.
  IfFileExists "$INSTDIR\binaries" 0 +2
    Delete "$INSTDIR\binaries"
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  DetailPrint "Stopping running instances..."
  nsExec::ExecToLog 'taskkill /F /IM "yuansheng-data-assistant.exe" /T'
  nsExec::ExecToLog 'taskkill /F /IM "yuansheng-sidecar.exe" /T'
  Sleep 1500
!macroend
