from pathlib import Path

import chainlit as cl
from chainlit.auth import get_current_user
from chainlit.context import init_http_context
from chainlit.utils import mount_chainlit
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from typing_extensions import Annotated

from podflix.env_settings import env_settings
from podflix.gui.fasthtml_ui.home import app as fasthtml_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return RedirectResponse(url="/home")


@app.get("/chainlit-message-test")
async def chainlit_message_send(
    request: Request,
    current_user: Annotated[cl.User, Depends(get_current_user)],
):
    init_http_context(user=current_user)

    logger.debug(f"Current User: {current_user}")

    logger.debug(f"Request: {request}")

    await cl.Message(content="Hello World").send()

    return HTMLResponse("Hello World")


# Mount fasthtml app
app.mount(app=fasthtml_app, path="/home")


# Mount chainlit app
mount_chainlit(
    app=app,
    path="/chat",
    target=Path(__file__)
    .parent.joinpath(f"{env_settings.chainlit_app_type}.py")
    .absolute()
    .as_posix(),
)
