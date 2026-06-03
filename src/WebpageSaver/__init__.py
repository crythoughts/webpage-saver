from WebpageSaver.Config import Config
import logging

logging.basicConfig(
    level = logging.INFO,
    #filename='app.log',
    #encoding='utf-8',
)

app = None
config = Config()
