$sw = [System.Diagnostics.Stopwatch]::StartNew()
Invoke-WebRequest http://keel.tom-mendy.local/ -UseBasicParsing | Out-Null
$sw.Stop()
$sw.ElapsedMilliseconds
