import subprocess
import sys


def test_cli_starts_and_exits_with_salir():
    completed = subprocess.run(
        [sys.executable, "src/cli.py"],
        input="salir\n",
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0
    assert "Agente IA local iniciado" in completed.stdout
    assert "Puedes pedirme tareas como" in completed.stdout
    assert "resume la ventana actual" in completed.stdout
