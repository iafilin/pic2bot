import os
import time
import threading
from time import sleep

from telebot import types
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QDialog, QFormLayout, \
    QDialogButtonBox, QFileDialog, QRadioButton, QCheckBox
from telegram_bot import TelegramBot
from config import load_config, save_config


class ScreenshotAppUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Автоматическая отправка скриншотов")

        screen_geometry = self.frameGeometry()
        center_point = self.screen().availableGeometry().center()
        screen_geometry.moveCenter(center_point)
        self.move(screen_geometry.topLeft())

        # set size
        self.resize(700, 500)

        # Загрузка конфигурации
        self.config = load_config()

        # Инициализация переменных
        self.bot = None
        self.running = False
        self.monitoring = False  # Заменили watching на monitoring

        # Инициализация UI
        self.setup_ui()

    def setup_ui(self):
        """Настроить элементы пользовательского интерфейса."""
        main_layout = QVBoxLayout(self)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(QLabel("Логи:"))
        main_layout.addWidget(self.log_text)

        # Загружаем лог из файла, если он есть
        if os.path.exists("activity.txt"):
            try:
                with open("activity.txt", "r", encoding="utf-8") as f:
                    self.log_text.append(f.read())
            except Exception as e:
                self.add_log(f"Ошибка при чтении лог-файла: {e}")

        # Папка для мониторинга
        self.folder_input = QLineEdit(self.config.get("watch_folder", ""))
        self.folder_input.setReadOnly(True)
        main_layout.addWidget(QLabel("Выберите папку для мониторинга:"))
        main_layout.addWidget(self.folder_input)

        # Кнопка выбора папки
        self.choose_folder_button = QPushButton("Выбрать папку")
        self.choose_folder_button.clicked.connect(self.select_folder)
        main_layout.addWidget(self.choose_folder_button)

        # Убираем чекбокс "Отправить только новые скриншоты", поведение по умолчанию
        # Галочка для отправки всех скриншотов в одно сообщение
        self.single_message_radio = QRadioButton("Отправлять все скриншоты в одно сообщение (обновление)")
        self.single_message_radio.setChecked(self.config.get("single_message", False))
        self.single_message_radio.toggled.connect(self.update_config_radio)
        main_layout.addWidget(self.single_message_radio)

        # Радиокнопка для отправки отдельных скриншотов
        self.separate_message_radio = QRadioButton("Отправлять каждый скриншот как отдельное сообщение")
        self.separate_message_radio.setChecked(not self.config.get("single_message", False))
        self.separate_message_radio.toggled.connect(self.update_config_radio)
        main_layout.addWidget(self.separate_message_radio)

        # Галочка удаления исходников
        self.delete_sources_checkbox = QCheckBox("Удалить исходники после отправки")
        self.delete_sources_checkbox.setChecked(self.config.get("delete_sources", False))
        self.delete_sources_checkbox.stateChanged.connect(self.update_config_checkboxes)
        main_layout.addWidget(self.delete_sources_checkbox)

        # Статус
        self.status_label = QLabel("Статус: Ожидание")
        main_layout.addWidget(self.status_label)

        # Кнопки
        self.start_button = QPushButton("Запустить")
        self.stop_button = QPushButton("Остановить")
        self.setup_button = QPushButton("Настройки Telegram")

        self.stop_button.setEnabled(False)  # Сделать кнопку неактивной по умолчанию

        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.setup_button.clicked.connect(self.setup_telegram)

        self.start_button.setEnabled(self.config.get("watch_folder") is not None)

        main_layout.addWidget(self.start_button)
        main_layout.addWidget(self.stop_button)
        main_layout.addWidget(self.setup_button)

    def update_config_checkboxes(self):
        """Обновить конфигурацию с состоянием чекбоксов."""
        self.config["delete_sources"] = self.delete_sources_checkbox.isChecked()
        save_config(self.config)

    def update_config_radio(self):
        """Обновить конфигурацию с состоянием радиокнопок."""
        self.config["single_message"] = self.single_message_radio.isChecked()
        save_config(self.config)

    def add_log(self, message):
        msg = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
        """Добавляет сообщение в лог."""
        self.log_text.append(msg)
        """Сохраняем в файл"""
        with open("activity.txt", "a", encoding="utf-8") as f:
            f.write(msg)

    def select_folder(self):
        """Выбор папки для мониторинга."""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder_input.setText(folder)
            self.config["watch_folder"] = folder
            save_config(self.config)

            # Включаем кнопку "Запустить", если папка выбрана
            self.start_button.setEnabled(True)

    def start_monitoring(self):
        """Запуск мониторинга папки."""
        folder = self.config.get("watch_folder")
        if not folder or not os.path.isdir(folder):
            self.add_log("Ошибка: Неверная папка для мониторинга.")
            return

        # Инициализация бота, если не был инициализирован
        if self.bot is None:
            try:
                self.bot = TelegramBot(self.config["TOKEN"])
            except Exception as e:
                self.add_log(f"Ошибка при инициализации бота: {e}")
                return

        self.running = True
        self.monitoring = True  # Обновили переменную
        self.add_log(f"Запуск мониторинга папки: {folder}")

        # Отключаем кнопку "Запустить" и включаем кнопку "Остановить"
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Запуск потока для мониторинга
        threading.Thread(target=self.monitor_folder, daemon=True).start()



    def stop_monitoring(self):
        """Останавливает мониторинг папки."""
        self.monitoring = False
        self.running = False
        self.add_log("Мониторинг папки остановлен")
        self.status_label.setText("Мониторинг папки остановлен")

        # Включаем кнопку "Запустить" и отключаем кнопку "Остановить"
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def monitor_folder(self):
        """Мониторит папку на наличие новых скриншотов."""
        event_handler = FileSystemEventHandler()
        event_handler.on_created = self.on_new_file

        observer = Observer()
        observer.schedule(event_handler, self.config["watch_folder"], recursive=False)
        observer.start()

        while self.monitoring:
            time.sleep(1)

        observer.stop()
        observer.join()

    def on_new_file(self, event):
        sleep(1)
        """Обрабатывает создание нового файла в папке."""
        path = os.path.normpath(event.src_path)
        if not event.is_directory and path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.add_log(f"Новый файл найден: {path}")
            self.send_screenshot(path)

    def send_screenshot(self, file_path):
        """Отправляет скриншот в Telegram в зависимости от выбранной опции."""
        try:
            with open(file_path, 'rb') as photo:
                # Если выбран вариант отправки всех скриншотов в одно сообщение
                if self.single_message_radio.isChecked():
                    # Получаем текущее время для метки
                    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

                    # Если в конфиге нет message_id, отправляем первое сообщение
                    if self.config.get("message_id") is None:
                        message = self.bot.send_photo(self.config["CHAT_ID"], photo,
                                                      caption=f"Обновлено: {current_time}")
                        # Сохраняем message_id для последующего обновления
                        self.config["message_id"] = message.message_id
                        save_config(self.config)
                    else:
                        # Обновляем существующее сообщение
                        media = types.InputMediaPhoto(photo, caption=f"Обновлено: {current_time}")
                        self.bot.edit_message_media(
                            chat_id=self.config["CHAT_ID"],
                            message_id=self.config["message_id"],
                            media=media
                        )
                else:
                    # Если чекбокс не активирован, отправляем каждое изображение как отдельное сообщение
                    self.bot.send_photo(self.config["CHAT_ID"], photo)

            self.add_log(f"Скриншот {file_path} успешно отправлен.")
            self.status_label.setText(f"Скриншот {file_path} отправлен")

            # Удаляем файл после отправки
            if self.delete_sources_checkbox.isChecked():
                os.remove(file_path)
                self.add_log(f"Скриншот {file_path} удален после отправки.")

        except Exception as e:
            if "message to edit not found" in str(e) or "MESSAGE_ID_INVALID" in str(e):
                self.config["message_id"] = None
                save_config(self.config)
                self.send_screenshot(file_path)
            else:
                error_message = f"Ошибка при создании и отправке скриншота: {e}"
                self.add_log(error_message)
                self.status_label.setText(error_message)

    def setup_telegram(self):
        """Открывает диалог для настройки Telegram."""
        dialog = TelegramSetupDialog(self)
        dialog.exec()

class TelegramSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка Telegram")
        self.setGeometry(100, 100, 300, 200)
        layout = QFormLayout(self)

        self.token_input = QLineEdit(self.parent().config.get("TOKEN", ""))
        self.chat_id_input = QLineEdit(self.parent().config.get("CHAT_ID", ""))

        layout.addRow("Токен бота:", self.token_input)
        layout.addRow("ID чата:", self.chat_id_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)

        layout.addRow(button_box)

    def save_settings(self):
        """Сохраняет настройки Telegram в конфигурации."""
        token = self.token_input.text()
        chat_id = self.chat_id_input.text()

        if ":" not in token:
            self.parent().add_log("Неверный формат токена. Убедитесь, что токен содержит двоеточие.")
            return

        self.parent().config["TOKEN"] = token
        self.parent().config["CHAT_ID"] = chat_id
        save_config(self.parent().config)
        self.parent().add_log("Настройки Telegram сохранены.")
        self.accept()
