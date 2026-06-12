# Brief: Bluesky Daily Recap — Produced Hype Video

## What this is

Every day, generate a <60s vertical video (9:16, 1080x1920) recapping the last 24 hours
of activity from cee's (@cee.wtf) Bluesky mutuals. The video gets posted back to Bluesky.

It must feel like a **produced hype edit** — the kind a human video editor with taste and
an unhealthy meme diet would cut. Reference points, in order of importance:

1. **Smash Bros / fighting game combo videos** — hitstop, impact, escalation, a finisher
2. **Anime AMVs / hype trailers** — story arc, tension, payoff, needle-drop sync
3. **MTV promos / channel idents** — bold type, absurd juxtaposition, visual confidence
4. **Gen Z brainrot edits** — speed, chaos, self-awareness, things that should not be there

## The one-sentence goal

Make the viewer (cee) feel **invested in their moots** — excited about their friends'
bangers, like they're watching a highlight reel of people they love going off.

## How to get the data

Run this first — it does ALL the Bluesky fetching in one go, no API fiddling needed:

```bash
cd bsky-recap
PYTHONIOENCODING=utf-8 python fetch_bsky.py            # defaults: cee.wtf, last 24h
```

It produces `data/recap_data.json` (everything, machine-readable), `data/SUMMARY.txt`
(human-readable digest — read this first), and `data/assets/` (downloaded avatars and
post images, local paths embedded in the JSON). Fields per post: text, timestamp,
likes/reposts/replies/quotes, bsky.app URL, local image paths, quoted-post text if it's
a quote post. Per mutual: interaction score (how much cee actually engages with them —
weight these people more), display name, avatar path, all their 24h posts.

## What the previous attempts got wrong (read this — it's the whole reason you exist)

Three iterations were made by a previous session. Each was rejected. The failure was
structural and kept reappearing despite surface changes:

- **v1 "Spotify Wrapped":** 8 sequential cards: badge + avatar + quote + like counter.
  A slideshow.
- **v2 "combo video":** same 8 cards with whip-pans, impact frames, screen shake, combo
  counter, glitches layered on top. Still a slideshow — *flashing lights don't change
  the skeleton*.
- **v3 "story":** narration lines + the same quote-card layout, uniform 1-bar scenes.
  Better arc, still template: every scene was visibly the same layout machine with
  different text.

Diagnosed failure modes — avoid ALL of these:

1. **Uniform segmentation.** Equal-duration scenes aligned to bars read as PowerPoint.
   Pacing must vary wildly: a 4-second dramatic hold, then five 0.4s cuts, then a 2s
   scene. Let the *content* dictate duration.
2. **One layout engine.** If every post appears as [avatar circle + name + quote text
   with accent bar], it's a template no matter what surrounds it. Every scene should be
   a *different visual idea*: a fake phone lockscreen notification, a giant tweet
   screenshot tumbling in 3D, text crawling like a news ticker, a single word filling
   the whole frame, a fake group-chat UI typing in real time, a "breaking news" lower
   third, a fighting-game character-select screen, a slow zoom into someone's avatar
   with text orbiting it. The post content should *inhabit* a scene, not fill a slot.
3. **Post-FX as a substitute for motion.** Shake/flash/chromatic aberration over a
   static layout is lipstick. Real motion = elements with their own trajectories,
   layered parallax, things entering/exiting constantly, camera moves (pan across a
   large canvas, not just zoom), rotation in depth.
4. **Showing posts instead of telling a story.** "Here's a post, here are its stats" is
   a database query. The story is in the *relationships*: who's beefing, what meme
   spread across multiple accounts the same day, who went viral and didn't expect it,
   callbacks (someone's 2am poetry recontextualized at the end). Mine the data for
   narrative, write narration that talks TO the viewer ("your timeline woke up and
   chose violence"), and make posts appear as *evidence* in that story.
5. **Wasting the climax.** Build to something. The best ending discovered so far: the
   video revealing it knows it's a video (on June 11 a mutual literally posted "ask an
   LLM to render a video with ffmpeg" and another posted "ominous output from fable" —
   the recap ended with "YOU'RE WATCHING IT"). Look for whatever today's equivalent is
   in the fresh data. If there's a self-referential or dramatic-irony angle, take it.

## What good looks like

- **A cold open** that grabs in 1 second.
- **An arc**: normal day -> escalation -> twist -> climax -> button. Acts should FEEL
  different (color, tempo, density, layout language all shift per act).
- **Scene variety**: if you pause on any two scenes and they look like the same
  template, redo one of them.
- **Beat-synced but not beat-enslaved**: cuts land on hits, but scene lengths vary.
  Tempo changes, drops, a tape-stop or silence moment are encouraged — silence is the
  loudest effect in a hype video.
- **Sound design**: music synthesized to fit the arc (or sliced/arranged procedurally),
  plus SFX coupled to picture: whooshes on cuts, sub impacts on slams, risers into
  reveals. Audio you generate yourself — no copyrighted tracks.
- **Specificity**: real handles, real avatars, real quotes (verbatim — never paraphrase
  someone's post into something they didn't say; trimming with "..." is fine), real
  numbers. The likes counts and post counts are part of the hype ("246 PEOPLE FELT
  THAT").
- **The viewer is cee**: they know these people. In-jokes land. Weight the mutuals with
  high interaction scores — those are the friends. But a 0-score mutual with a massive
  banger still makes the cut.

## Constraints & environment notes

- Windows. Always run python with `PYTHONIOENCODING=utf-8` (display names contain
  emoji; cp1252 console will crash). Never put emoji in python source.
- Available: ffmpeg (full build), Python 3.13 with numpy, scipy, Pillow. No internet
  audio/video downloads.
- Fonts in C:/Windows/Fonts: seguibl.ttf (Segoe UI Black — good for slams),
  segoeuib.ttf, bahnschrift.ttf, impact.ttf, consolab.ttf (mono), arial/ariblk.ttf.
  Strip chars >U+FFFF before drawing text (PIL chokes on emoji glyphs anyway).
- Bluesky video limits: 60s, 100MB. Render high quality then re-encode (~crf 26) for
  the postable file.
- Pipe raw RGB frames straight into ffmpeg stdin (no PNG intermediate) — proven fast.
  30fps is fine. 1080x1920.
- A 45s render (~1350 frames, Pillow+numpy compositing) takes a few minutes. Preview
  individual frames as PNGs BEFORE committing to a full render, and extract frames
  from the final mp4 to verify (you can read images). Check: text fits the frame, no
  overlaps, animations mid-state look right, audio waveform/spectrogram sanity.
- Music: synthesizing from scratch with numpy/scipy works well (drums, bass, pads,
  arps, risers, sidechain ducking, tape-stop varispeed). 124-140 BPM. Master through
  tanh, normalize to ~-1dB peak.

## Deliverables

1. `recap.mp4` (archival quality) + `recap_post.mp4` (<100MB, postable)
2. Re-runnable scripts committed to git (fetch -> music -> render), so tomorrow's recap
   is one command away. Keep curation (which posts, what story) as clearly-marked
   editable data near the top of the render script.
