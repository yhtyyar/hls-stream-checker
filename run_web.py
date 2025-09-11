#!/usr/bin/env python3
"""
Запуск веб-интерфейса HLS Stream Checker
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    """Запуск веб-сервера"""
    # Получение пути к проекту
    project_root = Path(__file__).parent.absolute()
    
    # Добавление проекта в путь Python
    sys.path.insert(0, str(project_root))
    
    # Импорт и запуск API напрямую
    try:
        from api import app
        print("🚀 Запуск веб-интерфейса HLS Stream Checker...")
        print("🌐 Доступен по адресу: http://localhost:5000")
        print("⌨️  Нажмите Ctrl+C для остановки")
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()