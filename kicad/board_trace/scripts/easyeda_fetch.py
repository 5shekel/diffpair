import json, urllib.request

url = "https://easyeda.com/api/products/C7501881/components?version=6.5.36"
req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
data = json.load(urllib.request.urlopen(req, timeout=40))
res = data["result"]
print("title:", res["title"])
pd = res.get("packageDetail") or {}
print("packageDetail keys:", list(pd.keys()))
ds = pd.get("dataStr")
print("dataStr type:", type(ds))
if isinstance(ds, str):
    obj = json.loads(ds)
else:
    obj = ds
print("dataStr keys:", list(obj.keys()))
head = obj.get("head"); 
print("head:", json.dumps(head)[:800] if head else head)
shape = obj.get("shape") or []
print("shape count:", len(shape))
# summarize record types
from collections import Counter
c = Counter(s.split("~")[0] for s in shape)
print("record types:", c)
for s in shape[:25]:
    print("  ", s[:160])
json.dump(res, open(r"C:\Users\user\AppData\Local\Temp\opencode\dp\C7501881_easyeda.json","w"))
