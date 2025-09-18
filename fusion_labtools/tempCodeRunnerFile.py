import time, re, os, tempfile

def safe_temp_name(original_path):
    # Sanitize and shorten
    safe_path = re.sub(r'[^\w.-]', '_', original_path)[-50:]
    timestamp = str(time.time())[6:-3]
    return os.path.join(tempfile.gettempdir(), f"temp_{safe_path}_{timestamp}")