# Сборка `TheEdgeOfSilence.exe`

## 1) Подготовка окружения

```powershell
Set-Location "c:\Users\neons\PycharmProjects\TEoS beta 1.0"
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pip install pyinstaller
```

## 2) Очистка старых артефактов

```powershell
Remove-Item -Recurse -Force ".\build\TheEdgeOfSilence" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\dist\TheEdgeOfSilence" -ErrorAction SilentlyContinue
```

Если удаление не проходит, закройте запущенный `TheEdgeOfSilence.exe` и повторите.

## 3) Сборка (onedir)

```powershell
.\venv\Scripts\python.exe -m PyInstaller .\TheEdgeOfSilence.spec --noconfirm
```

Готовый запускной файл:

`dist\TheEdgeOfSilence\TheEdgeOfSilence.exe`

## 4) Что передавать на другой ПК

Передавать нужно всю папку:

`dist\TheEdgeOfSilence\`

Не только один `exe`, потому что рядом лежат шейдеры, библиотеки и ресурсы.

## 5) Быстрые проверки после сборки

```powershell
Test-Path ".\dist\TheEdgeOfSilence\TheEdgeOfSilence.exe"
Test-Path ".\dist\TheEdgeOfSilence\_internal\shaders\water.vert"
```

Обе проверки должны вернуть `True`.

## 6) Где теперь сохраняются настройки и рекорды

Игра сохраняет пользовательские данные в `%APPDATA%\TheEdgeOfSilence\`:

- `config\settings.json`
- `data\teos.db`

Это сделано специально, чтобы запуск через `exe` и через ярлык работал одинаково.
