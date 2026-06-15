from WebpageSaver.Config import Config
import logging
import os

os.environ["PW_TEST_SCREENSHOT_NO_FONTS_READY"] = "1" # removing fonts waiting for screenshots

logging.basicConfig(
    level = logging.INFO,
    #filename='app.log',
    #encoding='utf-8',
)

app = None
config = Config()
