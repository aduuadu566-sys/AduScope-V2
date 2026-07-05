# AduScope

AI-powered talent-discovery app. Flet (Python) frontend, OpenRouter (free
tier — no credit card, works worldwide) for question generation, grading,
and final talent analysis.

## What's built (Phase 1 + delight features)
- Screen 1: Language selection (22 languages)
- Screen 2: Name entry
- Screen 3: Personalized welcome
- Screen 4: 10-question adaptive interview (open text only, no multiple choice;
  each question is uniquely AI-generated based on name/language/time, and
  difficulty adapts to your previous answer's grade). Each answer also gets a
  live "mood emoji" tone read (no audio needed — just the writing style).
- Screen 5: Final result — talent title, summary, personality analysis,
  3-year roadmap, animated staggered reveal + confetti, a code-drawn talent
  **badge** (icon + color chosen by AI, rendered with no external image API),
  and a **Talent Twin** match (a well-known figure with a similar strength).
- **Daily Journal Mode**: one short AI reflection question per day, streak
  counter, and history — all stored locally on-device via
  page.client_storage (no server, no account needed).
- **Compare with a Friend**: generates a small shareable text "code" (no
  internet/bluetooth pairing needed) — a friend pastes it into their app and
  the AI writes a short comparison of how your two talents complement each
  other.
- Auto day/night theme.
- **Splash screen**: an animated branded intro (logo badge + app name +
  "Powered by AI" note) shown for ~1.5s before the language screen — the
  polished "outer look" before entering the app itself.

## Not yet built (would need a real backend/server)
- Voice input/output (Speech-to-Text / Text-to-Speech)
- Downloadable certificate image/PDF + real platform share sheet
- Global leaderboard (needs a shared database — Flet alone is client-only, so
  this was intentionally left out to keep everything code-only/serverless)
- Extra encryption layer for stored answers

## Setup

cd aduscope
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
flet run main.py

## Building the Android APK

### Option A — You have a computer with Flutter/Android SDK
1. Install Flutter: https://docs.flutter.dev/get-started/install
2. Install Android Studio (for the Android SDK + emulator)
3. Run flutter doctor and fix any red items
4. From the project folder, run: flet build apk
5. The finished .apk will be in build/apk/

### Option B — Phone only, no computer (recommended for you)
The build happens for free in GitHub's cloud — no laptop, no terminal.

1. Create a free GitHub account (github.com) if you don't have one.
2. Create a new repository, set it to Private.
3. Upload all the project files using "Add file → Upload files". Make sure
   the folder structure is preserved, especially .github/workflows/build-apk.yml
4. Add your API key as a secret: Repo → Settings → Secrets and variables →
   Actions → "New repository secret" → Name: OPENROUTER_API_KEY → Value: your key
5. Trigger the build: go to "Actions" tab → "Build AduScope APK" → "Run workflow"
6. Wait 5–10 minutes. When done, open that run → scroll to "Artifacts" →
   download aduscope-apk (a zip containing your .apk)
7. On your phone: unzip it, tap the .apk file, allow "install from unknown
   sources" if asked, and install AduScope like any normal app.

## Notes on the AI key
Never commit your real API key. config.py reads it from the
OPENROUTER_API_KEY environment variable so it's never hardcoded in source.
OpenRouter works worldwide with no VPN needed and no credit card required —
sign up free at https://openrouter.ai, go to "Keys", and create a new key.
