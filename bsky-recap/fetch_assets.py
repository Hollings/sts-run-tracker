"""Download avatars and post images for the featured mutuals."""
import json
import os
import urllib.request

data = json.load(open("recap_data.json", encoding="utf-8"))
os.makedirs("assets", exist_ok=True)

featured = [
    "norvid-studies.bsky.social", "freyja-lynx.dev", "scoiattolo.mountainherder.xyz",
    "quillmatiq.com", "isolyth.dev", "minormobius.bsky.social", "thebadcode.com",
    "brennan.computer", "gracekind.net", "lathrys.at", "minormobius.bsky.social",
]

def dl(url, path):
    if os.path.exists(path):
        return
    req = urllib.request.Request(url, headers={"User-Agent": "cee-daily-recap/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
        f.write(r.read())
    print("ok", path)

for a in data["activity"]:
    h = a["handle"]
    if h not in featured:
        continue
    safe = h.replace(".", "_")
    if a.get("avatar"):
        dl(a["avatar"], f"assets/avatar_{safe}.jpg")
    # post images for norvid poetry post + quillmatiq fixed-me post
    for p in a["posts"]:
        if h == "norvid-studies.bsky.social" and p["text"].startswith("the water grows cold"):
            for i, img in enumerate(p["images"]):
                dl(img, f"assets/post_norvid_{i}.jpg")
        if h == "quillmatiq.com" and p["text"].startswith("Btw, I was right"):
            for i, img in enumerate(p["images"]):
                dl(img, f"assets/post_quillmatiq_{i}.jpg")

# also grab cee's own avatar for the intro/outro
dl("https://cdn.bsky.app/img/avatar/plain/did:plc:xb2urvqt5f4zzccjs46hysbf/bafkreigyfwcdlgfoo73jsjas2mtmcwzugmg37gdobl6psgfmz47lwuvncu",
   "assets/avatar_cee.jpg")
print("done")
