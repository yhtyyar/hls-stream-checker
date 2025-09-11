#!/usr/bin/env python3
"""
Тестирование веб API HLS Stream Checker
"""

import requests
import time
import json

def test_api_endpoints():
    """Тестирование основных endpoint'ов API"""
    base_url = "http://localhost:5000"
    
    print("🚀 Тестирование веб API HLS Stream Checker")
    print("=" * 50)
    
    # Тест 1: Проверка главной страницы
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Главная страница: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка доступа к главной странице: {e}")
    
    # Тест 2: Проверка API конфигурации
    try:
        response = requests.get(f"{base_url}/api/config")
        if response.status_code == 200:
            config_data = response.json()
            print(f"✅ API конфигурации: {response.status_code}")
            print(f"   - Количество каналов по умолчанию: {config_data.get('defaultChannelCount')}")
            print(f"   - Длительность по умолчанию: {config_data.get('defaultDurationMinutes')} минут")
        else:
            print(f"❌ API конфигурации: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка доступа к API конфигурации: {e}")
    
    # Тест 3: Проверка статуса проверки
    try:
        response = requests.get(f"{base_url}/api/check/status")
        if response.status_code == 200:
            status_data = response.json()
            print(f"✅ API статуса проверки: {response.status_code}")
            print(f"   - Проверка запущена: {status_data.get('isChecking')}")
            print(f"   - Процесс запущен: {status_data.get('isProcessRunning')}")
        else:
            print(f"❌ API статуса проверки: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка доступа к API статуса проверки: {e}")
    
    # Тест 4: Проверка API логов
    try:
        response = requests.get(f"{base_url}/api/logs")
        if response.status_code == 200:
            logs_data = response.json()
            print(f"✅ API логов: {response.status_code}")
            print(f"   - Всего записей в логах: {logs_data.get('total', 0)}")
        else:
            print(f"❌ API логов: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка доступа к API логов: {e}")
    
    # Тест 5: Проверка API данных
    try:
        response = requests.get(f"{base_url}/api/data/files")
        if response.status_code == 200:
            files_data = response.json()
            print(f"✅ API файлов данных: {response.status_code}")
            print(f"   - CSV файлов: {len(files_data.get('csv', []))}")
            print(f"   - JSON файлов: {len(files_data.get('json', []))}")
        else:
            print(f"❌ API файлов данных: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка доступа к API файлов данных: {e}")
    
    print("=" * 50)
    print("🏁 Тестирование завершено")

if __name__ == "__main__":
    test_api_endpoints()