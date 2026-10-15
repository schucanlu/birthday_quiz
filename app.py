"""
Birthday Quiz – Streamlit application
-------------------------------------
Run with:   streamlit run app.py
All content (welcome page, questions, final reveal) is defined in quiz_config.json.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import streamlit as st

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "quiz_config.json"

SUPPORTED_TYPES = {"single_choice", "multiple_choice", "text", "number"}


# --------------------------------------------------------------------------- #
# Config loading & validation
# --------------------------------------------------------------------------- #
@st.cache_data
def load_config(path: str, _mtime: float) -> dict[str, Any]:
    """Load the JSON config. `_mtime` invalidates the cache when the file changes."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """Return a list of human-readable problems in the config (empty = OK)."""
    errors: list[str] = []
    questions = cfg.get("questions", [])
    if not questions:
        errors.append("No questions defined in 'questions'.")
    for i, q in enumerate(questions, start=1):
        qtype = q.get("type")
        if qtype not in SUPPORTED_TYPES:
            errors.append(f"Question {i}: unknown type '{qtype}'. Use one of {sorted(SUPPORTED_TYPES)}.")
            continue
        if "question" not in q:
            errors.append(f"Question {i}: missing 'question' text.")
        if "answer" not in q:
            errors.append(f"Question {i}: missing 'answer'.")
            continue
        if qtype in {"single_choice", "multiple_choice"}:
            options = q.get("options", [])
            if len(options) < 2:
                errors.append(f"Question {i}: needs at least 2 'options'.")
            answers = q["answer"] if isinstance(q["answer"], list) else [q["answer"]]
            for a in answers:
                if a not in options:
                    errors.append(f"Question {i}: answer '{a}' is not in the options.")
        if qtype == "number":
            try:
                float(q["answer"])
            except (TypeError, ValueError):
                errors.append(f"Question {i}: 'answer' must be a number.")
    return errors


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def normalize(text: str) -> str:
    """Lower-case, trim, collapse spaces and strip accents (é -> e)."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def resolve_image(src: str | None) -> str | None:
    """Accept a URL or a path relative to the app folder."""
    if not src:
        return None
    if src.startswith(("http://", "https://")):
        return src
    path = (BASE_DIR / src).resolve()
    if path.exists():
        return str(path)
    st.warning(f"Image not found: {src}")
    return None


def show_images(images: list[str] | str | None, width: int | None = None) -> None:
    """Show one image or a row of images."""
    if not images:
        return
    if isinstance(images, str):
        images = [images]
    resolved = [p for p in (resolve_image(i) for i in images) if p]
    if not resolved:
        return
    if len(resolved) == 1:
        if width:
            st.image(resolved[0], width=width)
        else:
            st.image(resolved[0], width="content")
    else:
        cols = st.columns(len(resolved))
        for col, img in zip(cols, resolved):
            col.image(img, width="stretch")


def check_answer(q: dict[str, Any], user_answer: Any) -> bool:
    """Automatic correctness check depending on question type."""
    qtype = q["type"]
    correct = q["answer"]

    if qtype == "single_choice":
        return user_answer == correct

    if qtype == "multiple_choice":
        expected = set(correct if isinstance(correct, list) else [correct])
        return set(user_answer or []) == expected

    if qtype == "text":
        accepted = correct if isinstance(correct, list) else [correct]
        accepted += q.get("alternatives", [])
        return normalize(user_answer) in {normalize(a) for a in accepted}

    if qtype == "number":
        if user_answer is None:
            return False
        tolerance = float(q.get("tolerance", 0))
        return abs(float(user_answer) - float(correct)) <= tolerance

    return False


def has_answer(q: dict[str, Any], user_answer: Any) -> bool:
    if q["type"] == "multiple_choice":
        return bool(user_answer)
    if q["type"] == "text":
        return bool(str(user_answer or "").strip())
    return user_answer is not None


def format_correct_answer(q: dict[str, Any]) -> str:
    ans = q["answer"]
    return ", ".join(map(str, ans)) if isinstance(ans, list) else str(ans)


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
def init_state() -> None:
    defaults = {
        "page": "welcome",       # welcome | quiz | final
        "q_index": 0,
        "score": 0,
        "validated": False,      # current question has been validated
        "last_correct": False,
        "attempts": 0,           # attempts on current question
        "revealed": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_quiz() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


def go_next(total: int) -> None:
    st.session_state.q_index += 1
    st.session_state.validated = False
    st.session_state.last_correct = False
    st.session_state.attempts = 0
    if st.session_state.q_index >= total:
        st.session_state.page = "final"


# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
def inject_css(theme: dict[str, Any]) -> None:
    primary = theme.get("primary_color", "#e75480")
    background = theme.get("background_color", "#fff5f8")
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {background}; }}
        h1, h2, h3 {{ color: {primary}; text-align: center; }}
        .centered {{ text-align: center; font-size: 1.15rem; line-height: 1.6; }}
        .final-answer {{
            text-align: center; font-size: 2.2rem; font-weight: 700;
            color: {primary}; padding: 1.5rem; border-radius: 1rem;
            border: 3px dashed {primary}; background: white; margin: 1rem 0;
        }}
        div.stButton > button {{
            background-color: {primary}; color: white; border: none;
            border-radius: 2rem; padding: 0.6rem 2rem; font-size: 1.1rem;
        }}
        div.stButton > button:hover {{ opacity: 0.85; color: white; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_welcome(cfg: dict[str, Any]) -> None:
    w = cfg.get("welcome", {})
    st.title(w.get("title", "Bon anniversaire ! 🎉"))
    show_images(w.get("images"))
    if w.get("text"):
        st.markdown(f"<div class='centered'>{w['text']}</div>", unsafe_allow_html=True)
    st.write("")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button(w.get("button_label", "Voir la première question 💖"), width="stretch"):
            st.session_state.page = "quiz"
            st.rerun()


def render_input(q: dict[str, Any], key: str, disabled: bool) -> Any:
    qtype = q["type"]
    if qtype == "single_choice":
        return st.radio("Your answer:", q["options"], index=None, key=key, disabled=disabled)
    if qtype == "multiple_choice":
        st.caption("Several answers may be correct.")
        return [opt for i, opt in enumerate(q["options"])
                if st.checkbox(opt, key=f"{key}_{i}", disabled=disabled)]
    if qtype == "text":
        return st.text_input("Your answer:", key=key, disabled=disabled)
    if qtype == "number":
        return st.number_input("Your answer:", value=None, step=q.get("step", 1),
                               key=key, disabled=disabled)
    return None


def page_quiz(cfg: dict[str, Any]) -> None:
    questions = cfg["questions"]
    settings = cfg.get("settings", {})
    max_attempts = int(settings.get("max_attempts", 1))   # 0 = unlimited
    show_solution = bool(settings.get("show_correct_answer", True))

    total = len(questions)
    idx = st.session_state.q_index
    q = questions[idx]

    st.progress(idx / total, text=f"Question {idx + 1} / {total}")
    st.subheader(q["question"])
    show_images(q.get("image"), width=q.get("image_width"))

    key = f"answer_{idx}_{st.session_state.attempts}"
    user_answer = render_input(q, key, disabled=st.session_state.validated)

    if q.get("hint") and not st.session_state.validated:
        with st.expander("Un indice ? 🤫"):
            st.write(q["hint"])

    # ---- Validate --------------------------------------------------------- #
    if not st.session_state.validated:
        if st.button("Validate ✅"):
            if not has_answer(q, user_answer):
                st.warning("Mariella.... Il faut mettre une réponse 😉")
                return
            correct = check_answer(q, user_answer)
            st.session_state.attempts += 1
            if correct:
                st.session_state.score += 1
                st.session_state.last_correct = True
                st.session_state.validated = True
            elif max_attempts and st.session_state.attempts >= max_attempts:
                st.session_state.last_correct = False
                st.session_state.validated = True
            else:
                left = (f" ({max_attempts - st.session_state.attempts} attempt(s) left)"
                        if max_attempts else "")
                st.session_state["retry_msg"] = (
                    q.get("retry_message", "He non ! Essaie encore") + left)
            st.rerun()
        if msg := st.session_state.pop("retry_msg", None):
            st.error(msg)
        return

    # ---- Feedback after validation --------------------------------------- #
    if st.session_state.last_correct:
        st.success(q.get("correct_message", "Correct! 🎉"))
    else:
        text = q.get("wrong_message", "Oops, ce n'était pas ça! 🙈")
        if show_solution:
            text += f"  \nLa bonne réponse était: **{format_correct_answer(q)}**"
        st.error(text)

    if q.get("explanation"):
        st.info(q["explanation"])
    show_images(q.get("answer_image"), width=q.get("image_width"))

    label = "Prochaine question ➡️" if idx + 1 < total else "Voir la surprise 🎁"
    if st.button(label):
        go_next(total)
        st.rerun()


def page_final(cfg: dict[str, Any]) -> None:
    f = cfg.get("final", {})
    total = len(cfg["questions"])
    score = st.session_state.score

    st.title(f.get("title", "Quiz terminé! 🥳"))
    if f.get("show_score", True):
        st.markdown(f"<div class='centered'>Ton score: <b>{score} / {total}</b></div>",
                    unsafe_allow_html=True)
    if f.get("text_before_reveal"):
        st.markdown(f"<div class='centered'>{f['text_before_reveal']}</div>",
                    unsafe_allow_html=True)

    st.write("")
    if not st.session_state.revealed:
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if st.button(f.get("reveal_button_label", "Voir la dernière réponse ✨"),
                         width="stretch"):
                st.session_state.revealed = True
                st.rerun()
        return

    # ---- Reveal ----------------------------------------------------------- #
    effect = f.get("effect", "balloons")
    if not st.session_state.get("effect_done"):
        if effect == "balloons":
            st.balloons()
        elif effect == "snow":
            st.snow()
        st.session_state.effect_done = True

    st.markdown(f"<div class='final-answer'>{f.get('final_answer', '🎁')}</div>",
                unsafe_allow_html=True)
    show_images(f.get("images"))
    if f.get("text_after_reveal"):
        st.markdown(f"<div class='centered'>{f['text_after_reveal']}</div>",
                    unsafe_allow_html=True)

    pdf_file = "Affiche_week-end_surprise.pdf"

    with open(pdf_file, "rb") as file:
        st.download_button(
            label="📄 Voilà le programme !",
            data=file,
            file_name="programme_Madrid.pdf",
            mime="application/pdf"
        )

    if f.get("allow_restart", True):
        st.write("")
        if st.button("Encore ! 🔁"):
            reset_quiz()
            st.rerun()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    if not CONFIG_FILE.exists():
        st.set_page_config(page_title="Birthday Quiz")
        st.error(f"Config file not found: {CONFIG_FILE.name}")
        st.stop()

    try:
        cfg = load_config(str(CONFIG_FILE), CONFIG_FILE.stat().st_mtime)
    except json.JSONDecodeError as exc:
        st.set_page_config(page_title="Birthday Quiz")
        st.error(f"quiz_config.json is not valid JSON: {exc}")
        st.stop()

    st.set_page_config(
        page_title=cfg.get("page_title", "Birthday Quiz"),
        page_icon=cfg.get("page_icon", "🎂"),
        layout="centered",
    )
    inject_css(cfg.get("theme", {}))

    if errors := validate_config(cfg):
        st.error("There are problems in quiz_config.json:")
        for e in errors:
            st.markdown(f"- {e}")
        st.stop()

    init_state()
    match st.session_state.page:
        case "welcome":
            page_welcome(cfg)
        case "quiz":
            page_quiz(cfg)
        case "final":
            page_final(cfg)


if __name__ == "__main__":
    main()
