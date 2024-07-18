from os import getenv
from functools import cache
from logging import getLogger
from typing import Any, Callable
from inspect import getmembers, isfunction

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from selenium.webdriver.remote.webdriver import WebDriver

from . import messages_pb2
from . import actions

app = FastAPI(
    docs_url=None,
    redoc_url=None,
)


async def receive_proto(ws: WebSocket, message: Any) -> None:
    data = await ws.receive_text()
    message.ParseFromString(data.encode("utf-8"))


async def send_proto(ws: WebSocket, message: Any) -> None:
    data = message.SerializeToString()
    await ws.send_bytes(data)


@cache
def action_dict() -> dict[str, Callable[[Any, WebDriver], messages_pb2.Response]]:
    return {
        name: func for name, func in getmembers(actions, isfunction) if name != "start"
    }


def dispatch(request: messages_pb2.Request, driver: WebDriver) -> messages_pb2.Response:
    logger = getLogger("uvicorn")
    logger.info("dispatching a request")

    request_type = request.WhichOneof("request")
    logger.info('request of type "%s"', request_type)

    if request_type is None:
        return messages_pb2.Response(error="no request data")

    data = getattr(request, request_type)
    return action_dict()[request_type](data, driver)


@app.websocket("/")
async def proxy(ws: WebSocket):
    logger = getLogger("uvicorn")

    await ws.accept()
    start_session = messages_pb2.StartSession()
    await receive_proto(ws, start_session)

    with actions.start(start_session) as driver:
        logger.info("started selenium session")
        request = messages_pb2.Request()
        try:
            while True:
                await receive_proto(ws, request)
                response = dispatch(request, driver)
                await send_proto(ws, response)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.exception(e)


def main() -> None:
    host = getenv("SELENIUM_PROXY_LISTEN", "0.0.0.0")
    port = getenv("SELENIUM_PROXY_PORT", 80)
    log_level = getenv("SELENIUM_PROXY_LOG_LEVEL", "info")
    root_path = getenv("SELENIUM_PROXY_ROOT_PATH", "")

    uvicorn.run(
        app,
        host=host,
        port=int(port),
        log_level=log_level,
        root_path=root_path,
    )


if __name__ == "__main__":
    main()
