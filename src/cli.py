"""Entrada CLI del agente local."""

try:
    from agent import main
except ModuleNotFoundError:
    from src.agent import main


if __name__ == "__main__":
    main()
