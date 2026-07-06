"""
AduScope - Main Application
A Flet (Python -> mobile APK) app that discovers a user's unique talent
through an adaptive, AI-driven 10-question interview.

Run locally:
    export OPENROUTER_API_KEY="sk-or-v1-..."
    flet run main.py

Build APK (after installing Flutter + Android SDK, see README.md):
    flet build apk
"""

import base64
import datetime
import json
import random
import threading
import time

import flet as ft

from config import LANGUAGES, TOTAL_QUESTIONS, LIGHT_THEME, DARK_THEME
import ai_service

JOURNAL_KEY = "aduscope_journal_v1"  # client_storage key: {"streak":int,"last_date":"YYYY-MM-DD","entries":[...]}


# ============================================================================
# Application State
# ============================================================================
class AppState:
    def __init__(self):
        self.language_code = "en"
        self.language_name = "English"
        self.name = ""
        self.history = []          # list of {"question","answer","score","level"}
        self.current_question = ""
        self.question_index = 0    # 0-based, up to TOTAL_QUESTIONS
        self.result = None


# ============================================================================
# Main
# ============================================================================
def main(page: ft.Page):
    page.title = "AduScope"
    page.padding = 0
    page.window_width = 420
    page.window_height = 860
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    state = AppState()

    # -- Auto dark/light theme based on time of day -------------------------
    hour = datetime.datetime.now().hour
    is_night = hour >= 19 or hour < 6
    theme = DARK_THEME if is_night else LIGHT_THEME
    page.bgcolor = theme["bg"]
    page.theme_mode = ft.ThemeMode.DARK if is_night else ft.ThemeMode.LIGHT

    body = ft.Column(
        expand=True,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    page.add(body)

    def set_view(controls: list):
        body.controls = controls
        page.update()

    def show_snack(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    # ------------------------------------------------------------------
    # SCREEN 0: Splash — the outer look before entering the app
    # ------------------------------------------------------------------
    def screen_splash():
        logo_circle = ft.Container(
            content=ft.Icon(ft.Icons.AUTO_AWESOME, size=54, color="white"),
            width=110, height=110, border_radius=55,
            bgcolor=theme["primary"], alignment=ft.alignment.center,
            opacity=0, scale=0.7,
            animate_opacity=700, animate_scale=ft.Animation(700, "easeOutBack"),
        )
        title = ft.Text(
            "AduScope", size=34, weight=ft.FontWeight.BOLD, color=theme["primary"],
            opacity=0, animate_opacity=700,
        )
        subtitle = ft.Text(
            "✨ Discover your unique talent",
            size=14, color=theme["text"], opacity=0, animate_opacity=700,
        )
        powered_by = ft.Text(
            "✨ Powered by AI", size=11, color=theme["accent"],
            opacity=0, animate_opacity=700,
        )

        set_view([
            ft.Container(height=260),
            ft.Container(logo_circle, alignment=ft.alignment.center),
            ft.Container(height=18),
            ft.Container(title, alignment=ft.alignment.center),
            ft.Container(subtitle, alignment=ft.alignment.center),
            ft.Container(height=30),
            ft.Container(powered_by, alignment=ft.alignment.center),
        ])

        def animate_in():
            time.sleep(0.1)
            logo_circle.opacity = 1
            logo_circle.scale = 1
            title.opacity = 1
            page.update()
            time.sleep(0.25)
            subtitle.opacity = 1
            powered_by.opacity = 1
            page.update()
            time.sleep(1.1)
            screen_language()

        threading.Thread(target=animate_in, daemon=True).start()

    # ------------------------------------------------------------------
    # SCREEN 1: Language selection
    # ------------------------------------------------------------------
    def screen_language():
        buttons = []
        for code, native in LANGUAGES:
            buttons.append(
                ft.ElevatedButton(
                    text=native,
                    width=160,
                    color=theme["text"],
                    bgcolor=theme["card"],
                    on_click=lambda e, c=code, n=native: choose_language(c, n),
                )
            )
        grid = ft.GridView(
            expand=True,
            runs_count=2,
            max_extent=180,
            child_aspect_ratio=2.6,
            spacing=10,
            run_spacing=10,
            padding=20,
        )
        grid.controls = buttons

        set_view([
            ft.Container(height=40),
            ft.Text("AduScope", size=32, weight=ft.FontWeight.BOLD, color=theme["primary"]),
            ft.Text("Choose your language / ቋንቋዎን ይምረጡ", size=14, color=theme["text"]),
            ft.Container(grid, expand=True),
        ])

    def choose_language(code: str, native: str):
        state.language_code = code
        state.language_name = native
        screen_name_entry()

    # ------------------------------------------------------------------
    # SCREEN 2: Name entry
    # ------------------------------------------------------------------
    def screen_name_entry():
        name_field = ft.TextField(
            label="Your name" if state.language_code == "en" else "ስምዎ",
            width=280,
            autofocus=True,
            border_color=theme["primary"],
        )

        def on_continue(e):
            if not name_field.value or not name_field.value.strip():
                show_snack("Please enter your name.")
                return
            state.name = name_field.value.strip()
            screen_welcome()

        set_view([
            ft.Container(height=80),
            ft.Text("👋", size=48),
            ft.Container(height=20),
            name_field,
            ft.Container(height=20),
            ft.ElevatedButton(
                "Continue", bgcolor=theme["primary"], color="white",
                width=280, on_click=on_continue,
            ),
        ])

    # ------------------------------------------------------------------
    # SCREEN 3: Welcome
    # ------------------------------------------------------------------
    def screen_welcome():
        welcome_msg = (
            f"እንኳን ደህና መጡ {state.name}፣ ወደ ልዩው ተሰጥኦ መርማሪ AduScope በሰላም ተቀላቅለዋል!"
            if state.language_code == "am"
            else f"Welcome, {state.name}! You've just joined AduScope — let's uncover your talent."
        )

        content = [
            ft.Container(height=100),
            ft.Text("✨", size=56),
            ft.Container(height=16),
            ft.Text(welcome_msg, size=18, text_align=ft.TextAlign.CENTER,
                    color=theme["text"], width=320),
        ]

        def on_start(e):
            start_ai_question(is_first=True)

        content.append(ft.Container(height=30))
        content.append(
            ft.ElevatedButton(
                "Begin" if state.language_code == "en" else "ጀምር",
                bgcolor=theme["primary"], color="white", width=200,
                on_click=on_start,
            )
        )

        set_view(content)

    # ------------------------------------------------------------------
    # SCREEN 4: Adaptive question cycle (AI-driven)
    # ------------------------------------------------------------------
    def screen_loading(msg="Thinking..."):
        set_view([
            ft.Container(height=200),
            ft.ProgressRing(color=theme["primary"]),
            ft.Container(height=16),
            ft.Text(msg, color=theme["text"]),
        ])

    def start_ai_question(is_first: bool):
        screen_loading("Preparing your question...")

        def worker():
            try:
                if is_first:
                    q = ai_service.generate_first_question(
                        state.name, state.language_code, state.language_name
                    )
                else:
                    last_level = state.history[-1]["level"]
                    q = ai_service.generate_next_question(
                        state.history, state.language_name, last_level
                    )
                state.current_question = q
                screen_question()
            except Exception as ex:
                show_snack(f"AI error: {ex}")

        threading.Thread(target=worker, daemon=True).start()

    def screen_question():
        answer_field = ft.TextField(
            label="Your answer" if state.language_code == "en" else "መልስዎ",
            multiline=True, min_lines=4, max_lines=8, width=340,
            border_color=theme["primary"],
        )
        progress = f"{state.question_index + 1} / {TOTAL_QUESTIONS}"

        def on_submit(e):
            if not answer_field.value or not answer_field.value.strip():
                show_snack("Please write an answer.")
                return
            submit_answer(answer_field.value.strip())

        set_view([
            ft.Container(height=40),
            ft.Text(progress, size=14, color=theme["accent"], weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Container(
                ft.Text(state.current_question, size=18, color=theme["text"],
                        text_align=ft.TextAlign.CENTER),
                width=340, padding=16, bgcolor=theme["card"], border_radius=16,
            ),
            ft.Container(height=20),
            answer_field,
            ft.Container(height=16),
            ft.ElevatedButton(
                "Submit" if state.language_code == "en" else "ላክ",
                bgcolor=theme["primary"], color="white", width=200,
                on_click=on_submit,
            ),
        ])

    def submit_answer(answer_text: str):
        screen_loading("Evaluating your answer...")
        question = state.current_question

        def worker():
            try:
                grading = ai_service.grade_answer(question, answer_text, state.language_name)
                state.history.append({
                    "question": question,
                    "answer": answer_text,
                    "score": grading.get("score", 5),
                    "level": grading.get("level", "medium"),
                    "on_topic": grading.get("on_topic", True),
                    "mood_emoji": grading.get("mood_emoji", ""),
                })
                if not grading.get("on_topic", True):
                    show_snack("🛑 That seems off-topic — let's try to stay focused!")
                elif grading.get("mood_emoji"):
                    show_snack(f"{grading['mood_emoji']} tone detected")

                state.question_index += 1
                if state.question_index >= TOTAL_QUESTIONS:
                    finish_interview()
                else:
                    start_ai_question(is_first=False)
            except Exception as ex:
                show_snack(f"AI error: {ex}")

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # SCREEN 5: Final result
    # ------------------------------------------------------------------
    def finish_interview():
        screen_loading("Revealing your talent...")

        def worker():
            try:
                result = ai_service.generate_final_result(
                    state.name, state.history, state.language_name
                )
                try:
                    result["twin"] = ai_service.generate_talent_twin(
                        result.get("talent_title", ""),
                        result.get("talent_summary", ""),
                        state.language_name,
                    )
                except Exception:
                    result["twin"] = None
                try:
                    result["badge"] = ai_service.generate_badge_spec(
                        result.get("talent_title", ""), state.language_name
                    )
                except Exception:
                    result["badge"] = {"icon": "auto_awesome", "color_hex": theme["primary"]}

                state.result = result
                screen_result()
            except Exception as ex:
                show_snack(f"AI error: {ex}")

        threading.Thread(target=worker, daemon=True).start()

    def screen_result():
        r = state.result or {}
        badge = r.get("badge") or {"icon": "auto_awesome", "color_hex": theme["primary"]}
        twin = r.get("twin")

        def on_share(e):
            code = make_compare_code()
            page.set_clipboard(code)
            show_snack("Talent code copied! Paste it to a friend to compare.")

        def on_restart(e):
            state.__init__()
            screen_language()

        def on_journal(e):
            screen_journal_home()

        def on_compare(e):
            screen_compare()

        badge_circle = ft.Container(
            content=ft.Icon(badge.get("icon", "auto_awesome"), size=40, color="white"),
            width=76, height=76, border_radius=38,
            bgcolor=badge.get("color_hex", theme["primary"]),
            alignment=ft.alignment.center,
            opacity=0, animate_opacity=400,
        )

        twin_card = ft.Container(visible=False)
        if twin:
            twin_card = ft.Container(
                ft.Column([
                    ft.Text("🪞 Talent Twin", weight=ft.FontWeight.BOLD, color=theme["accent"]),
                    ft.Text(twin.get("twin_name", ""), size=16, weight=ft.FontWeight.BOLD,
                            color=theme["text"]),
                    ft.Text(twin.get("twin_reason", ""), size=13, color=theme["text"]),
                ]),
                width=340, padding=14, bgcolor=theme["card"], border_radius=16,
                opacity=0, animate_opacity=400,
            )

        title_text = ft.Text(
            r.get("talent_title", "—"), size=26, weight=ft.FontWeight.BOLD,
            color=theme["primary"], text_align=ft.TextAlign.CENTER,
            opacity=0, animate_opacity=400,
        )

        detail_card = ft.Container(
            ft.Column([
                ft.Text(r.get("talent_summary", ""), color=theme["text"]),
                ft.Divider(),
                ft.Text("Personality", weight=ft.FontWeight.BOLD, color=theme["accent"]),
                ft.Text(r.get("personality_analysis", ""), color=theme["text"]),
                ft.Divider(),
                ft.Text("3-Year Roadmap", weight=ft.FontWeight.BOLD, color=theme["accent"]),
                ft.Text(r.get("roadmap", ""), color=theme["text"]),
            ], scroll=ft.ScrollMode.AUTO),
            width=340, height=260, padding=16, bgcolor=theme["card"], border_radius=16,
            opacity=0, animate_opacity=400,
        )

        confetti = ft.Stack(
            [
                ft.Container(
                    ft.Text(random.choice(["🎉", "✨", "🏆", "🌟"]), size=22),
                    left=random.randint(10, 320), top=-30,
                    animate_position=1200 + i * 120,
                )
                for i in range(10)
            ],
            width=340, height=1,
        )

        set_view([
            ft.Container(height=20),
            confetti,
            badge_circle,
            ft.Container(height=8),
            title_text,
            ft.Container(height=10),
            detail_card,
            twin_card,
            ft.Container(height=16),
            ft.Row([
                ft.ElevatedButton("Share / Copy Code", bgcolor=theme["accent"], color="black",
                                  on_click=on_share),
                ft.OutlinedButton("Restart", on_click=on_restart),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12, wrap=True),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("📓 Daily Journal", on_click=on_journal),
                ft.TextButton("🤝 Compare with Friend", on_click=on_compare),
            ], alignment=ft.MainAxisAlignment.CENTER, wrap=True),
            ft.Container(height=20),
        ])

        def reveal():
            time.sleep(0.15)
            badge_circle.opacity = 1
            title_text.opacity = 1
            page.update()
            time.sleep(0.2)
            detail_card.opacity = 1
            if twin:
                twin_card.opacity = 1
            page.update()
            for c in confetti.controls:
                c.top = 340
            page.update()

        threading.Thread(target=reveal, daemon=True).start()

    # ------------------------------------------------------------------
    # Compare Mode helpers
    # ------------------------------------------------------------------
    def make_compare_code() -> str:
        r = state.result or {}
        payload = {
            "n": state.name,
            "t": r.get("talent_title", ""),
            "s": r.get("talent_summary", ""),
        }
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def decode_compare_code(code: str) -> dict:
        raw = base64.urlsafe_b64decode(code.strip().encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        return {"name": payload["n"], "talent_title": payload["t"], "talent_summary": payload["s"]}

    # ------------------------------------------------------------------
    # SCREEN: Compare with a friend (no server — just a shareable text code)
    # ------------------------------------------------------------------
    def screen_compare():
        my_code = make_compare_code()
        code_field = ft.TextField(
            label="Your code (copy & send to a friend)",
            value=my_code, read_only=True, width=320, multiline=True, max_lines=3,
        )
        friend_field = ft.TextField(
            label="Paste your friend's code here", width=320,
            multiline=True, max_lines=3,
        )
        result_text = ft.Text("", color=theme["text"], width=320, text_align=ft.TextAlign.CENTER)

        def on_copy(e):
            page.set_clipboard(my_code)
            show_snack("Copied your code!")

        def on_compare_submit(e):
            if not friend_field.value or not friend_field.value.strip():
                show_snack("Paste a friend's code first.")
                return
            try:
                friend = decode_compare_code(friend_field.value)
            except Exception:
                show_snack("That code looks invalid.")
                return

            result_text.value = "Comparing..."
            page.update()

            def worker():
                try:
                    r = state.result or {}
                    summary = ai_service.compare_profiles(
                        state.name, r.get("talent_title", ""),
                        friend["name"], friend["talent_title"],
                        state.language_name,
                    )
                    result_text.value = summary
                except Exception as ex:
                    result_text.value = f"AI error: {ex}"
                page.update()

            threading.Thread(target=worker, daemon=True).start()

        def on_back(e):
            screen_result()

        set_view([
            ft.Container(height=30),
            ft.Text("🤝 Compare with a Friend", size=20, weight=ft.FontWeight.BOLD,
                    color=theme["primary"]),
            ft.Container(height=10),
            code_field,
            ft.OutlinedButton("Copy my code", on_click=on_copy),
            ft.Container(height=16),
            friend_field,
            ft.ElevatedButton("Compare", bgcolor=theme["primary"], color="white",
                               on_click=on_compare_submit),
            ft.Container(height=16),
            ft.Container(result_text, width=320, padding=12, bgcolor=theme["card"],
                         border_radius=12),
            ft.Container(height=16),
            ft.TextButton("← Back", on_click=on_back),
        ])

    # ------------------------------------------------------------------
    # Journal Mode helpers (fully local via page.client_storage — no server)
    # ------------------------------------------------------------------
    def load_journal() -> dict:
        try:
            raw = page.client_storage.get(JOURNAL_KEY)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return {"streak": 0, "last_date": "", "entries": []}

    def save_journal(data: dict):
        page.client_storage.set(JOURNAL_KEY, json.dumps(data, ensure_ascii=False))

    def screen_journal_home():
        data = load_journal()
        today = datetime.date.today().isoformat()
        already_done_today = data["last_date"] == today

        def on_write(e):
            screen_journal_entry(data)

        def on_back(e):
            screen_result() if state.result else screen_language()

        entries_preview = data["entries"][-5:][::-1]
        entry_widgets = [
            ft.Container(
                ft.Column([
                    ft.Text(en["date"], size=11, color=theme["accent"]),
                    ft.Text(en["question"], size=13, weight=ft.FontWeight.BOLD, color=theme["text"]),
                    ft.Text(en["answer"], size=13, color=theme["text"]),
                ]),
                width=320, padding=10, bgcolor=theme["card"], border_radius=12,
            )
            for en in entries_preview
        ] or [ft.Text("No entries yet — start today!", color=theme["text"])]

        set_view([
            ft.Container(height=30),
            ft.Text("📓 Daily Journal", size=22, weight=ft.FontWeight.BOLD, color=theme["primary"]),
            ft.Text(f"🔥 {data['streak']}-day streak", size=16, color=theme["accent"]),
            ft.Container(height=12),
            ft.ElevatedButton(
                "✓ Today's entry done" if already_done_today else "Write today's entry",
                bgcolor=theme["primary"], color="white", width=260,
                on_click=on_write, disabled=already_done_today,
            ),
            ft.Container(height=16),
            ft.Column(entry_widgets, spacing=10, width=340, scroll=ft.ScrollMode.AUTO, height=280),
            ft.Container(height=10),
            ft.TextButton("← Back", on_click=on_back),
        ])

    def screen_journal_entry(data: dict):
        screen_loading("Preparing today's question...")
        recent = [en["answer"] for en in data["entries"]]
        streak_day = data["streak"] + 1

        def worker():
            try:
                prompt = ai_service.generate_daily_prompt(
                    state.name or "Friend", state.language_name or "English",
                    streak_day, recent,
                )
                render(prompt)
            except Exception as ex:
                show_snack(f"AI error: {ex}")

        def render(prompt: str):
            answer_field = ft.TextField(
                label="Your reflection", multiline=True, min_lines=3, max_lines=6, width=320,
                border_color=theme["primary"],
            )

            def on_save(e):
                if not answer_field.value or not answer_field.value.strip():
                    show_snack("Write something first.")
                    return
                today = datetime.date.today()
                yesterday = (today - datetime.timedelta(days=1)).isoformat()
                new_streak = data["streak"] + 1 if data["last_date"] == yesterday or not data["last_date"] else (
                    data["streak"] if data["last_date"] == today.isoformat() else 1
                )
                data["streak"] = new_streak
                data["last_date"] = today.isoformat()
                data["entries"].append({
                    "date": today.isoformat(),
                    "question": prompt,
                    "answer": answer_field.value.strip(),
                })
                save_journal(data)
                show_snack("Saved! 🔥")
                screen_journal_home()

            set_view([
                ft.Container(height=40),
                ft.Text(f"Day {streak_day}", size=14, color=theme["accent"], weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Container(
                    ft.Text(prompt, size=17, color=theme["text"], text_align=ft.TextAlign.CENTER),
                    width=320, padding=16, bgcolor=theme["card"], border_radius=16,
                ),
                ft.Container(height=20),
                answer_field,
                ft.Container(height=16),
                ft.ElevatedButton("Save entry", bgcolor=theme["primary"], color="white",
                                   width=200, on_click=on_save),
            ])

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Kick off
    # ------------------------------------------------------------------
    screen_splash()


if __name__ == "__main__":
    ft.app(target=main)
