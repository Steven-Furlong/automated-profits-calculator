import os 
import pandas as pd
from etsy_client import get_shop_receipts

def fetch_all_receipts():
    all_receipts []
    offset = 0
    limit = 100
