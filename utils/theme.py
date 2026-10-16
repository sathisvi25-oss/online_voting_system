"""
Premium shared theme for the voting system.

Drop this file in:
    utils/theme.py

The public helper API is intentionally kept 100% compatible with the
existing pages:
    apply_theme()
    page_header()
    section_title()
    pill()
    badge()
    feature_card()
    candidate_card()
    winner_card()
    stepper()

New, additive helpers (safe to ignore if you don't need them):
    divider()
    empty_state()
    stat_row()

Design direction:
    "Civic Luxe" v2 — premium navy, warm gold, crisp white surfaces,
    glass effects, one consistent elevation/shadow system, smoother
    motion, and full coverage of Streamlit's input widgets (selects,
    sliders, progress bars, tooltips) so nothing looks "unthemed".

Use apply_theme() once near the top of every Streamlit page, after
st.set_page_config().
Use page_header() instead of st.title()/st.header() for the main banner.
"""

import base64
import html
import textwrap

import streamlit as st


# ============================================================
# DESIGN TOKENS
# ============================================================

INK = "#0A1728"
INK_SOFT = "#233A56"

NAVY_950 = "#071522"
NAVY_900 = "#0E2947"
NAVY_800 = "#1B426B"
NAVY_700 = "#285783"

# Unified card surface (was hardcoded in multiple places before —
# now every dark panel pulls from these two tokens only).
SURFACE_START = "#2A4E78"
SURFACE_END = "#203D60"

GOLD = "#D8AD55"
GOLD_LIGHT = "#F2CB75"
GOLD_DARK = "#9C701F"
GOLD_SOFT = "#FBF0D4"

PAPER = "#F5F7FA"
PAPER_2 = "#E9EFF6"
WHITE = "#FFFFFF"

LINE = "#D5DEE9"
LINE_DARK = "#B7C6D7"

SLATE = "#667A91"
MUTED = "#8999AB"

GOOD = "#197447"
GOOD_SOFT = "#E8F6EE"

WARN = "#B53030"
WARN_SOFT = "#FCEBEC"

AMBER = "#AF761A"
AMBER_SOFT = "#FFF4DD"

# Backward-compatible aliases for existing pages.
HARBOR = NAVY_800
HARBOR_DEEP = NAVY_900
SIGNAL = GOLD
SIGNAL_DEEP = GOLD_DARK
CLOUD = WHITE
BLOCK = SURFACE_START
BLOCK_DEEP = SURFACE_END

SHADOW_SM = "0 6px 18px rgba(8, 21, 37, 0.07)"
SHADOW_MD = "0 14px 32px rgba(8, 21, 37, 0.12)"
SHADOW_LG = "0 24px 58px rgba(8, 21, 37, 0.17)"
SHADOW_GOLD = "0 10px 24px rgba(156, 112, 31, 0.22)"

RADIUS_SM = "11px"
RADIUS_MD = "16px"
RADIUS_LG = "20px"
RADIUS_XL = "24px"

SURFACE_GRADIENT = f"linear-gradient(150deg, {SURFACE_START} 0%, {SURFACE_END} 100%)"
GOLD_GRADIENT = f"linear-gradient(135deg, {GOLD_LIGHT} 0%, {GOLD} 55%, {GOLD_DARK} 100%)"


# ============================================================
# INTERNAL HTML HELPER
# ============================================================

def _html(markup: str) -> None:
    """
    Render HTML safely for Streamlit.

    Streamlit/Markdown can interpret indented HTML as a code block.
    We therefore normalize every line before rendering so the visual
    components always appear as HTML instead of raw source code.
    """
    raw = textwrap.dedent(str(markup)).strip()
    normalized = "\n".join(
        line.strip()
        for line in raw.splitlines()
        if line.strip()
    )

    st.markdown(
        normalized,
        unsafe_allow_html=True,
    )


def _safe_text(value) -> str:
    """Escape user/database content before placing it into HTML."""
    return html.escape(str(value or ""))


# ============================================================
# GLOBAL THEME
# ============================================================

def apply_theme():
    """
    Apply the premium visual system to the entire Streamlit app.
    Call once per page after st.set_page_config().
    """

    st.markdown(
        textwrap.dedent(
            f"""
            <style>

            /* ==================================================
               FONT + ROOT
               ================================================== */

            @import url(
                'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap'
            );

            :root {{
                --ink: {INK};
                --ink-soft: {INK_SOFT};

                --navy-950: {NAVY_950};
                --navy-900: {NAVY_900};
                --navy-800: {NAVY_800};
                --navy-700: {NAVY_700};

                --surface-start: {SURFACE_START};
                --surface-end: {SURFACE_END};

                --gold: {GOLD};
                --gold-light: {GOLD_LIGHT};
                --gold-dark: {GOLD_DARK};
                --gold-soft: {GOLD_SOFT};

                --paper: {PAPER};
                --paper-2: {PAPER_2};
                --white: {WHITE};

                --line: {LINE};
                --line-dark: {LINE_DARK};

                --slate: {SLATE};
                --muted: {MUTED};

                --good: {GOOD};
                --good-soft: {GOOD_SOFT};

                --warn: {WARN};
                --warn-soft: {WARN_SOFT};

                --amber: {AMBER};
                --amber-soft: {AMBER_SOFT};

                --radius-sm: {RADIUS_SM};
                --radius-md: {RADIUS_MD};
                --radius-lg: {RADIUS_LG};
                --radius-xl: {RADIUS_XL};

                --shadow-sm: {SHADOW_SM};
                --shadow-md: {SHADOW_MD};
                --shadow-lg: {SHADOW_LG};
                --shadow-gold: {SHADOW_GOLD};

                --ease: cubic-bezier(0.22, 1, 0.36, 1);
            }}

            html,
            body,
            [class*="css"] {{
                font-family: "DM Sans", sans-serif;
            }}

            .stApp {{
                background:
                    radial-gradient(
                        900px 420px at 90% -8%,
                        rgba(216, 173, 85, 0.10),
                        transparent 62%
                    ),
                    radial-gradient(
                        720px 390px at -6% 12%,
                        rgba(40, 87, 131, 0.08),
                        transparent 60%
                    ),
                    linear-gradient(
                        160deg,
                        #FAFBFD 0%,
                        {PAPER} 46%,
                        #E7EDF4 100%
                    );
                background-attachment: fixed;
            }}

            .main .block-container {{
                max-width: 1450px;
                padding-top: 1.05rem;
                padding-bottom: 2.8rem;
                animation: vsFadeUp 420ms var(--ease) both;
            }}

            /* A subtle page-wide premium frame. */
            .main .block-container::before {{
                content: "";
                position: fixed;
                inset: 0;
                pointer-events: none;
                border: 1px solid rgba(255,255,255,0.45);
                z-index: 0;
            }}

            [data-testid="stAppViewContainer"] {{
                background: transparent;
            }}

            /* Fully opaque — a translucent/blurred header lets page
               content show through as you scroll, which visually
               "cuts" through the hero card and looks like a bug. */
            [data-testid="stHeader"] {{
                background: rgba(245,247,250,0.96) !important;
                border-bottom: 1px solid rgba(183,198,215,0.72);
                box-shadow: 0 2px 12px rgba(8,21,37,0.03);
                backdrop-filter: blur(10px) !important;
                -webkit-backdrop-filter: blur(10px) !important;
            }}

            @media (min-width: 1100px) {{
                .main .block-container {{
                    padding-left: 3.2rem;
                    padding-right: 3.2rem;
                }}
            }}

            h1, h2, h3, h4, h5, h6 {{
                font-family: "Manrope", sans-serif !important;
                color: var(--ink) !important;
                letter-spacing: -0.02em;
            }}

            a {{
                color: var(--navy-800);
                font-weight: 600;
                text-decoration-color: rgba(18, 49, 94, 0.35);
            }}

            a:hover {{
                color: var(--gold-dark);
            }}

            * {{
                scrollbar-width: thin;
                scrollbar-color: #AEBCCD transparent;
            }}

            *:focus-visible {{
                outline: 2px solid var(--gold) !important;
                outline-offset: 3px !important;
                border-radius: 6px;
            }}

            @keyframes vsFadeUp {{
                from {{ opacity: 0; transform: translateY(8px); }}
                to   {{ opacity: 1; transform: translateY(0); }}
            }}

            @keyframes vsPulse {{
                0%, 100% {{ box-shadow: 0 0 0 0 rgba(175, 118, 26, 0.35); }}
                50%      {{ box-shadow: 0 0 0 5px rgba(175, 118, 26, 0); }}
            }}

            @keyframes vsShimmer {{
                0%   {{ background-position: -200% 0; }}
                100% {{ background-position: 200% 0; }}
            }}

            /* ==================================================
               HERO
               ================================================== */

            .vs-hero {{
                position: relative;
                isolation: isolate;
                overflow: hidden;

                background:
                    radial-gradient(
                        520px 220px at 92% -10%,
                        rgba(216, 170, 70, 0.26),
                        transparent 65%
                    ),
                    radial-gradient(
                        420px 240px at -6% 118%,
                        rgba(255, 255, 255, 0.10),
                        transparent 60%
                    ),
                    linear-gradient(130deg, {NAVY_800} 0%, {NAVY_950} 88%);

                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: var(--radius-xl);
                padding: 2.25rem 2.45rem;
                margin: 0 0 1.6rem 0;

                box-shadow: var(--shadow-lg);
                animation: vsFadeUp 480ms var(--ease) both;
            }}

            .vs-hero::before {{
                content: "";
                position: absolute;
                inset: 0;
                opacity: 0.4;
                pointer-events: none;

                background-image:
                    linear-gradient(rgba(255,255,255,0.055) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.055) 1px, transparent 1px);

                background-size: 26px 26px;
                mask-image: linear-gradient(135deg, black 10%, transparent 78%);
            }}

            .vs-hero::after {{
                content: "";
                position: absolute;
                width: 240px;
                height: 240px;
                right: -95px;
                top: -85px;

                border-radius: 50%;
                border: 1px solid rgba(216, 170, 70, 0.24);
                box-shadow:
                    0 0 0 28px rgba(216, 170, 70, 0.035),
                    0 0 0 56px rgba(216, 170, 70, 0.02);

                pointer-events: none;
            }}

            .vs-hero-row {{
                position: relative;
                z-index: 2;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1.5rem;
            }}

            .vs-hero-copy {{
                min-width: 0;
            }}

            .vs-kicker {{
                color: var(--gold-light);
                font-family: "Manrope", sans-serif;
                font-size: 0.73rem;
                font-weight: 800;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                margin-bottom: 0.55rem;
                display: flex;
                align-items: center;
                gap: 0.4rem;
            }}

            .vs-kicker::before {{
                content: "";
                width: 16px;
                height: 2px;
                border-radius: 2px;
                background: var(--gold);
                display: inline-block;
            }}

            .vs-hero h1, .vs-hero h2 {{
                color: #FFFFFF !important;
                margin: 0 !important;
                font-size: clamp(1.85rem, 3.2vw, 2.75rem) !important;
                line-height: 1.12 !important;
            }}

            .vs-hero p {{
                color: #D7E1F1;
                margin: 0.65rem 0 0 0;
                max-width: 68ch;
                line-height: 1.65;
                font-size: 0.97rem;
            }}

            .vs-hero-meta {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-top: 1rem;
            }}

            .vs-hero-emblem {{
                flex: 0 0 auto;
                width: 78px;
                height: 78px;
                border-radius: 20px;

                display: flex;
                align-items: center;
                justify-content: center;

                background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03));
                border: 1px solid rgba(216, 170, 70, 0.55);
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,0.10),
                    0 14px 28px rgba(0,0,0,0.18);

                color: #FFFFFF;
                font-size: 2rem;
            }}

            /* ==================================================
               UNIFIED DARK SURFACE (cards / forms / panels)
               ================================================== */

            .vs-card {{
                position: relative;
                overflow: hidden;

                background:
                    linear-gradient(
                        145deg,
                        #2B527D 0%,
                        #25486F 48%,
                        #203E61 100%
                    );

                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: var(--radius-lg);
                padding: 1.35rem 1.45rem;
                margin-bottom: 1rem;

                box-shadow:
                    0 14px 32px rgba(8, 21, 37, 0.13),
                    inset 0 1px 0 rgba(255,255,255,0.06);

                color: #F8FBFF;

                transition:
                    transform 180ms var(--ease),
                    box-shadow 180ms var(--ease),
                    border-color 180ms var(--ease);
            }}

            .vs-card::before {{
                content: "";
                position: absolute;
                left: 0;
                right: 0;
                top: 0;
                height: 1px;
                background: linear-gradient(
                    90deg,
                    transparent,
                    rgba(255,255,255,0.16),
                    transparent
                );
                pointer-events: none;
            }}

            .vs-card:hover {{
                transform: translateY(-3px);
                box-shadow:
                    0 20px 42px rgba(8, 21, 37, 0.19),
                    inset 0 1px 0 rgba(255,255,255,0.08);
                border-color: rgba(216, 173, 85, 0.48);
            }}

            .vs-card-accent {{
                border-left: 4px solid var(--gold);
            }}

            .vs-card h4 {{
                margin: 0 0 0.45rem 0 !important;
                font-size: 1.05rem !important;
                color: #FFFFFF !important;
            }}

            .vs-card p {{
                color: #D7E3F2 !important;
                margin: 0;
                font-size: 0.92rem;
                line-height: 1.6;
            }}

            [data-testid="stVerticalBlockBorderWrapper"] {{
                background:
                    linear-gradient(
                        145deg,
                        #2B527D 0%,
                        #224467 100%
                    ) !important;
                border: 1px solid rgba(255, 255, 255, 0.14) !important;
                border-radius: 20px !important;
                box-shadow:
                    0 16px 34px rgba(8,21,37,0.15),
                    inset 0 1px 0 rgba(255,255,255,0.05) !important;
            }}

            [data-testid="stForm"] {{
                background:
                    linear-gradient(
                        145deg,
                        #2B527D 0%,
                        #224467 100%
                    ) !important;
                border: 1px solid rgba(255, 255, 255, 0.14) !important;
                border-radius: 20px !important;
                padding: 1.55rem 1.6rem 1.05rem 1.6rem;
                box-shadow:
                    0 16px 34px rgba(8,21,37,0.15),
                    inset 0 1px 0 rgba(255,255,255,0.05) !important;
            }}

            [data-testid="stVerticalBlockBorderWrapper"] h1,
            [data-testid="stVerticalBlockBorderWrapper"] h2,
            [data-testid="stVerticalBlockBorderWrapper"] h3,
            [data-testid="stVerticalBlockBorderWrapper"] h4,
            [data-testid="stVerticalBlockBorderWrapper"] p,
            [data-testid="stVerticalBlockBorderWrapper"] span,
            [data-testid="stForm"] h1,
            [data-testid="stForm"] h2,
            [data-testid="stForm"] h3,
            [data-testid="stForm"] h4,
            [data-testid="stForm"] p,
            [data-testid="stForm"] span {{
                color: #F4F7FC !important;
            }}

            [data-testid="stForm"] label,
            [data-testid="stVerticalBlockBorderWrapper"] label {{
                color: #F7FAFF !important;
            }}

            [data-testid="stForm"] small,
            [data-testid="stForm"] [data-testid="InputInstructions"],
            [data-testid="stVerticalBlockBorderWrapper"] small {{
                color: #E5D7B5 !important;
            }}

            /* ==================================================
               BRAND CHIPS / BADGES
               ================================================== */

            .vs-pill {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                font-family: "Manrope", sans-serif;
                font-size: 0.68rem;
                font-weight: 800;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: var(--gold-dark);
                background: var(--gold-soft);
                border: 1px solid rgba(154, 108, 24, 0.14);
                border-radius: 999px;
                padding: 0.32rem 0.72rem;
            }}

            .vs-hero .vs-pill {{
                color: #F7E9C8;
                background: rgba(216, 170, 70, 0.15);
                border-color: rgba(216, 170, 70, 0.24);
            }}

            .vs-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                font-family: "Manrope", sans-serif;
                font-weight: 700;
                font-size: 0.71rem;
                border-radius: 999px;
                padding: 0.34rem 0.72rem;
                line-height: 1;
            }}

            .vs-badge::before {{
                content: "";
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: currentColor;
                box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.75);
            }}

            .vs-badge-success {{ background: var(--good-soft); color: var(--good); }}
            .vs-badge-pending {{ background: var(--amber-soft); color: var(--amber); }}
            .vs-badge-pending::before {{ animation: vsPulse 1.8s ease-in-out infinite; }}
            .vs-badge-danger  {{ background: var(--warn-soft); color: var(--warn); }}
            .vs-badge-neutral {{ background: #EEF2F7; color: var(--slate); }}

            /* ==================================================
               FEATURE CARDS
               ================================================== */

            .vs-feature {{
                min-height: 168px;
                padding: 1.4rem;
            }}

            .vs-feature-icon {{
                width: 46px;
                height: 46px;
                border-radius: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.25rem;
                background: linear-gradient(135deg, rgba(255,255,255,0.14), rgba(216,170,70,0.16));
                border: 1px solid rgba(255, 255, 255, 0.14);
                margin-bottom: 0.8rem;
            }}

            /* ==================================================
               CANDIDATE CARDS
               ================================================== */

            .vs-candidate-card {{
                text-align: center;
                padding: 1.25rem 1rem 1.3rem 1rem;
            }}

            .vs-candidate-card .vs-candidate-name {{ color: #FFFFFF !important; }}
            .vs-candidate-card .vs-candidate-sub {{ color: #D7E3F2 !important; }}

            .vs-candidate-photo,
            .vs-candidate-photo-fallback {{
                width: 96px;
                height: 96px;
                border-radius: 50%;
                object-fit: cover;
                margin: 0 auto 0.8rem auto;
                display: flex;
                border: 4px solid #FFFFFF;
                box-shadow: 0 0 0 1px var(--line), 0 9px 20px rgba(7, 19, 41, 0.15);
                transition: transform 180ms var(--ease);
            }}

            .vs-candidate-card:hover .vs-candidate-photo,
            .vs-candidate-card:hover .vs-candidate-photo-fallback {{
                transform: scale(1.04);
            }}

            .vs-candidate-photo-fallback {{
                align-items: center;
                justify-content: center;
                background: linear-gradient(145deg, {NAVY_700}, {NAVY_950});
                color: #FFFFFF;
                font-family: "Manrope", sans-serif;
                font-weight: 800;
                font-size: 2rem;
            }}

            .vs-candidate-name {{
                font-family: "Manrope", sans-serif;
                font-size: 1rem;
                font-weight: 800;
            }}

            .vs-candidate-sub {{
                font-size: 0.84rem;
                margin-top: 0.18rem;
            }}

            .vs-candidate-meta {{ margin-top: 0.7rem; }}

            /* ==================================================
               WINNER CARD
               ================================================== */

            .vs-winner-card {{
                position: relative;
                overflow: hidden;
                background:
                    radial-gradient(420px 190px at 50% -15%, rgba(216, 170, 70, 0.20), transparent 70%),
                    linear-gradient(180deg, #FFFFFF 0%, #FBF7EE 100%);
                border: 1px solid rgba(216, 170, 70, 0.55);
                border-radius: var(--radius-xl);
                padding: 2.2rem 1.5rem 1.9rem 1.5rem;
                text-align: center;
                box-shadow: var(--shadow-lg);
                margin-bottom: 1.4rem;
                animation: vsFadeUp 520ms var(--ease) both;
            }}

            .vs-winner-ribbon {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                color: #FFFFFF;
                background: GOLD_GRADIENT_PLACEHOLDER;
                font-family: "Manrope", sans-serif;
                font-size: 0.73rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                padding: 0.4rem 0.95rem;
                border-radius: 999px;
                box-shadow: var(--shadow-gold);
                margin-bottom: 1rem;
            }}

            .vs-winner-photo,
            .vs-winner-photo-fallback {{
                width: 148px;
                height: 148px;
                border-radius: 50%;
                object-fit: cover;
                margin: 0 auto 1rem auto;
                display: flex;
                border: 5px solid #FFFFFF;
                box-shadow: 0 0 0 2px var(--gold), 0 16px 34px rgba(7, 19, 41, 0.18);
            }}

            .vs-winner-photo-fallback {{
                align-items: center;
                justify-content: center;
                background: linear-gradient(145deg, {NAVY_700}, {NAVY_950});
                color: #FFFFFF;
                font-family: "Manrope", sans-serif;
                font-weight: 800;
                font-size: 3rem;
            }}

            .vs-winner-name {{
                color: var(--ink);
                font-family: "Manrope", sans-serif;
                font-size: 1.68rem;
                font-weight: 800;
            }}

            .vs-winner-sub {{
                color: var(--slate);
                font-size: 0.96rem;
                margin-top: 0.24rem;
            }}

            .vs-winner-votes {{
                color: var(--gold-dark);
                font-family: "Manrope", sans-serif;
                font-size: 1.15rem;
                font-weight: 800;
                margin-top: 0.75rem;
            }}

            .vs-winner-margin {{
                color: var(--muted);
                font-size: 0.84rem;
                margin-top: 0.28rem;
            }}

            /* ==================================================
               STEPPER
               ================================================== */

            .vs-stepper {{
                display: flex;
                gap: 0;
                margin: 0.5rem 0 0.8rem 0;
            }}

            .vs-step {{
                flex: 1;
                position: relative;
                padding: 0 0.8rem 0 0;
            }}

            .vs-step:not(:last-child)::after {{
                content: "";
                position: absolute;
                top: 15px;
                left: calc(30px + 0.45rem);
                right: 0.35rem;
                height: 2px;
                background: linear-gradient(90deg, #B7C4D6, #D7E0EC);
            }}

            .vs-step.is-done:not(:last-child)::after {{
                background: linear-gradient(90deg, var(--gold), #E3C778);
            }}

            .vs-step-num {{
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background: linear-gradient(145deg, {NAVY_700}, {NAVY_950});
                color: #FFFFFF;
                font-family: "Manrope", sans-serif;
                font-weight: 800;
                font-size: 0.78rem;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 0.55rem;
                position: relative;
                z-index: 1;
                box-shadow: 0 0 0 4px #FFFFFF, 0 0 0 5px #CBD7E4;
                transition: background 180ms var(--ease), box-shadow 180ms var(--ease);
            }}

            .vs-step.is-active .vs-step-num {{
                background: {GOLD_GRADIENT};
                color: #17233A;
                box-shadow: 0 0 0 4px #FFFFFF, 0 0 0 5px var(--gold);
            }}

            .vs-step.is-done .vs-step-num {{
                background: linear-gradient(145deg, var(--good), #0F5934);
            }}

            .vs-step-title {{
                font-family: "Manrope", sans-serif;
                font-weight: 800;
                font-size: 0.88rem;
                color: var(--ink);
                margin-bottom: 0.18rem;
            }}

            .vs-step-desc {{
                font-size: 0.80rem;
                color: var(--slate);
                line-height: 1.5;
            }}

            /* ==================================================
               DIVIDER / EMPTY STATE / STAT ROW (new, additive)
               ================================================== */

            .vs-divider {{
                display: flex;
                align-items: center;
                gap: 0.7rem;
                margin: 1.1rem 0;
                color: var(--muted);
                font-family: "Manrope", sans-serif;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }}

            .vs-divider::before,
            .vs-divider::after {{
                content: "";
                flex: 1;
                height: 1px;
                background: linear-gradient(90deg, transparent, var(--line-dark), transparent);
            }}

            .vs-empty {{
                text-align: center;
                padding: 2.5rem 1.5rem;
                border-radius: var(--radius-lg);
                border: 1px dashed rgba(183,198,215,0.95);
                background:
                    linear-gradient(
                        180deg,
                        rgba(255,255,255,0.82),
                        rgba(245,248,252,0.92)
                    );
                color: var(--slate);
                box-shadow: 0 10px 22px rgba(8,21,37,0.05);
            }}

            .vs-empty-icon {{
                font-size: 2.1rem;
                margin-bottom: 0.5rem;
            }}

            .vs-empty-title {{
                font-family: "Manrope", sans-serif;
                font-weight: 800;
                color: var(--ink);
                font-size: 1rem;
                margin-bottom: 0.3rem;
            }}

            .vs-stat-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.7rem;
                margin: 0.4rem 0 1rem 0;
            }}

            .vs-stat {{
                flex: 1;
                min-width: 140px;
                background: {SURFACE_GRADIENT};
                border: 1px solid rgba(255, 255, 255, 0.13);
                border-radius: var(--radius-md);
                padding: 0.9rem 1rem;
                box-shadow: var(--shadow-sm);
            }}

            .vs-stat-label {{
                color: #D7E3F2;
                font-size: 0.74rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}

            .vs-stat-value {{
                color: #FFFFFF;
                font-family: "Manrope", sans-serif;
                font-weight: 800;
                font-size: 1.4rem;
                margin-top: 0.2rem;
            }}

            /* ==================================================
               BUTTONS
               ================================================== */

            .stButton > button,
            .stDownloadButton > button {{
                min-height: 44px;
                font-family: "Manrope", sans-serif !important;
                font-size: 0.88rem !important;
                font-weight: 800 !important;
                letter-spacing: 0.005em;

                border-radius: 12px !important;
                border: 1px solid #B88528 !important;

                background:
                    linear-gradient(
                        135deg,
                        #EFC96D 0%,
                        #CF9D35 100%
                    ) !important;

                color: #17263B !important;

                box-shadow: var(--shadow-gold) !important;

                transition:
                    transform 140ms var(--ease),
                    box-shadow 140ms var(--ease),
                    filter 140ms var(--ease) !important;
            }}

            /* Form CTA = strongest visual action. */
            [data-testid="stForm"] .stButton > button,
            [data-testid="stForm"] .stDownloadButton > button {{
                min-height: 46px;
                font-size: 0.91rem !important;
            }}

            .stButton > button:hover,
            .stDownloadButton > button:hover {{
                transform: translateY(-2px);
                filter: brightness(1.06);
                box-shadow: 0 14px 28px rgba(165, 112, 19, 0.30) !important;
            }}

            .stButton > button:active,
            .stDownloadButton > button:active {{
                transform: translateY(1px);
                filter: brightness(0.98);
            }}

            .stButton > button:disabled,
            .stDownloadButton > button:disabled {{
                opacity: 0.55 !important;
                filter: grayscale(0.3);
                box-shadow: none !important;
                transform: none !important;
            }}

            button[kind="secondary"] {{
                background: rgba(255,255,255,0.05) !important;
                color: #F4F8FD !important;
                border-color: rgba(255,255,255,0.20) !important;
                box-shadow: none !important;
            }}

            button[kind="secondary"]:hover {{
                background: rgba(216,173,85,0.14) !important;
                border-color: rgba(216,173,85,0.56) !important;
                color: #FFF5D8 !important;
                box-shadow: 0 8px 18px rgba(8,21,37,0.12) !important;
            }}

            /* Keep primary form actions gold even when Streamlit marks them
               as secondary buttons internally. */
            [data-testid="stForm"] button[kind="secondary"] {{
                background:
                    linear-gradient(
                        135deg,
                        #EFC96D 0%,
                        #CF9D35 100%
                    ) !important;
                color: #17263B !important;
                border-color: #B88528 !important;
                box-shadow: var(--shadow-gold) !important;
            }}

            [data-testid="stForm"] button[kind="secondary"]:hover {{
                background:
                    linear-gradient(
                        135deg,
                        #F2D37F 0%,
                        #D9AB47 100%
                    ) !important;
                color: #132239 !important;
            }}

            [data-testid="stForm"] .stButton > button {{
                background: linear-gradient(135deg, #ECC46A 0%, #CB962D 100%) !important;
                border-color: #B98622 !important;
                color: #15233A !important;
            }}

            /* ==================================================
               TEXT / NUMBER / DATE INPUTS
               Clean, high-contrast fields with a restrained gold
               focus accent — the gold is a highlight, not the field
               color, which is what reads as "premium form" rather
               than "warning state".
               ================================================== */

            .stTextInput input,
            .stTextArea textarea,
            .stNumberInput input,
            .stDateInput input,
            .stTimeInput input {{
                background:
                    linear-gradient(
                        180deg,
                        #FFFDF8 0%,
                        #F8F3E8 100%
                    ) !important;

                border: 1.5px solid #D2C09A !important;
                border-radius: 12px !important;
                min-height: 47px;

                color: #20334B !important;
                caret-color: var(--gold-dark) !important;

                font-family: "DM Sans", sans-serif !important;
                font-size: 0.96rem !important;
                font-weight: 600 !important;

                padding-left: 0.95rem !important;
                padding-right: 0.95rem !important;

                box-shadow:
                    inset 0 1px 1px rgba(255,255,255,0.88),
                    0 3px 10px rgba(8,21,37,0.05) !important;

                transition:
                    border-color 150ms var(--ease),
                    box-shadow 150ms var(--ease),
                    transform 150ms var(--ease),
                    background 150ms var(--ease) !important;
            }}

            .stTextInput input:hover,
            .stTextArea textarea:hover,
            .stNumberInput input:hover,
            .stDateInput input:hover,
            .stTimeInput input:hover {{
                border-color: #D8AA4E !important;
                background:
                    linear-gradient(
                        180deg,
                        #FFFDF9 0%,
                        #F9F2E0 100%
                    ) !important;
            }}

            /* On the dark navy panels (forms / bordered containers)
               the field needs to sit on a slightly raised, cool
               surface instead of pure white so it doesn't glare. */
            [data-testid="stForm"] .stTextInput input,
            [data-testid="stForm"] .stTextArea textarea,
            [data-testid="stForm"] .stNumberInput input,
            [data-testid="stForm"] .stDateInput input,
            [data-testid="stForm"] .stTimeInput input,
            [data-testid="stVerticalBlockBorderWrapper"] .stTextInput input,
            [data-testid="stVerticalBlockBorderWrapper"] .stTextArea textarea,
            [data-testid="stVerticalBlockBorderWrapper"] .stNumberInput input,
            [data-testid="stVerticalBlockBorderWrapper"] .stDateInput input,
            [data-testid="stVerticalBlockBorderWrapper"] .stTimeInput input {{
                background: rgba(255, 255, 255, 0.96) !important;
                border-color: rgba(255, 255, 255, 0.22) !important;
            }}

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder,
            .stNumberInput input::placeholder {{
                color: var(--muted) !important;
                opacity: 1 !important;
                font-weight: 500 !important;
            }}

            .stTextInput input:hover,
            .stTextArea textarea:hover,
            .stNumberInput input:hover,
            .stDateInput input:hover,
            .stTimeInput input:hover {{
                border-color: var(--gold) !important;
            }}

            .stTextInput input:focus,
            .stTextArea textarea:focus,
            .stNumberInput input:focus,
            .stDateInput input:focus,
            .stTimeInput input:focus {{
                border-color: #D9AA49 !important;
                box-shadow:
                    0 0 0 3px rgba(216,173,85,0.18),
                    0 8px 18px rgba(8,21,37,0.08) !important;
                transform: translateY(-1px);
                background: #FFFEFB !important;
            }}

            .stTextInput input:disabled,
            .stTextArea textarea:disabled,
            .stNumberInput input:disabled,
            .stDateInput input:disabled,
            .stTimeInput input:disabled {{
                opacity: 0.55 !important;
            }}

            .stDateInput [data-baseweb="input"],
            .stTimeInput [data-baseweb="input"],
            .stNumberInput [data-baseweb="input"] {{
                border-radius: 12px !important;
                background: transparent !important;
            }}

            /* ==================================================
               SELECT / MULTISELECT — matches the text-field style
               ================================================== */

            [data-baseweb="select"] > div {{
                background: linear-gradient(180deg, #FFFDF8 0%, #F8F3E8 100%) !important;
                border: 1.5px solid #D2C09A !important;
                border-radius: 12px !important;
                min-height: 46px;
                color: var(--ink) !important;
                box-shadow: 0 1px 2px rgba(7, 19, 41, 0.04) !important;
                transition: border-color 150ms var(--ease), box-shadow 150ms var(--ease);
            }}

            [data-testid="stForm"] [data-baseweb="select"] > div,
            [data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] > div {{
                background: rgba(255, 255, 255, 0.96) !important;
                border-color: rgba(255, 255, 255, 0.22) !important;
            }}

            [data-baseweb="select"] > div:hover {{ border-color: var(--gold) !important; }}

            [data-baseweb="select"] > div:focus-within {{
                border-color: var(--gold) !important;
                box-shadow: 0 0 0 3px rgba(216, 170, 70, 0.22) !important;
            }}

            [data-baseweb="tag"] {{
                background: {NAVY_800} !important;
                border-radius: 8px !important;
            }}

            [data-baseweb="popover"] [data-baseweb="menu"] {{
                border-radius: 12px !important;
                box-shadow: var(--shadow-lg) !important;
                border: 1px solid var(--line) !important;
            }}

            [data-baseweb="menu"] li:hover {{
                background: var(--gold-soft) !important;
            }}

            /* ==================================================
               SLIDER
               ================================================== */

            [data-testid="stSlider"] [role="slider"] {{
                background: {GOLD_GRADIENT} !important;
                box-shadow: 0 3px 10px rgba(154, 108, 24, 0.35) !important;
                border: 2px solid #FFFFFF !important;
            }}

            [data-testid="stSlider"] > div > div > div > div {{
                background: {GOLD_GRADIENT} !important;
            }}

            [data-testid="stTickBar"] {{ display: none; }}

            /* ==================================================
               PROGRESS BAR
               ================================================== */

            [data-testid="stProgress"] > div > div {{
                background: {GOLD_GRADIENT} !important;
                border-radius: 999px !important;
            }}

            [data-testid="stProgress"] > div {{
                background: #E5EAF2 !important;
                border-radius: 999px !important;
            }}

            /* ==================================================
               LABELS
               ================================================== */

            label,
            .stRadio label,
            .stSelectbox label,
            .stMultiSelect label,
            .stTextInput label,
            .stTextArea label,
            .stDateInput label,
            .stTimeInput label,
            .stNumberInput label,
            .stSlider label {{
                font-family: "Manrope", sans-serif !important;
                font-weight: 800 !important;
                color: var(--ink-soft) !important;
                font-size: 0.83rem !important;
                letter-spacing: 0.01em;
                margin-bottom: 0.3rem !important;
            }}

            /* Password-eye / input action area */
            [data-baseweb="input"] button {{
                background: transparent !important;
                color: var(--slate) !important;
                border-left: 1px solid var(--line) !important;
                border-radius: 0 12px 12px 0 !important;
            }}

            [data-baseweb="input"] button:hover {{
                color: var(--gold-dark) !important;
            }}

            /* ==================================================
               FILE UPLOADER
               ================================================== */

            .stFileUploader [data-testid="stFileUploaderDropzone"] {{
                background: #FFFFFF !important;
                border: 1.5px dashed var(--line-dark);
                border-radius: 14px;
                padding: 0.7rem;
                transition: all 160ms var(--ease);
            }}

            .stFileUploader [data-testid="stFileUploaderDropzone"]:hover {{
                border-color: var(--gold);
                background: var(--gold-soft) !important;
            }}

            /* ==================================================
               RADIO / CHECKBOX / TOGGLE
               ================================================== */

            [data-testid="stRadio"] > div {{ gap: 0.45rem; }}

            [data-testid="stRadio"] label {{
                background:
                    linear-gradient(
                        145deg,
                        #2A507A,
                        #224467
                    ) !important;
                border: 1px solid rgba(255,255,255,0.12) !important;
                border-radius: 12px;
                padding: 0.62rem 0.78rem;
                color: #F4F8FD !important;
                transition:
                    border-color 150ms var(--ease),
                    transform 150ms var(--ease),
                    background 150ms var(--ease);
            }}

            [data-testid="stRadio"] label:hover {{
                border-color: rgba(216,173,85,0.56) !important;
                transform: translateX(2px);
                background:
                    linear-gradient(
                        145deg,
                        #2D5784,
                        #254A70
                    ) !important;
            }}

            [data-testid="stCheckbox"] label {{ font-weight: 700 !important; }}

            [data-testid="stToggle"] label[data-baseweb="checkbox"] > div:first-child {{
                background: #C7D2E0 !important;
            }}

            [data-testid="stToggle"] input:checked + div {{
                background: {GOLD_GRADIENT} !important;
            }}

            /* ==================================================
               METRICS
               ================================================== */

            [data-testid="stMetric"] {{
                position: relative;
                background: {SURFACE_GRADIENT} !important;
                border: 1px solid rgba(255, 255, 255, 0.11) !important;
                border-radius: var(--radius-md);
                padding: 1rem 1.05rem 0.85rem 1.05rem;
                box-shadow: var(--shadow-md);
                overflow: hidden;
                transition: transform 180ms var(--ease), box-shadow 180ms var(--ease);
            }}

            [data-testid="stMetric"]:hover {{
                transform: translateY(-2px);
                box-shadow: var(--shadow-lg);
            }}

            [data-testid="stMetric"]::after {{
                content: "";
                position: absolute;
                width: 78px;
                height: 78px;
                right: -28px;
                top: -28px;
                border-radius: 50%;
                border: 1px solid rgba(216, 170, 70, 0.18);
                background: rgba(216, 170, 70, 0.08);
            }}

            [data-testid="stMetricLabel"] {{ color: #D7E3F2 !important; font-weight: 700 !important; }}
            [data-testid="stMetricValue"] {{
                color: #FFFFFF !important;
                font-family: "Manrope", sans-serif !important;
                font-weight: 800 !important;
            }}
            [data-testid="stMetricDelta"] svg {{ color: {GOLD_LIGHT} !important; }}

            /* ==================================================
               SIDEBAR
               ================================================== */

            [data-testid="stSidebar"] {{
                background:
                    radial-gradient(300px 180px at 100% 0%, rgba(216, 170, 70, 0.13), transparent 70%),
                    linear-gradient(180deg, {NAVY_800} 0%, {NAVY_950} 82%);
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }}

            [data-testid="stSidebar"] * {{ color: #EAF0F8 !important; }}
            [data-testid="stSidebar"] hr {{ border-color: rgba(255, 255, 255, 0.12) !important; }}

            [data-testid="stSidebar"] .stRadio label {{
                background: transparent;
                border: 1px solid transparent;
                padding: 0.6rem 0.75rem;
                border-radius: var(--radius-sm);
                color: #EAF0F8 !important;
                transition: background 150ms var(--ease);
            }}

            [data-testid="stSidebar"] .stRadio label:hover {{
                background: rgba(255, 255, 255, 0.07);
                border-color: rgba(255, 255, 255, 0.07);
            }}

            [data-testid="stSidebar"] button {{
                background: rgba(255,255,255,0.055) !important;
                border: 1px solid rgba(255,255,255,0.13) !important;
                box-shadow: none !important;
                color: #F4F8FD !important;
            }}

            [data-testid="stSidebar"] button:hover {{
                background: rgba(216,173,85,0.16) !important;
                border-color: rgba(216,173,85,0.52) !important;
                color: #FFF5D8 !important;
                box-shadow: 0 8px 18px rgba(0,0,0,0.15) !important;
            }}

            [data-testid="stSidebarNav"] a {{
                border-radius: var(--radius-sm);
                margin: 0.12rem 0.3rem;
                transition: background-color 130ms var(--ease), transform 130ms var(--ease);
            }}

            [data-testid="stSidebarNav"] a:hover {{
                background: rgba(255, 255, 255, 0.07);
                transform: translateX(2px);
            }}

            [data-testid="stSidebarNav"] a[aria-current="page"] {{
                background: linear-gradient(90deg, rgba(216, 170, 70, 0.22), rgba(255, 255, 255, 0.05));
                box-shadow: inset 3px 0 0 var(--gold);
            }}

            /* ==================================================
               PREMIUM PRODUCT FINISH
               ================================================== */

            [data-testid="stVerticalBlock"],
            [data-testid="stHorizontalBlock"] {{
                scroll-margin-top: 72px;
            }}

            [data-testid="stElementContainer"] {{
                transition: opacity 120ms ease;
            }}

            .stCaption {{
                color: var(--muted) !important;
            }}

            /* Camera/video frame */
            [data-testid="stCameraInput"] {{
                border-radius: 16px !important;
                border: 1px solid rgba(255,255,255,0.15);
                box-shadow: 0 12px 26px rgba(8,21,37,0.13);
                overflow: hidden;
            }}

            /* Downloaded/selected file badge */
            [data-testid="stFileUploaderFile"] {{
                border-radius: 10px !important;
                border: 1px solid rgba(156,112,31,0.22) !important;
                background: rgba(255,249,234,0.88) !important;
            }}

            /* ==================================================
               ALERTS / TOAST / TOOLTIP
               ================================================== */

            .stAlert {{
                border-radius: 13px !important;
                border: 1px solid var(--line) !important;
                box-shadow: 0 6px 16px rgba(7, 19, 41, 0.05);
            }}

            [data-testid="stTooltipIcon"] svg {{ color: var(--gold-dark) !important; }}

            div[data-baseweb="tooltip"] {{
                background: {NAVY_950} !important;
                border-radius: 9px !important;
                font-size: 0.78rem !important;
            }}

            [data-testid="stToast"] {{
                border-radius: 14px !important;
                border: 1px solid var(--line) !important;
                box-shadow: var(--shadow-md) !important;
            }}

            /* ==================================================
               TABS
               ================================================== */

            .stTabs [data-baseweb="tab-list"] {{
                gap: 0.35rem;
                background: transparent;
                border-bottom: 1px solid var(--line);
            }}

            .stTabs [data-baseweb="tab"] {{
                font-family: "Manrope", sans-serif !important;
                font-weight: 800 !important;
                color: var(--slate) !important;
                border-radius: 9px 9px 0 0;
                padding: 0.65rem 0.8rem;
                transition: color 150ms var(--ease);
            }}

            .stTabs [data-baseweb="tab"]:hover {{ color: var(--navy-800) !important; }}

            .stTabs [aria-selected="true"] {{
                color: {NAVY_800} !important;
                box-shadow: inset 0 -3px 0 var(--gold);
            }}

            /* ==================================================
               EXPANDERS / DATAFRAMES
               ================================================== */

            [data-testid="stExpander"] {{
                background: {SURFACE_GRADIENT} !important;
                border: 1px solid rgba(255, 255, 255, 0.11) !important;
                border-radius: var(--radius-md) !important;
                box-shadow: var(--shadow-md);
            }}

            [data-testid="stExpander"] * {{ color: #F4F7FC !important; }}

            [data-testid="stDataFrame"] {{
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 14px;
                overflow: hidden;
                box-shadow: var(--shadow-md);
                background: {SURFACE_END};
            }}

            hr {{ border-color: var(--line) !important; }}

            [data-testid="stCameraInput"] {{
                border-radius: 16px;
                overflow: hidden;
            }}

            /* ==================================================
               SPINNER
               ================================================== */

            [data-testid="stSpinner"] > div {{
                border-top-color: var(--gold) !important;
            }}

            /* ==================================================
               MOBILE
               ================================================== */

            @media (max-width: 900px) {{
                .main .block-container {{
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                }}

                .vs-hero {{
                    border-radius: 19px;
                    padding: 1.5rem 1.3rem;
                }}

                .vs-hero-row {{ align-items: flex-start; }}

                .vs-hero-emblem {{
                    width: 58px;
                    height: 58px;
                    border-radius: 17px;
                    font-size: 1.55rem;
                }}

                .vs-stepper {{
                    flex-direction: column;
                    gap: 1rem;
                }}

                .vs-step:not(:last-child)::after {{ display: none; }}

                .vs-stat {{ min-width: 100%; }}
            }}

            @media (prefers-reduced-motion: reduce) {{
                *, *::before, *::after {{
                    animation: none !important;
                    transition: none !important;
                    scroll-behavior: auto !important;
                }}
            }}

            </style>
            """
        ).strip().replace("GOLD_GRADIENT_PLACEHOLDER", GOLD_GRADIENT),
        unsafe_allow_html=True,
    )


# ============================================================
# PAGE HEADER
# ============================================================

def page_header(title, subtitle="", kicker="", icon="", meta=None):
    """
    Premium hero banner.

    meta may be a list/tuple of short strings, for example:
        meta=["Secure", "Face Verified", "Constituency: Thondi"]
    """
    title_html = _safe_text(title)
    subtitle_html = _safe_text(subtitle)
    kicker_html = (
        f'<div class="vs-kicker">{_safe_text(kicker)}</div>'
        if kicker else ""
    )
    emblem_html = (
        f'<div class="vs-hero-emblem">{_safe_text(icon)}</div>'
        if icon else ""
    )

    meta_html = ""
    if meta:
        meta_items = "".join(
            f'<span class="vs-pill">{_safe_text(item)}</span>'
            for item in meta
            if str(item or "").strip()
        )
        if meta_items:
            meta_html = f'<div class="vs-hero-meta">{meta_items}</div>'

    _html(
        f"""
        <div class="vs-hero">
            <div class="vs-hero-row">
                <div class="vs-hero-copy">
                    {kicker_html}
                    <h1>{title_html}</h1>
                    <p>{subtitle_html}</p>
                    {meta_html}
                </div>
                {emblem_html}
            </div>
        </div>
        """
    )


# ============================================================
# SECTION TITLE
# ============================================================

def section_title(text, icon=""):
    """Small high-contrast section heading."""
    display = (
        f"{_safe_text(icon)} {_safe_text(text)}"
        if icon
        else _safe_text(text)
    )

    st.markdown(
        f"""
        <div style="
            display:flex;
            align-items:center;
            gap:0.45rem;
            margin:0.35rem 0 0.85rem 0;
        ">
            <span style="
                width:7px;
                height:27px;
                border-radius:999px;
                background:{GOLD};
                display:inline-block;
            "></span>
            <span style="
                font-family:'Manrope',sans-serif;
                font-size:1.08rem;
                font-weight:800;
                color:{INK};
                letter-spacing:-0.018em;
            ">{display}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SMALL UI HELPERS
# ============================================================

def pill(text):
    """Return an inline brand pill."""
    return f'<span class="vs-pill">{_safe_text(text)}</span>'


def badge(text, kind="neutral"):
    """Return an inline status badge."""
    if kind not in ("success", "pending", "danger", "neutral"):
        kind = "neutral"

    return (
        f'<span class="vs-badge vs-badge-{kind}">'
        f'{_safe_text(text)}'
        f'</span>'
    )


def feature_card(icon, title, desc):
    """Render a premium feature/benefit card."""
    _html(
        f"""
        <div class="vs-card vs-card-accent vs-feature">
            <div class="vs-feature-icon">{_safe_text(icon)}</div>
            <h4>{_safe_text(title)}</h4>
            <p>{_safe_text(desc)}</p>
        </div>
        """
    )


# ============================================================
# IMAGE HELPERS
# ============================================================

def _image_data_uri(image_bytes, mime="image/png"):
    """Base64-encode raw image bytes for inline HTML images."""
    if not image_bytes:
        return None

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


# ============================================================
# CANDIDATE CARD
# ============================================================

def candidate_card(name, subtitle="", meta="", image_bytes=None):
    """
    Render a premium candidate card.

    Falls back to an initial avatar when no photo exists.
    """
    safe_name = _safe_text(name)
    safe_subtitle = _safe_text(subtitle)

    uri = _image_data_uri(image_bytes)

    if uri:
        avatar = (
            f'<img src="{uri}" '
            f'class="vs-candidate-photo" '
            f'alt="{safe_name}" />'
        )
    else:
        initial = _safe_text((str(name or "?").strip()[:1] or "?").upper())
        avatar = (
            f'<div class="vs-candidate-photo-fallback">'
            f'{initial}'
            f'</div>'
        )

    meta_html = (
        f'<div class="vs-candidate-meta">{meta}</div>'
        if meta
        else ""
    )

    _html(
        f"""
        <div class="vs-card vs-candidate-card">
            {avatar}
            <div class="vs-candidate-name">{safe_name}</div>
            <div class="vs-candidate-sub">{safe_subtitle}</div>
            {meta_html}
        </div>
        """
    )


# ============================================================
# WINNER CARD
# ============================================================

def winner_card(
    name,
    party="",
    constituency="",
    votes=0,
    margin_text="",
    image_bytes=None,
):
    """
    Render the large results winner card.
    """
    safe_name = _safe_text(name)

    uri = _image_data_uri(image_bytes)

    if uri:
        avatar = (
            f'<img src="{uri}" '
            f'class="vs-winner-photo" '
            f'alt="{safe_name}" />'
        )
    else:
        initial = _safe_text(
            (str(name or "?").strip()[:1] or "?").upper()
        )
        avatar = (
            f'<div class="vs-winner-photo-fallback">'
            f'{initial}'
            f'</div>'
        )

    sub_parts = [
        _safe_text(value)
        for value in (party, constituency)
        if str(value or "").strip()
    ]

    sub_html = ""
    if sub_parts:
        sub_html = (
            f'<div class="vs-winner-sub">'
            f'{" · ".join(sub_parts)}'
            f'</div>'
        )

    margin_html = ""
    if str(margin_text or "").strip():
        margin_html = (
            f'<div class="vs-winner-margin">'
            f'{_safe_text(margin_text)}'
            f'</div>'
        )

    try:
        votes_display = f"{int(votes):,}"
    except (TypeError, ValueError):
        votes_display = _safe_text(votes)

    _html(
        f"""
        <div class="vs-winner-card">
            <div class="vs-winner-ribbon">🏆 WINNER</div>
            {avatar}
            <div class="vs-winner-name">{safe_name}</div>
            {sub_html}
            <div class="vs-winner-votes">
                {votes_display} votes
            </div>
            {margin_html}
        </div>
        """
    )


# ============================================================
# STEPPER
# ============================================================

def stepper(steps):
    """
    Render a numbered process stepper.

    steps:
        [
            ("Register", "Submit voter details"),
            ("Verify", "Complete face verification"),
            ("Vote", "Select your candidate"),
        ]

    Optionally pass a status as a 3rd item to color the step:
        ("Register", "Submit voter details", "done")     # gold->green
        ("Verify", "Complete face verification", "active") # gold highlight
        ("Vote", "Select your candidate", "todo")           # default (or omit)
    """
    items = []

    for i, item in enumerate(steps or [], start=1):
        if not item or len(item) < 2:
            continue

        title, desc = item[0], item[1]
        status = item[2] if len(item) > 2 else ""
        status_class = ""
        if status == "done":
            status_class = "is-done"
        elif status == "active":
            status_class = "is-active"

        items.append(
            textwrap.dedent(
                f"""
                <div class="vs-step {status_class}">
                    <div class="vs-step-num">{i}</div>
                    <div class="vs-step-title">
                        {_safe_text(title)}
                    </div>
                    <div class="vs-step-desc">
                        {_safe_text(desc)}
                    </div>
                </div>
                """
            ).strip()
        )

    _html(
        f'<div class="vs-stepper">{"".join(items)}</div>'
    )


# ============================================================
# NEW ADDITIVE HELPERS (optional — nothing existing depends on these)
# ============================================================

def divider(label=""):
    """Render a labeled or plain section divider."""
    _html(f'<div class="vs-divider">{_safe_text(label)}</div>')


def empty_state(icon, title, desc=""):
    """Render a dashed placeholder panel for empty lists/tables."""
    desc_html = (
        f'<p style="margin-top:0.3rem;font-size:0.88rem;">{_safe_text(desc)}</p>'
        if desc else ""
    )
    _html(
        f"""
        <div class="vs-empty">
            <div class="vs-empty-icon">{_safe_text(icon)}</div>
            <div class="vs-empty-title">{_safe_text(title)}</div>
            {desc_html}
        </div>
        """
    )


def stat_row(stats):
    """
    Render a row of compact stat chips.

    stats: [("Registered", "12,480"), ("Turnout", "68%"), ...]
    """
    items = "".join(
        f"""
        <div class="vs-stat">
            <div class="vs-stat-label">{_safe_text(label)}</div>
            <div class="vs-stat-value">{_safe_text(value)}</div>
        </div>
        """
        for label, value in (stats or [])
    )
    _html(f'<div class="vs-stat-row">{items}</div>')