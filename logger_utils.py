import os
import logging
import datetime

class Colors:
    RESET = '\033[0m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, use_colors=True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
        
        # Define colors for each log level
        self.LEVEL_COLORS = {
            logging.DEBUG: Colors.BRIGHT_BLACK,
            logging.INFO: Colors.GREEN,
            logging.WARNING: Colors.YELLOW,
            logging.ERROR: Colors.RED,
            logging.CRITICAL: Colors.BOLD + Colors.RED
        }
    
    def format(self, record):
        # Check for special markers in the message to apply custom colors
        if hasattr(record, 'color') and self.use_colors:
            color = getattr(record, 'color')
            record.msg = f"{color}{record.msg}{Colors.RESET}"
        
        # Apply colors to the level name
        if self.use_colors and record.levelno in self.LEVEL_COLORS:
            color = self.LEVEL_COLORS[record.levelno]
            record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        
        # Format the record using parent formatter
        result = super().format(record)
        
        return result

def setup_logging(script_name='script'):
    """Configure logging with proper formatting and file output
    
    Args:
        script_name (str): Name to use in the log file name
        
    Returns:
        logging.Logger: Configured logger instance
    """
    log_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_directory, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_directory, f'{script_name}_{timestamp}.log')
       
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger
