from fasthtml.common import Script, Titled, fast_app

app, rt = fast_app()


@rt("/")
def get():
    return Titled(
        "Chainlit Copilot Demo",
        # Add the Chainlit widget scripts
        Script(src="http://localhost:5000/copilot/index.js"),
        Script("""
            window.mountChainlitWidget({
                chainlitServer: "http://localhost:5000",
            });
        """),
    )
