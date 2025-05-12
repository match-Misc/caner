import os
import sys
import logging

# Set a dummy DATABASE_URL for testing purposes before importing app components
# This is to allow app initialization without a real database connection for these tests.
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add the parent directory to the Python path to allow sibling imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import specific functions from app.py
# We need to set up a Flask app context to make this work,
# as some functions might rely on app.static_folder or other app configurations.
from app import app, download_and_manage_xxxlutz_vouchers, download_menu_hg_pdf

# Configure basic logging for the test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_voucher_download():
    logger.info("Attempting to download XXXLutz voucher...")
    # Create an application context
    with app.app_context():
        success = download_and_manage_xxxlutz_vouchers()
        if success:
            logger.info("XXXLutz voucher download function executed.")
            # Check if the 'neue_gutscheine.pdf' was created
            static_folder = app.static_folder if app.static_folder else "static"
            voucher_path = os.path.join(static_folder, 'vouchers', 'neue_gutscheine.pdf')
            if os.path.exists(voucher_path) and os.path.getsize(voucher_path) > 0:
                logger.info(f"SUCCESS: XXXLutz voucher downloaded to: {voucher_path} (Size: {os.path.getsize(voucher_path)} bytes)")
            else:
                logger.error(f"FAILURE: XXXLutz voucher file not found or empty at: {voucher_path}")
        else:
            logger.error("FAILURE: download_and_manage_xxxlutz_vouchers returned False.")

def test_menu_hg_download():
    logger.info("\nAttempting to download Menu HG PDF...")
    # Create an application context
    with app.app_context():
        # The download_menu_hg_pdf function in app.py currently returns a Flask response
        # or a string tuple for errors. For testing the download itself, we'll check
        # for file creation as it's done within that function.
        
        # Call the function which internally handles the download and returns a response
        # We won't check the response directly, but the file it's supposed to create.
        download_menu_hg_pdf() # This will attempt the download

        static_folder = app.static_folder if app.static_folder else "static"
        menu_pdf_path = os.path.join(static_folder, 'menu', 'menu_hg.pdf') # Corrected path to 'menu'
        
        if os.path.exists(menu_pdf_path) and os.path.getsize(menu_pdf_path) > 0:
            logger.info(f"SUCCESS: Menu HG PDF downloaded to: {menu_pdf_path} (Size: {os.path.getsize(menu_pdf_path)} bytes)")
        else:
            logger.error(f"FAILURE: Menu HG PDF file not found or empty at: {menu_pdf_path}. This might also indicate the download_menu_hg_pdf function returned an error response before creating the file.")

if __name__ == "__main__":
    logger.info("Starting download tests...")
    
    # Ensure the vouchers and menu directories exist
    # This would normally be handled by the app, but good to ensure for a standalone test
    with app.app_context():
        static_folder_path = app.static_folder if app.static_folder else "static"
        vouchers_dir_path = os.path.join(static_folder_path, 'vouchers')
        menu_dir_path = os.path.join(static_folder_path, 'menu') # Added menu directory path
        
        if not os.path.exists(vouchers_dir_path):
            os.makedirs(vouchers_dir_path)
            logger.info(f"Created directory: {vouchers_dir_path}")
        
        if not os.path.exists(menu_dir_path):
            os.makedirs(menu_dir_path)
            logger.info(f"Created directory: {menu_dir_path}")

    test_voucher_download()
    test_menu_hg_download()
    
    logger.info("\nDownload tests finished.")
    logger.info("Please check the log messages above for success/failure.")
    logger.info(f"Voucher files would be in: {os.path.join(os.getcwd(), app.static_folder if app.static_folder else 'static', 'vouchers')}")
    logger.info(f"Menu HG files would be in: {os.path.join(os.getcwd(), app.static_folder if app.static_folder else 'static', 'menu')}")
