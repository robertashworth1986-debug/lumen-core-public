$ErrorActionPreference = 'Stop'
Set-Location 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code'
python 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\REBUILD_SINGLE_TRUTH_AND_REVALIDATE.py'
if (Test-Path 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\seed_validation_readout.txt') { Start-Process 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\seed_validation_readout.txt' }
if (Test-Path 'C:\LumaTrader\dashboard\seed_validation_readout.html') { Start-Process 'C:\LumaTrader\dashboard\seed_validation_readout.html' }