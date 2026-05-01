from core.game import Game


if __name__ == "__main__":
    try:
        Game().run()
    except ModuleNotFoundError as exc:
        missing_module = getattr(exc, "name", None)
        if missing_module:
            print(f"Missing dependency: {missing_module}")
        else:
            print("Missing dependency detected.")
        print("Use the project's virtual environment:")
        print(r"  .\venv\Scripts\python.exe main.py")
        print("Or install dependencies first:")
        print(r"  .\venv\Scripts\pip.exe install -r requirements.txt")
        raise
    