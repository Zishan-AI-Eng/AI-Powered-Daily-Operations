import logging
import os
import sys

def get_logger(name: str) -> logging.Logger:
    """
    Project ke liye centralized logger. 
    Yeh terminal aur logs/system.log dono jagah log karega.
    """
    logger = logging.getLogger(name)
    
    # Agar logger ke paas pehle se handlers hain toh naye add na karo (duplicate logs se bachne ke liye)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG) # Lowest level set kiya, handlers apni marzi se filter karenge

        # 1. Console Handler (Terminal par dikhane ke liye)
        c_handler = logging.StreamHandler(sys.stdout)
        c_handler.setLevel(logging.INFO) # Terminal par sirf INFO aur ERROR dikhayenge

        # 2. File Handler (File mein save karne ke liye)
        # Project ki root mein 'logs' folder banayega
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        f_handler = logging.FileHandler(os.path.join(log_dir, "system.log"))
        f_handler.setLevel(logging.DEBUG) # File mein DEBUG level (choti choti details) bhi save hogi

        # Formatting set karein (Time - Module - Level - Message)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        c_handler.setFormatter(formatter)
        f_handler.setFormatter(formatter)

        # Handlers ko logger mein add karein
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

    return logger