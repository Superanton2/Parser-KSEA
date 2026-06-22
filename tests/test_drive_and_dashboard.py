import os
import pytest
from google_sheets_manager import GoogleSheetsManager
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "KSE_Agrocenter_Parser")

# Live integration test that uploads to Drive and writes the Dashboard. Opt in
# explicitly so it never runs (and mutates real data) in CI or a normal run.
pytestmark = pytest.mark.skipif(
    not (os.getenv("RUN_INTEGRATION_TESTS") and os.path.exists(CREDENTIALS_PATH)),
    reason="integration test: set RUN_INTEGRATION_TESTS=1 and provide credentials.json",
)


@pytest.fixture(scope="module")
def sheet_manager():
    """Initialize the Google Sheets connection."""
    manager = GoogleSheetsManager(CREDENTIALS_PATH, SPREADSHEET_NAME)
    return manager


@pytest.fixture(scope="module")
def drive_folder_id(sheet_manager):
    """Retrieve the folder ID from Bot_Params."""
    params = sheet_manager.get_bot_params()
    folder_id = params.get("drive_folder_id")
    if not folder_id:
        pytest.skip("drive_folder_id not found in Bot_Params. Skipping the upload test.")
    return folder_id


def test_end_to_end_upload_and_save(sheet_manager, drive_folder_id):
    """
    End-to-End test: Uploads a real file to Google Drive and saves the
    generated link directly to the Dashboard worksheet for manual verification.
    """

    # 1. Get the absolute path to the test CSV file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    test_file = os.path.join(project_root, "google_search_results.csv")

    assert os.path.exists(test_file), f"Local file not found! Path checked: {test_file}"

    # 2. Upload the file to Google Drive
    print(f"\nUploading {test_file} to Drive folder: {drive_folder_id}...")
    link = sheet_manager.upload_file_to_drive(test_file, drive_folder_id)

    assert isinstance(link, str)
    assert link.startswith("https://"), f"Upload failed, returned: {link}"
    print(f"Upload successful! Link: {link}")

    # 3. Save the actual generated link to the Dashboard
    # We pass the same link for both raw and sorted just for this test
    print("Saving links to Dashboard worksheet...")
    sheet_manager.save_links_to_dashboard(raw_link=link, sorted_link=link)
    print("Done! Open your Google Sheet 'Dashboard' tab to see the real links.")

    # 4. Verify that the Dashboard was actually updated
    worksheet = sheet_manager.sh.worksheet("Dashboard")
    data = worksheet.get_all_values()

    saved_links = {}
    for row in data:
        if len(row) >= 2:
            saved_links[row[0].strip()] = row[1].strip()

    assert "raw_csv_link" in saved_links
    assert saved_links["raw_csv_link"] == link