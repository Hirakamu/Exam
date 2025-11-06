import logging
from psycopg2 import pool, sql
import json
import os
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    with open(os.path.join(ROOT , "data/config.yaml"), "r") as f:
        config = yaml.safe_load(f) or {}
except FileNotFoundError:
    logger.warning("config.yaml not found, using empty config")
    config = {}

DBCONFIG = {
    "dbname": f"{config.get('database', {}).get('name', '')}",
    "user": f"{config.get('database', {}).get('user', '')}",
    "password": f"{config.get('database', {}).get('password', '')}",
    "host": f"{config.get('database', {}).get('host', '')}"
}

try:
    dbPool = pool.ThreadedConnectionPool(1, 50, **DBCONFIG)
except Exception:
    logger.exception("Failed to create DB connection pool")
    dbPool = None

def getDB():
    if not dbPool:
        raise RuntimeError("DB pool is not initialized")
    return dbPool.getconn()
def putDB(conn):
    if not dbPool:
        return
    try:
        dbPool.putconn(conn)
    except Exception:
        logger.exception("Failed to return connection to pool")

baseDir = os.path.join(os.path.dirname(__file__), "data")
if not os.path.isdir(baseDir):
    logger.warning("Students base directory %s not found", baseDir)
    exit()

jsonFiles = ["X.json","XI.json","XII.json"]
conn = getDB()
try:
    with conn:
        with conn.cursor() as cur:
            for fileName in jsonFiles:
                with open(os.path.join(baseDir, fileName), "r") as f:
                    data = json.load(f)

                grade = data.get("grade")
                sections = data.get("sections", {})

                if not grade:
                    logger.warning("Skipping %s: missing grade", os.path.join(baseDir, fileName))
                    continue

                cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(grade)))
                cur.execute(sql.SQL(
                    """
                    CREATE TABLE {} (
                        nis VARCHAR(20) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        grade VARCHAR(10) NOT NULL
                        );
                    """
                ).format(sql.Identifier(grade)))
                for section, students in sections.items():
                    for s in students:
                        cur.execute(
                            sql.SQL("INSERT INTO {} (nis, name, class) VALUES (%s, %s, %s)").format(sql.Identifier(grade)),
                            (s.get("nis"), s.get("name"), s.get("class") if s.get("class") else section),
                        )
    print("Success")
finally:
    putDB(conn)