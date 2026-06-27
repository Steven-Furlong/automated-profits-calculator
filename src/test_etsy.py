import os
from etsy_client import get_shop_receipts

print("SHARED_SECRET:", os.getenv("ETSY_SHARED_SECRET"))
print("API_KEY:", os.getenv("ETSY_API_KEY"))
print("ACCESS_TOKEN:", os.getenv("ETSY_ACCESS_TOKEN"))

data = get_shop_receipts(limit=5)
print(data)
