"""One-shot Bluesky data pull for the daily recap video.

Fetches everything in a single run -- no further API fiddling needed:
  1. Profile for the target account
  2. All follows + followers -> mutuals
  3. Interaction scores (scans the target's recent feed for replies/reposts/quotes/mentions)
  4. Every mutual's posts from the last N hours, with engagement stats, post URLs,
     image URLs, and quoted-post context
  5. Downloads avatars (all active mutuals) and post images (top posts) to data/assets/

Outputs:
  data/recap_data.json   -- everything, machine-readable, local asset paths embedded
  data/SUMMARY.txt       -- human-readable digest (read this first)
  data/assets/*.jpg      -- avatars + post images

Usage:
  PYTHONIOENCODING=utf-8 python fetch_bsky.py [--handle cee.wtf] [--hours 24]
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://public.api.bsky.app/xrpc"


def get(endpoint, **params):
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{API}/{endpoint}?{qs}"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "daily-recap/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if attempt == 3:
                print(f"  FAILED {endpoint}: {e}")
                return None
            time.sleep(1.5 * (attempt + 1))


def paginate(endpoint, list_key, **params):
    items, cursor = [], None
    while True:
        d = get(endpoint, cursor=cursor, limit=100, **params)
        if not d:
            break
        items.extend(d.get(list_key, []))
        cursor = d.get("cursor")
        if not cursor:
            break
    return items


def safe_name(handle):
    return re.sub(r"[^A-Za-z0-9_-]", "_", handle)


def download(url, path):
    if os.path.exists(path):
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "daily-recap/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
            f.write(r.read())
        return True
    except Exception as e:
        print(f"  image download failed: {e}")
        return False


def post_url(handle, uri):
    # at://did:plc:xxx/app.bsky.feed.post/RKEY -> https://bsky.app/profile/handle/post/RKEY
    rkey = uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def extract_images(post):
    embed = post.get("embed") or {}
    et = embed.get("$type", "")
    imgs = []
    if et.startswith("app.bsky.embed.images"):
        imgs = embed.get("images", [])
    elif et.startswith("app.bsky.embed.recordWithMedia"):
        media = embed.get("media", {})
        if media.get("$type", "").startswith("app.bsky.embed.images"):
            imgs = media.get("images", [])
    return [i.get("thumb") or i.get("fullsize") for i in imgs if i.get("thumb") or i.get("fullsize")]


def extract_quote_context(post):
    """if this is a quote post, return {author_handle, text} of the quoted post"""
    embed = post.get("embed") or {}
    et = embed.get("$type", "")
    rec = None
    if et.startswith("app.bsky.embed.record#view"):
        rec = embed.get("record")
    elif et.startswith("app.bsky.embed.recordWithMedia"):
        rec = (embed.get("record") or {}).get("record")
    if not rec or "value" not in rec:
        return None
    return {
        "author": (rec.get("author") or {}).get("handle", "?"),
        "text": (rec.get("value") or {}).get("text", "")[:300],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default="cee.wtf")
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out, "assets"), exist_ok=True)

    print(f"Profile: {args.handle}")
    profile = get("app.bsky.actor.getProfile", actor=args.handle)
    if not profile:
        sys.exit("could not fetch profile")
    my_did = profile["did"]
    if profile.get("avatar"):
        p = os.path.join(args.out, "assets", "avatar__self.jpg")
        if download(profile["avatar"], p):
            profile["avatar_path"] = p

    print("Follows / followers...")
    follows = paginate("app.bsky.graph.getFollows", "follows", actor=args.handle)
    followers = paginate("app.bsky.graph.getFollowers", "followers", actor=args.handle)
    follower_dids = {f["did"] for f in followers}
    mutuals = {f["did"]: f for f in follows if f["did"] in follower_dids}
    print(f"  {len(follows)} follows, {len(followers)} followers, {len(mutuals)} mutuals")

    print("Interaction scan (target's recent feed)...")
    my_feed, cursor = [], None
    for _ in range(8):
        d = get("app.bsky.feed.getAuthorFeed", actor=args.handle, limit=100, cursor=cursor)
        if not d:
            break
        my_feed.extend(d.get("feed", []))
        cursor = d.get("cursor")
        if not cursor:
            break

    interaction = {}
    def bump(did, amt):
        if did and did != my_did:
            interaction[did] = interaction.get(did, 0) + amt

    for item in my_feed:
        post = item.get("post", {})
        record = post.get("record", {})
        mine = post.get("author", {}).get("did") == my_did
        reply = item.get("reply")
        if reply and mine:
            bump(((reply.get("parent") or {}).get("author") or {}).get("did"), 3)
        reason = item.get("reason")
        if reason and reason.get("$type", "").endswith("reasonRepost"):
            bump(post.get("author", {}).get("did"), 2)
        embed = record.get("embed") or {}
        if mine and "record" in embed.get("$type", ""):
            rec = embed.get("record") or {}
            inner = rec.get("record") or rec
            uri = inner.get("uri", "")
            if uri.startswith("at://did:"):
                bump(uri.split("/")[2], 2)
        if mine:
            for facet in record.get("facets") or []:
                for feat in facet.get("features", []):
                    if feat.get("$type", "").endswith("mention"):
                        bump(feat.get("did"), 1)
    print(f"  {sum(1 for d in mutuals if interaction.get(d, 0) > 0)} mutuals with interaction signal")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    ordered = sorted(mutuals.values(), key=lambda m: interaction.get(m["did"], 0), reverse=True)
    print(f"Fetching {args.hours:.0f}h activity for all {len(ordered)} mutuals...")

    activity = []
    for i, m in enumerate(ordered):
        feed = get("app.bsky.feed.getAuthorFeed", actor=m["did"], limit=40,
                   filter="posts_no_replies")
        if not feed:
            continue
        posts = []
        for item in feed.get("feed", []):
            post = item.get("post", {})
            if item.get("reason"):       # skip their reposts of others
                continue
            rec = post.get("record", {})
            try:
                ts = datetime.fromisoformat(rec.get("createdAt", "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts < cutoff:
                continue
            posts.append({
                "uri": post.get("uri"),
                "url": post_url(m["handle"], post.get("uri", "")),
                "text": rec.get("text", ""),
                "createdAt": rec.get("createdAt"),
                "likes": post.get("likeCount", 0),
                "reposts": post.get("repostCount", 0),
                "replies": post.get("replyCount", 0),
                "quotes": post.get("quoteCount", 0),
                "image_urls": extract_images(post),
                "image_paths": [],
                "quoting": extract_quote_context(post),
            })
        if posts:
            activity.append({
                "did": m["did"],
                "handle": m["handle"],
                "displayName": m.get("displayName") or m["handle"],
                "avatar_url": m.get("avatar"),
                "avatar_path": None,
                "interaction_score": interaction.get(m["did"], 0),
                "posts": sorted(posts, key=lambda p: p["createdAt"]),
            })
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(ordered)} checked, {len(activity)} active")

    print(f"  {len(activity)} mutuals active in window")

    # ---- download avatars (all active) ----
    print("Downloading avatars...")
    for a in activity:
        if a["avatar_url"]:
            p = os.path.join(args.out, "assets", f"avatar_{safe_name(a['handle'])}.jpg")
            if download(a["avatar_url"], p):
                a["avatar_path"] = p

    # ---- download images for top posts ----
    def engagement(p):
        return p["likes"] + 2 * p["reposts"] + p["replies"] + 2 * p["quotes"]

    all_posts = [(a, p) for a in activity for p in a["posts"]]
    with_imgs = [(a, p) for a, p in all_posts if p["image_urls"]]
    with_imgs.sort(key=lambda ap: engagement(ap[1]) + ap[0]["interaction_score"], reverse=True)
    print(f"Downloading images for top {min(40, len(with_imgs))} image posts...")
    for a, p in with_imgs[:40]:
        rkey = p["uri"].rsplit("/", 1)[-1]
        for j, url in enumerate(p["image_urls"][:4]):
            path = os.path.join(args.out, "assets",
                                f"post_{safe_name(a['handle'])}_{rkey}_{j}.jpg")
            if download(url, path):
                p["image_paths"].append(path)

    # ---- stats + top posts ----
    total_posts = sum(len(a["posts"]) for a in activity)
    total_likes = sum(p["likes"] for a in activity for p in a["posts"])
    ranked = sorted(all_posts, key=lambda ap: engagement(ap[1]) + ap[0]["interaction_score"] * 0.5,
                    reverse=True)
    top_posts = [{
        "handle": a["handle"], "displayName": a["displayName"],
        "interaction_score": a["interaction_score"], "engagement": engagement(p), **p,
    } for a, p in ranked[:30]]

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": args.hours,
        "profile": profile,
        "stats": {
            "mutual_count": len(mutuals),
            "active_mutuals": len(activity),
            "total_posts": total_posts,
            "total_likes_received": total_likes,
        },
        "top_posts": top_posts,
        "mutuals": activity,
    }
    jpath = os.path.join(args.out, "recap_data.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"Wrote {jpath}")

    # ---- human-readable summary ----
    lines = []
    lines.append(f"DAILY RECAP DATA -- @{args.handle} -- last {args.hours:.0f}h "
                 f"-- generated {out['generated_at'][:16]}Z")
    lines.append(f"{len(mutuals)} mutuals | {len(activity)} active | "
                 f"{total_posts} posts | {total_likes} likes received")
    lines.append("")
    lines.append("=== MUTUALS BY INTERACTION SCORE (these are the friends) ===")
    for a in activity[:25]:
        if a["interaction_score"] > 0:
            lines.append(f"  {a['interaction_score']:4d}  @{a['handle']:36s} "
                         f"{a['displayName'][:40]}  ({len(a['posts'])} posts)")
    lines.append("")
    lines.append("=== TOP 30 POSTS (engagement + friendship weighting) ===")
    for tp in top_posts:
        text = tp["text"].replace("\n", " / ")[:200]
        img = f" [{len(tp['image_paths'])} img]" if tp["image_paths"] else ""
        q = f" [quoting @{tp['quoting']['author']}]" if tp.get("quoting") else ""
        lines.append(f"  {tp['likes']:4d}L {tp['reposts']:3d}R  "
                     f"@{tp['handle'][:30]:30s} {tp['createdAt'][11:16]}  {text}{img}{q}")
    lines.append("")
    lines.append("=== FULL FIREHOSE (every active mutual, chronological per mutual) ===")
    for a in activity:
        lines.append(f"--- @{a['handle']} ({a['displayName']}) "
                     f"score={a['interaction_score']} ---")
        for p in a["posts"]:
            text = p["text"].replace("\n", " / ")[:240]
            img = f" [{len(p['image_paths'])}img]" if p["image_paths"] else ""
            q = f" [quoting @{p['quoting']['author']}: {p['quoting']['text'][:60]}]" if p.get("quoting") else ""
            lines.append(f"  {p['createdAt'][11:16]} {p['likes']:4d}L  {text}{img}{q}")
    spath = os.path.join(args.out, "SUMMARY.txt")
    with open(spath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {spath}")
    print("Done. Read data/SUMMARY.txt first, then mine data/recap_data.json.")


if __name__ == "__main__":
    main()
