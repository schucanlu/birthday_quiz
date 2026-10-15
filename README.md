# 🎂 Birthday Quiz (Streamlit, Python 3.13)

## Installation
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
The app opens at http://localhost:8501

## Structure
```
birthday_quiz/
├── app.py              # application (no need to modify)
├── quiz_config.json    # ALL your content: welcome, questions, final reveal
├── images/             # put your pictures here
└── requirements.txt
```

## Customising (quiz_config.json)
Images: a path relative to the app folder (`images/us.jpg`) or a URL (`https://...`).
Text fields accept simple HTML (`<br>`, `<b>`) and emojis.

### Welcome page
| Key | Description |
|---|---|
| `title` | Page title |
| `images` | List of pictures (several = shown side by side) |
| `text` | Welcome message |
| `button_label` | Start button text |

### Questions – 4 types
| `type` | Required keys | Correctness check |
|---|---|---|
| `single_choice` | `options`, `answer` (one option) | exact option |
| `multiple_choice` | `options`, `answer` (list) | all correct options ticked, no wrong ones |
| `text` | `answer` (+ optional `alternatives` list) | ignores case, accents and extra spaces |
| `number` | `answer` (+ optional `tolerance`, `step`) | \|answer − value\| ≤ tolerance |

Optional keys for any question:
`image`, `image_width` (px), `hint`, `correct_message`, `wrong_message`,
`retry_message`, `explanation` (shown after validating), `answer_image` (shown after validating).

### Global settings
| Key | Description |
|---|---|
| `max_attempts` | Attempts per question (`0` = unlimited until correct) |
| `show_correct_answer` | Show the solution after a wrong answer |
| `theme.primary_color` / `theme.background_color` | Colours |

### Final page
`title`, `show_score`, `text_before_reveal`, `reveal_button_label`,
`final_answer` (the big reveal), `images`, `text_after_reveal`,
`effect` (`balloons`, `snow` or `none`), `allow_restart`.

The config is reloaded automatically when you save the file; just refresh the browser.
If something is wrong in the config (e.g. an answer not in the options), the app lists the problems.
