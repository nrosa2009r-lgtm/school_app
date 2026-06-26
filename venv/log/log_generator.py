import logging



def create_log(level,message):
    
    logging.basicConfig(
        filename='logs.log', 
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding="utf-8")
    
    if level == "debug":
        logging.debug(message)
    elif level == "info":
        logging.info(message)
    elif level =="warning":
        logging.warning(message)
    elif level =="error":
        logging.error(message)
    elif level =="critical":
        logging.critical(message)
