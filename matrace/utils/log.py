
import logging


def get_logger(name: str, path: str):

  logger = logging.getLogger(name)

  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.DEBUG)

  file_handler = logging.FileHandler(path)
  file_handler.setLevel(logging.INFO)

  formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

  console_handler.setFormatter(formatter)
  file_handler.setFormatter(formatter)

  logger.addHandler(console_handler)
  logger.addHandler(file_handler)

  logger.setLevel(logging.DEBUG)

  return logger
