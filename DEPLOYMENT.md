# 🚀 Руководство по развертыванию HLS Stream Checker на Ubuntu

## 📋 Содержание
1. [Обзор](#обзор)
2. [Требования к системе](#требования-к-системе)
3. [Автоматическая установка](#автоматическая-установка)
4. [Ручная установка](#ручная-установка)
5. [Запуск как системный сервис](#запуск-как-системный-сервис)
6. [Управление и мониторинг](#управление-и-мониторинг)
7. [Устранение неполадок](#устранение-неполадок)

## Обзор

Это руководство описывает процесс развертывания HLS Stream Checker на сервере Ubuntu. Проект включает в себя несколько скриптов для автоматизации установки и настройки:

- `setup_ubuntu.sh` - автоматическая установка зависимостей
- `deploy.sh` - полное развертывание на production сервере
- `run_checker.sh` - удобный скрипт для запуска проверок
- `hls_checker.service` - конфигурация systemd сервиса

## Требования к системе

- Ubuntu 18.04 или выше
- Доступ к интернету для установки зависимостей
- Права sudo для установки системных пакетов
- Как минимум 500MB свободного места на диске

## Автоматическая установка

### Для разработки/тестирования

1. Сделайте скрипт установки исполняемым:
   ```bash
   chmod +x setup_ubuntu.sh
   ```

2. Запустите скрипт установки:
   ```bash
   ./setup_ubuntu.sh
   ```

Скрипт выполнит следующие действия:
- Обновит список пакетов
- Установит Python 3 и pip, если они отсутствуют
- Установит системные зависимости (python3-venv, python3-dev, build-essential)
- Создаст виртуальное окружение `hls_venv`
- Установит Python зависимости из `requirements.txt`
- Создаст необходимые директории для данных

### Для production развертывания

1. Сделайте скрипт развертывания исполняемым:
   ```bash
   chmod +x deploy.sh
   ```

2. Запустите скрипт с правами root:
   ```bash
   sudo ./deploy.sh
   ```

Скрипт выполнит следующие действия:
- Создаст системного пользователя `hlschecker`
- Скопирует файлы в `/opt/hls-checker/`
- Установит правильные права доступа
- Создаст виртуальное окружение и установит зависимости
- Настроит systemd сервис
- Создаст необходимые директории

## Ручная установка

Если вы предпочитаете установить всё вручную:

1. Установите системные зависимости:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv python3-dev build-essential
   ```

2. Создайте виртуальное окружение:
   ```bash
   python3 -m venv hls_venv
   source hls_venv/bin/activate
   ```

3. Установите Python зависимости:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Создайте необходимые директории:
   ```bash
   mkdir -p data/csv data/json logs
   ```

## Запуск как системный сервис

### Установка сервиса

1. После выполнения `deploy.sh` сервис уже настроен. В противном случае:
   ```bash
   sudo cp hls_checker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

2. Запустите сервис:
   ```bash
   sudo systemctl start hls_checker
   ```

3. Включите автозапуск:
   ```bash
   sudo systemctl enable hls_checker
   ```

### Настройка сервиса

Файл сервиса находится в `/etc/systemd/system/hls_checker.service` и может быть изменен:

```ini
[Unit]
Description=HLS Stream Checker Service
After=network.target

[Service]
Type=simple
User=hlschecker
Group=hlschecker
WorkingDirectory=/opt/hls-checker
ExecStart=/opt/hls-checker/hls_venv/bin/python hls_checker_single.py --count all --minutes 10
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Для применения изменений:
```bash
sudo systemctl daemon-reload
sudo systemctl restart hls_checker
```

## Управление и мониторинг

### Запуск проверок вручную

Используйте скрипт `run_checker.sh` для удобного запуска:

```bash
# Сделать исполняемым
chmod +x run_checker.sh

# Запустить проверку 5 каналов на 3 минуты
./run_checker.sh -c 5 -m 3

# Обновить плейлист и проверить все каналы на 10 минут
./run_checker.sh -r -c all -m 10

# Запустить без экспорта данных
./run_checker.sh --no-export
```

### Мониторинг сервиса

Проверить статус сервиса:
```bash
sudo systemctl status hls_checker
```

Просмотр логов в реальном времени:
```bash
sudo journalctl -u hls_checker -f
```

Просмотр последних 100 строк логов:
```bash
sudo journalctl -u hls_checker -n 100
```

### Расположение файлов

После развертывания файлы находятся в:
- Основная директория: `/opt/hls-checker/`
- Виртуальное окружение: `/opt/hls-checker/hls_venv/`
- Данные CSV: `/opt/hls-checker/data/csv/`
- Данные JSON: `/opt/hls-checker/data/json/`
- Логи: `/opt/hls-checker/logs/`

## Устранение неполадок

### Проблемы с зависимостями

Если установка зависимостей не удалась:
```bash
# Активируйте виртуальное окружение
source hls_venv/bin/activate

# Переустановите зависимости
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Проблемы с сервисом

Проверьте статус сервиса:
```bash
sudo systemctl status hls_checker
```

Если сервис не запускается, проверьте логи:
```bash
sudo journalctl -u hls_checker --no-pager
```

Перезапустите сервис:
```bash
sudo systemctl restart hls_checker
```

### Проблемы с правами доступа

Убедитесь, что все файлы принадлежат пользователю `hlschecker`:
```bash
sudo chown -R hlschecker:hlschecker /opt/hls-checker/
```

### Проблемы с сетью

Если проверка не может получить доступ к плейлисту:
1. Проверьте подключение к интернету
2. Убедитесь, что порты 80 и 443 открыты
3. Проверьте настройки прокси, если используется

## 🛠️ Рекомендации по эксплуатации

1. **Регулярный мониторинг**: Настройте оповещения о сбоях сервиса
2. **Ротация логов**: Настройте logrotate для предотвращения переполнения диска
3. **Резервное копирование**: Регулярно архивируйте директорию с данными
4. **Обновления**: Регулярно обновляйте зависимости и проверяйте актуальность кода

## 📞 Поддержка

Если у вас возникли проблемы с развертыванием:
1. Проверьте логи сервиса: `sudo journalctl -u hls_checker`
2. Убедитесь, что все зависимости установлены корректно
3. Проверьте права доступа к файлам и директориям
4. Обратитесь к документации проекта или создайте issue в репозитории