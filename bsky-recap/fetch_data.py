"""Fetch Bluesky data for the daily recap video.

Steps:
1. Get all follows + followers for cee.wtf -> mutuals
2. Scan cee's recent feed for replies/reposts/quotes -> interaction scores
3. Fetch each mutual's last-24h posts with engagement stats
Outputs: recap_data.json
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://public.api.bsky.app/xrpc"
ACTOR = "cee.wtf"
MY_DID = "did:plc:xb2urvqt5f4zzccjs46hysbf"


def get(endpoint, **params):
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{API}/{endpoint}?{qs}"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cee-daily-recap/0.1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if attempt == 3:
                print(f"  FAILED {endpoint}: {e}")
                return None
            time.sleep(1.5 * (attempt + 1))


def paginate(endpoint, list_key, **params):
    items = []
    cursor = None
    while True:
        data = get(endpoint, cursor=cursor, limit=100, **params)
        if not data:
            break
        items.extend(data.get(list_key, []))
        cursor = data.get("cursor")
        if not cursor:
            break
    return items


print("Fetching follows...")
follows = paginate("app.bsky.graph.getFollows", "follows", actor=ACTOR)
print(f"  {len(follows)} follows")

print("Fetching followers...")
followers = paginate("app.bsky.graph.getFollowers", "followers", actor=ACTOR)
print(f"  {len(followers)} followers")

follower_dids = {f["did"] for f in followers}
mutuals = {f["did"]: f for f in follows if f["did"] in follower_dids}
print(f"  {len(mutuals)} mutuals")

# --- interaction scoring: scan cee's recent posts for replies/quotes/reposts ---
print("Scanning cee's feed for interactions...")
my_feed = []
cursor = None
for _ in range(8):  # up to ~800 items
    data = get("app.bsky.feed.getAuthorFeed", actor=ACTOR, limit=100, cursor=cursor)
    if not data:
        break
    my_feed.extend(data.get("feed", []))
    cursor = data.get("cursor")
    if not cursor:
        break
print(f"  {len(my_feed)} feed items")

interaction = {}  # did -> score
def bump(did, amt):
    if did and did != MY_DID:
        interaction[did] = interaction.get(did, 0) + amt

for item in my_feed:
    post = item.get("post", {})
    record = post.get("record", {})
    # reply by cee -> who they replied to
    reply = item.get("reply")
    if reply and post.get("author", {}).get("did") == MY_DID:
        parent_author = (reply.get("parent") or {}).get("author") or {}
        bump(parent_author.get("did"), 3)
    # repost by cee
    reason = item.get("reason")
    if reason and reason.get("$type", "").endswith("reasonRepost"):
        bump(post.get("author", {}).get("did"), 2)
    # quote post by cee
    embed = record.get("embed") or {}
    et = embed.get("$type", "")
    if post.get("author", {}).get("did") == MY_DID and "record" in et:
        rec = embed.get("record") or {}
        inner = rec.get("record") or rec
        uri = inner.get("uri", "")
        if uri.startswith("at://did:"):
            bump(uri.split("/")[2], 2)
    # mentions in cee's own posts
    if post.get("author", {}).get("did") == MY_DID:
        for facet in record.get("facets") or []:
            for feat in facet.get("features", []):
                if feat.get("$type", "").endswith("mention"):
                    bump(feat.get("did"), 1)

scored_mutuals = sorted(
    mutuals.values(),
    key=lambda m: interaction.get(m["did"], 0),
    reverse=True,
)
top = [m for m in scored_mutuals if interaction.get(m["did"], 0) > 0]
print(f"  {len(top)} mutuals with interaction signal")
for m in top[:20]:
    print(f"    {interaction[m['did']]:3d}  {m['handle']}  ({m.get('displayName','')})")

# --- fetch last-24h posts from top mutuals (and a sample of the rest) ---
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
targets = top[:30] + [m for m in scored_mutuals if interaction.get(m["did"], 0) == 0][:30]
print(f"Fetching 24h activity for {len(targets)} mutuals...")

activity = []
for i, m in enumerate(targets):
    feed = get("app.bsky.feed.getAuthorFeed", actor=m["did"], limit=30,
               filter="posts_no_replies")
    if not feed:
        continue
    posts = []
    for item in feed.get("feed", []):
        post = item.get("post", {})
        reason = item.get("reason")
        if reason:  # skip their reposts; we want original content
            continue
        rec = post.get("record", {})
        created = rec.get("createdAt", "")
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts < cutoff:
            continue
        embed = post.get("embed") or {}
        images = []
        if embed.get("$type", "").startswith("app.bsky.embed.images"):
            images = [img.get("thumb") or img.get("fullsize") for img in embed.get("images", [])]
        elif embed.get("$type", "").startswith("app.bsky.embed.recordWithMedia"):
            media = embed.get("media", {})
            if media.get("$type", "").startswith("app.bsky.embed.images"):
                images = [img.get("thumb") or img.get("fullsize") for img in media.get("images", [])]
        posts.append({
            "uri": post.get("uri"),
            "text": rec.get("text", ""),
            "createdAt": created,
            "likes": post.get("likeCount", 0),
            "reposts": post.get("repostCount", 0),
            "replies": post.get("replyCount", 0),
            "quotes": post.get("quoteCount", 0),
            "images": images,
        })
    if posts:
        activity.append({
            "did": m["did"],
            "handle": m["handle"],
            "displayName": m.get("displayName") or m["handle"],
            "avatar": m.get("avatar"),
            "score": interaction.get(m["did"], 0),
            "posts": posts,
        })
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(targets)} checked, {len(activity)} active")

print(f"  {len(activity)} mutuals active in last 24h")

out = {
    "generated": datetime.now(timezone.utc).isoformat(),
    "actor": ACTOR,
    "mutual_count": len(mutuals),
    "activity": activity,
}
with open("recap_data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("Wrote recap_data.json")
