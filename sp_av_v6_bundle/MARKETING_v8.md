# AV v8 — demo landing copy, outreach angle, SEO (marketing skills, brand-checked)

Brand voice check (`/marketing:brand-review`): short, physical, numbers with sources, no hype words.
Removed from drafts: "revolutionary", "AI-powered", "industry-leading". Kept claims we can prove in the AV.
No Artechs / laser / sheet-metal claims anywhere — SP sells 3D printing + TPU heat-transfer apparel.

## Landing page (Vercel copy of `servo_mount_v8.html`)
**H1:** See if it fits, bolts up and holds — before you print it.
**Sub:** One link. Spin it, explode it, measure it, load it until something gives. Every number says where it came from.
**4 cards (one per phase):**
- **LOAD** — tap any part: material, mass and print time, straight from the slicer.
- **FIT** — every hole coloured by how *your* printer prints holes. Calipers built in.
- **SECURE** — the build plays itself: inserts at 240 °C, screws from the side they really go in.
- **TEST** — drag the load. Watch the stress, see what breaks first, and why the servo gives up before the bracket does.
**Proof line:** Built on Ender 3 S1 Pro data · PrusaSlicer G-code · PyBullet-checked to 0.1 %.
**CTA:** "Get an AV for your build — from $450" · footer: Prototyped on Ender 3 S1 Pro · Toronto, Canada

## Outreach angle (`/sp-sales`, `/sp-local-pitch`)
Target: first-time hardware founders + local makers (GTA maker spaces, Kickstarter "coming soon" pages).
> "Backers don't trust renders. Send them a link where your bracket survives 0.5 kg and the stall warning
> fires at 0.51 — with the formula one tap away. I build those. First one free for a testimonial."

Email sequence (`/marketing:email-sequence`): D0 the demo link · D3 "what breaks first?" GIF · D7 offer ($450 / $1,200 with TEST).
Campaign (`/marketing:campaign-plan`): 2 weeks · 1 reel/week from the TEST phase · 10 DMs/day to "coming soon" Kickstarters.
Performance report (`/marketing:performance-report`): nothing shipped yet → no data to report; baseline KPIs to track:
link opens, phase reach (hash tells you which phase people share), reply rate.

## SEO (`/marketing:seo-audit`, page not live yet)
- Title: "Interactive 3D assembly viewer with stress check — Shawarma Prints"
- Meta description: "Spin, explode, measure and load-test a 3D-printed part in your browser. Tolerances from real printer data, hand-calc stress, one shareable link."
- Keywords: interactive assembly viewer, 3D print tolerance, servo bracket stress, Kickstarter 3D product viewer, exploded view link
- Technical: single static HTML (fast, no JS framework); add `og:image` = `shots_v8/servo_mount/v8_test_1280_dark.png`; canonical URL once the Vercel domain exists.
