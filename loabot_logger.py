import logging

logger = logging.getLogger('Global')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formater = logging.Formatter('%(asctime)s - %(levelname)s %(name)s:%(msg)s', '%y-%m-%d, %H:%M') 
handler.setFormatter(formater)
logger.addHandler(handler)
logger.propagate = False