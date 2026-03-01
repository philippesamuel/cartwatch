from dotenv import load_dotenv

from app.utils import find_env

load_dotenv(find_env())
