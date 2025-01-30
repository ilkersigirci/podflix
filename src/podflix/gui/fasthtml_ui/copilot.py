from fasthtml.common import Script, Titled, fast_app

app, rt = fast_app()


@rt("/")
def get():
    return Titled(
        "Chainlit Copilot Demo",
        Script(src="http://localhost:5000/chat/copilot/index.js"),
        Script("""
            window.mountChainlitWidget({
                chainlitServer: "http://localhost:5000/chat",
                customCssUrl: '/public/copilot.css',
            });
        """),
    )
