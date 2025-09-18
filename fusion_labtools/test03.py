import time, re, os, tempfile

def generate_temp_file_name(original_path):
    safe_path = re.sub(r'[^\w.-]', '_', original_path)[-50:]
    timestamp = time.time_ns()  # nanosecond precision, guaranteed to be unique
    return os.path.join(tempfile.gettempdir(), f"temp_{safe_path}_{timestamp}")
