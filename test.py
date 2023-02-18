import pyupbit
import numpy as np
from utils import yesterday
import datetime

now = str(datetime.datetime.now())
print(yesterday(now))