from fasthtml.common import (
    H1,
    H2,
    H3,
    A,
    Card,
    Container,
    Div,
    Grid,
    P,
    Style,
    Title,
    fast_app,
)

app, rt = fast_app()


@rt("/")
def get():
    hero_section = Div(
        H1("PodFlix", cls="hero-title"),
        P("Chat with your favorite podcasts using AI", cls="hero-subtitle"),
        A("Try it now!", href="/chat", cls="button-primary"),
        cls="hero-section",
    )

    features = Grid(
        Card(
            H3("Upload"),
            P("Simply upload your podcast or audio file"),
            cls="feature-card",
        ),
        Card(
            H3("Transcribe"),
            P("Advanced AI converts speech to text with high accuracy"),
            cls="feature-card",
        ),
        Card(
            H3("Chat"),
            P("Have interactive conversations about the content"),
            cls="feature-card",
        ),
        cls="features-grid",
    )

    content = Container(
        # Div(A("Go to Chat", href="/chat", cls="chat-button"), cls="nav-bar"),
        hero_section,
        Div(H2("How it works", cls="section-title"), features, cls="features-section"),
    )

    styles = Style("""
        .nav-bar {
            display: flex;
            justify-content: flex-end;
            padding: 1rem;
            position: fixed;
            top: 0;
            right: 0;
            width: 100%;
            z-index: 100;
        }

        .chat-button {
            background: var(--primary);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            text-decoration: none;
            transition: transform 0.2s;
        }

        .chat-button:hover {
            transform: translateY(-2px);
        }

        .hero-section {
            text-align: center;
            padding: 6rem 2rem 4rem 2rem;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            margin-bottom: 2rem;
        }

        .hero-title {
            font-size: 3.5rem;
            margin-bottom: 1rem;
        }

        .hero-subtitle {
            font-size: 1.5rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }

        .button-primary {
            display: inline-block;
            padding: 1rem 2rem;
            font-size: 1.2rem;
            background: black;
            border-radius: 2rem;
            text-decoration: none;
            transition: transform 0.2s;
        }

        .button-primary:hover {
            transform: translateY(-2px);
        }

        .section-title {
            text-align: center;
            margin-bottom: 3rem;
        }

        .features-section {
            padding: 4rem 2rem;
        }

        .features-grid {
            gap: 2rem;
        }

        .feature-card {
            text-align: center;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }

        .feature-card:hover {
            transform: translateY(-5px);
        }

        @media (max-width: 768px) {
            .hero-title {
                font-size: 2.5rem;
            }

            .hero-subtitle {
                font-size: 1.2rem;
            }
        }
    """)

    return Title("PodFlix - Chat with your Podcasts"), styles, content
