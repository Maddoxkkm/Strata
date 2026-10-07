# Stop everything Strata: the HTTP server (serve/server.py), the engine, and anything holding port 8080.
# Deliberately matches only python.exe running serve/server.py, never the shell that calls this script.
$targets = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -and $_.CommandLine -like '*server.py*' -and $_.CommandLine -like '*--config*') -or
    ($_.Name -in @('strata.exe', 'strata-device.exe'))
}
foreach ($p in $targets) {
    Write-Output ("stopping {0} ({1})" -f $p.ProcessId, $p.Name)
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 5
$left = (Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -and $_.CommandLine -like '*server.py*' -and $_.CommandLine -like '*--config*') -or
    ($_.Name -in @('strata.exe', 'strata-device.exe'))
}).Count
$listeners = (netstat -ano | Select-String ':8080\s.*LISTENING' | Measure-Object).Count
Write-Output ("remaining strata processes: {0}; port 8080 listeners: {1}" -f $left, $listeners)
