#!/usr/bin/env python3
"""
Модуль для отправки email отчетов в HLS Stream Checker
"""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class EmailSender:
    """Класс для отправки email отчетов"""
    
    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 25):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        
    def create_report_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: List[Path]
    ) -> MIMEMultipart:
        """Создает email сообщение с отчетом"""
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = "HLS Stream Checker <noreply@hls-checker.local>"
        msg["To"] = to_email
        
        # Добавляем текст сообщения
        msg.attach(MIMEText(body, "plain"))
        
        # Добавляем вложения
        for attachment in attachments:
            if not attachment.exists():
                logger.warning(f"Файл вложения не найден: {attachment}")
                continue
                
            # Создаем вложение
            with open(attachment, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            
            # Кодируем вложение
            encoders.encode_base64(part)
            
            # Добавляем заголовки
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={attachment.name}"
            )
            msg.attach(part)
        
        return msg
    
    def send_report(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: List[Path]
    ) -> bool:
        """Отправляет email с отчетом"""
        try:
            msg = self.create_report_email(to_email, subject, body, attachments)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.send_message(msg)
                
            logger.info("📧 Отчет успешно отправлен на %s", to_email)
            return True
            
        except Exception as e:
            logger.error("❌ Ошибка при отправке отчета: %s", e)
            return False
