import logging
logger = logging.getLogger()
consoleHandler = logging.StreamHandler()
logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
if not logger.handlers:
    #runs only once
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    logger.setLevel(logging.INFO)
    logger.info('loading logger')

