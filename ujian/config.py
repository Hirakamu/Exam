from pathlib import Path
from datetime import timezone, timedelta


ROOT = Path(__file__).parent
USERDATA = Path(ROOT/"data")
EXAMDATA = Path(USERDATA / "exam")

SCHOOLJSON = USERDATA / "school.json"
ROUTESJSON = USERDATA / "route.json"
STUDENTSJSON = USERDATA / "siswa.json"
PAGEDIR = USERDATA / "htmls"

EXAMTMPL = EXAMDATA / "examtmp.json"
SCHEDULE = EXAMDATA / "schedule.json"

# timezone placeholder if needed elsewhere
UTC = timezone.utc
WIB = timezone(timedelta(hours=7), "WIB")

# app
APP_NAME = "HiraExam"
APP_VERSION = "beta-0.63"

# database
DB_ENGINE = "postgresql"
DB_HOST = "192.168.18.156"
DB_NAME = "ujian_sman2cikpus"
DB_USER = "ujian_sman2cikpus"
DB_PASSWORD = "sman2cikarangpusat@paknanang"
DB_PORT = 5432
DB = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST
}

# logging
LOG_FILE = USERDATA / "logs" / "app.log"
LOG_LEVEL = "INFO"

# exam flags
ONGOING_EXAM = True

# routes
FULL_PREFIX = "https://ujian.sman2cikpus.sch.id"

# secret & server
SECRET_KEY = "movingforbrightfuture"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000
