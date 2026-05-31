$sw = [System.Diagnostics.Stopwatch]::StartNew()
Invoke-WebRequest https://keel.home.tom-mendy.com/ -UseBasicParsing | Out-Null
$sw.Stop()
$sw.ElapsedMilliseconds
