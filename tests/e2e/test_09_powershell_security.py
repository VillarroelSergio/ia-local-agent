import pytest

from src.tools_catalog.local import validate_powershell_command


ALLOWED_COMMANDS = [
    "Get-Date",
    "Get-Process",
    "Get-Service",
    "Get-ChildItem",
    "Test-Path .",
]

BLOCKED_COMMANDS = [
    "Remove-Item file.txt",
    "Set-ExecutionPolicy Bypass",
    "Invoke-WebRequest https://example.com",
    "Start-Process calc.exe",
    "powershell -EncodedCommand AAAA",
    "Get-Date; Get-Process",
    "Get-Date && Get-Process",
    "Get-Date || Get-Process",
    "Get-Date > out.txt",
    "Get-Date < in.txt",
    "Get-Date $(Get-Process)",
    "Get-Date ` whoami",
]


@pytest.mark.parametrize("command", ALLOWED_COMMANDS)
def test_allowed_powershell_commands_validate(command):
    assert validate_powershell_command(command) is None


@pytest.mark.parametrize("command", BLOCKED_COMMANDS)
def test_blocked_powershell_commands_return_controlled_error(command):
    error = validate_powershell_command(command)
    assert isinstance(error, str)
    assert error
