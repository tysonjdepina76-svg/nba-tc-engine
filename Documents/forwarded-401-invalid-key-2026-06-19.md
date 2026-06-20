# Fwd: 401 invalid key

**From:** Tyson DePina <tysonjdepina76@gmail.com>
**Date:** Fri, Jun 19, 2026, 5:08 PM
**Subject:** Re: 401 invalid key
**To:** Nick Larsen <hello@theoddsapi.com>

---

Im where I need to be...

On Fri, Jun 19, 2026, 5:05 PM Nick Larsen <hello@theoddsapi.com> wrote:

> Tyson, I figured out what's happening. Nothing on our side is broken,
> and I'll walk you through this so you don't end up in the same loop
> again.
> ================================================================================================================================================
>
> **What I can see in our system at theoddsapi.com:**
>
> ```
> Email           tysonjdepina76@gmail.com   (the one you're writing from)
> API key         toa_live_t5d8p3n1
> Tier            Pro
> Status          ACTIVE, not revoked, not rotated, not exhausted
> Paid            $29 on June 18 (one charge, no duplicate on our side)
> Calls today     0 — your key against our service has never been called
> ```
>
> **Your other email (tysondepina99@gmail.com):**
>
> That email is not with us. There's no record of it in our customer
> database or our Stripe. So if you're getting charged or seeing an
> "exhausted until July 1" error against tysondepina99@gmail.com,
> that's from a different provider you also signed up with — not us.
>
> **Why I know it's a different provider:**
>
> Two specific things in your error don't match anything our system
> produces:
>
> 1. **"Exhausted until July 1"** — we don't have monthly resets. Our
>    Pro tier resets DAILY at midnight UTC (8 PM Eastern / 5 PM Pacific).
>    There's no scenario where our system says "wait until July 1." A
>    different provider uses monthly quotas; we don't.
> 2. **"Key revoked or rotated"** — that's not text our API produces.
>    Our rate-limit error reads "Daily rate limit reached (667 requests
>    per day). Resets at midnight UTC."
>
> Those are two separate accounts at two separate companies.
>
> ---
>
> OPTION 1 — Use OUR service (which you paid $29 for on June 18)
> --------------------------------------------------------------
>
> This is the important part. The likely reason you've been getting
> errors is your code is hitting the OTHER provider's URL, not ours.
> Their URL won't recognize your key from us. Here's exactly how to
> talk to OUR service so this doesn't happen again.
>
> ### Step 1 — Pay attention to OUR URL exactly
>
> Our API base URL is:
>
> ```
> https://api.theoddsapi.com
> ```
>
> Read that letter by letter:
>
> * `api` — subdomain
> * `.theoddsapi.com` — our domain. No hyphens. No "v4" prefix.
>   Nothing after `.com` until your path starts.
>
> If your code is calling anything that LOOKS LIKE OURS BUT ISN'T —
> something with extra hyphens, a "v4" in the path, or any other
> variation — that's the other provider's endpoint and your key from
> us will be rejected. Look at your code now and make sure the URL
> starts exactly with `https://api.theoddsapi.com`.
>
> ### Step 2 — Verify your key works (paste this exact command in terminal)
>
> Open your terminal and paste this exactly, including the backslash
> and the line break:
>
> ```
> curl -H "x-api-key: toa_live_t5d8p3n1" \
>      "https://api.theoddsapi.com/odds/?sport_key=basketball_wnba"
> ```
>
> Three pieces to that command:
>
> * `curl -H "x-api-key: toa_live_t5d8p3n1"` — the header carrying
>   your key. The header name is `x-api-key` (lowercase, with
>   hyphens). Not `Authorization`, not `apiKey`, not `api_key`.
> * `https://api.theoddsapi.com/odds/` — our endpoint for game odds.
> * `?sport_key=basketball_wnba` — query parameter telling us which
>   sport. WNBA is in season right now so you'll get live data back.
>
> ### Step 3 — Expected output
>
> You should see a JSON array come back within about a second.
> Something like:
>
> ```
> [
>   {
>     "id": "abc123...",
>     "sport_key": "basketball_wnba",
>     "commence_time": "2026-06-19T23:00:00Z",
>     "home_team": "...",
>     "away_team": "...",
>     "bookmakers": [ ... ]
>   },
>   ...
> ]
> ```
>
> If you see that, your key works. Done.
>
> ### Step 4 — If you see an error instead
>
> * **`{"detail":"Invalid API key"}`** → check that you copied the
>   exact key from this email: `toa_live_t5d8p3n1`. No spaces. No
>   extra characters. Header name is exactly `x-api-key`.
> * **`{"detail":"Daily rate limit reached..."}`** → you used 667
>   calls today. Comes back at midnight UTC (8 PM Eastern).
> * **Anything mentioning "exhausted until July 1"** → you're hitting
>   the OTHER provider's URL, not ours. Go back to Step 1 and check
>   your URL letter by letter.
> * **Connection refused, DNS not found, anything weird** → reply with
>   the exact error and the exact command you ran, I'll debug it.
>
> ### Step 5 — Verify your account dashboard
>
> You can also confirm your key is active by visiting:
>
> ```
> https://theoddsapi.com/me.html
> ```
>
> Paste your key in the box and you'll see your usage history, tier,
> and remaining quota for the day. That's a visual confirmation that
> you're talking to OUR service, on OUR domain.
>
> ### Step 6 — Your NFL/NCAAF use case for September
>
> NFL preseason opens August 7, regular season Week 1 is September 10.
> NCAAF starts late August. Your Pro tier here covers both. The same
> URL pattern, just swap the sport_key:
>
> ```
> curl -H "x-api-key: toa_live_t5d8p3n1" \
>      "https://api.theoddsapi.com/odds/?sport_key=americanfootball_nfl"
>
> curl -H "x-api-key: toa_live_t5d8p3n1" \
>      "https://api.theoddsapi.com/odds/?sport_key=americanfootball_ncaaf"
> ```
>
> Note the URL is identical to Step 2 — same `https://api.theoddsapi.com`,
> same path, same header. ONLY the sport_key changes.
>
> ---
>
> OPTION 2 — Refund and walk
> --------------------------
>
> If you didn't intend to sign up for our service and just want out of
> the $29 charge from June 18, reply "refund please" and I'll process
> it today. No questions, no fight, no retention attempt.
>
> Reply with either:
>
> * The WNBA curl output from Step 2 (so I can confirm your key works)
> * "Refund please" and I refund the $29 today
>
> — Neil
> TheOddsAPI
>
> On Fri, Jun 19, 2026 at 1:08 PM Nick Larsen <hello@theoddsapi.com> wrote:
>
> > Tyson - will take a look diagnose this for you .  Give me 1-2 hours.
> >
> > On Fri, Jun 19, 2026 at 3:33 PM Tyson DePina <tysonjdepina76@gmail.com> wrote:
> >
> > > THE ERRORVSAYS KEY IS DEAD MY SYSTEM SAYS WAS REVOKED OR ROTATED. It exhausted at 4am ... now dead