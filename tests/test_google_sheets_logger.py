import os
import time
import uuid
import logging
import pytest
from dotenv import load_dotenv

from google_sheets_manager import GoogleSheetsManager, GoogleSheetsLogHandler

load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "KSE_Agrocenter_Parser")


@pytest.fixture(scope="module")
def sheet_manager():
    """Initialize the Google Sheets connection."""
    manager = GoogleSheetsManager(CREDENTIALS_PATH, SPREADSHEET_NAME)
    return manager


def test_logger_captures_info(sheet_manager):
    """
    Test 1: Verify that logger.info() correctly formats and stores data
    in the internal batch without immediately uploading it.
    """
    print("\n[Test 1] Починаємо перевірку внутрішнього батчу логера...")

    # Use a large batch size so it does NOT auto-trigger upload during this test
    print("[Test 1] Створюємо хендлер з batch_size=100 (щоб уникнути миттєвої відправки)...")
    handler = GoogleSheetsLogHandler(sheet_manager, batch_size=100)
    handler.setFormatter(logging.Formatter('%(message)s'))

    # Create an isolated logger for this test
    print("[Test 1] Налаштовуємо ізольований тестовий логер...")
    test_logger = logging.getLogger("test_internal_batch")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    unique_msg = f"Internal batch test msg: {uuid.uuid4()}"
    print(f"[Test 1] Відправляємо тестове повідомлення: '{unique_msg}'")
    test_logger.info(unique_msg)

    # Check internal batch directly
    batch = handler.log_batch
    print(f"[Test 1] Перевіряємо розмір батчу. Очікуємо 1, маємо: {len(batch)}")
    assert len(batch) == 1, "Log batch should contain exactly 1 record."

    record = batch[0]
    print(f"[Test 1] Збережений запис виглядає так: {record}")

    print("[Test 1] Перевіряємо структуру запису (має бути 3 колонки)...")
    assert len(record) == 3, "Record should have exactly 3 columns: [Level, Time, Message]."

    print(f"[Test 1] Перевіряємо рівень логу (має бути INFO). Фактично: {record[0]}")
    assert record[0] == "INFO", "Log level should be correctly identified as INFO."

    print("[Test 1] Перевіряємо текст повідомлення...")
    assert record[2] == unique_msg, "The logged message does not match what was sent."

    print("[Test 1] Всі перевірки пройдено успішно! Очищуємо логер...")
    # Cleanup
    test_logger.removeHandler(handler)
    print("[Test 1] Тест 1 завершено.")


def test_logger_uploads_to_sheet(sheet_manager):
    """
    Test 2: Verify that flushed logs actually appear in the Google Sheet
    with the correct level and message.
    """
    # Setup handler and logger
    handler = GoogleSheetsLogHandler(sheet_manager, batch_size=10)
    handler.setFormatter(logging.Formatter('%(message)s'))

    test_logger = logging.getLogger("test_e2e_upload")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    # Generate unique messages to search for
    unique_msg_warn = f"E2E Sheet test WARN {uuid.uuid4()}"
    unique_msg_error = f"E2E Sheet test ERROR {uuid.uuid4()}"

    # Send logs
    test_logger.warning(unique_msg_warn)
    test_logger.error(unique_msg_error)

    print("\n[Тест] Save logs (flush call)...")
    handler.flush()

    print("[Тест] Wait to sync with Google...")
    time.sleep(2)

    print("[Тест] Download all data from the sheet Logs...")
    # Fetch data from the Logs worksheet
    worksheet = sheet_manager.sh.worksheet("Logs")
    data = worksheet.get_all_values()
    print(f"[Тест] Successfully loaded {len(data)} lines!")

    # Force upload synchronously using flush()
    handler.flush()

    # Give Google Sheets API a brief moment to process the insertion
    time.sleep(2)


    found_warn = False
    found_error = False

    # Iterate through the sheet to find our unique messages
    for row in data:
        if len(row) >= 3:
            if row[2] == unique_msg_warn:
                found_warn = True
                assert row[0] == "WARNING", "Level for the warning message is incorrect."
            if row[2] == unique_msg_error:
                found_error = True
                assert row[0] == "ERROR", "Level for the error message is incorrect."

    assert found_warn, "Did not find the WARNING test log in the Google Sheet."
    assert found_error, "Did not find the ERROR test log in the Google Sheet."

    # Cleanup
    test_logger.removeHandler(handler)