import logging
from os import getenv
from typing import Any
from inspect import getmembers, isfunction

from selenium.webdriver.remote.webdriver import WebDriver
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

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


def dispatch(request: messages_pb2.Request, driver: WebDriver) -> messages_pb2.Response:
    logger = logging.getLogger("uvicorn")
    logger.info("dispatching a request")

    if not hasattr(dispatch, "action_dict"):
        dispatch.action_dict = {
            name: func for name, func in getmembers(actions, isfunction)
        }

    request_type = request.WhichOneof("request")
    data = getattr(request, request_type)
    response = messages_pb2.Response()

    logger.info("request of type \"%s\"", request_type)

    dispatch.action_dict[request_type](data, driver, response)
    return response


@app.websocket("/")
async def proxy(ws: WebSocket):
    logger = logging.getLogger("uvicorn")

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
