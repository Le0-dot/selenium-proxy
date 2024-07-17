import logging

from selenium.webdriver import Remote, FirefoxOptions, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from . import messages_pb2


def start(args: messages_pb2.StartSession) -> WebDriver:
    browser_options = {
        messages_pb2.Browser.BROWSER_FIREFOX: FirefoxOptions,
        messages_pb2.Browser.BROWSER_CHROME: ChromeOptions
    }
    return Remote(
        command_executor=args.url,
        options=browser_options[args.browser](),
    )


def open_page(
    args: messages_pb2.OpenPage, driver: WebDriver, response: messages_pb2.Response
) -> None:
    logger = logging.getLogger("uvicorn")
    try:
        driver.get(args.url)
    except WebDriverException:
        logger.info("could not reach \"%s\"", args.url)
        response.error = "could not reach url"
        return
    response.result = driver.current_url


def find(
    args: messages_pb2.Find, driver: WebDriver, response: messages_pb2.Response
) -> None:
    logger = logging.getLogger("uvicorn")
    by_table = {
        messages_pb2.By.BY_TAG: By.TAG_NAME,
        messages_pb2.By.BY_ID: By.ID,
        messages_pb2.By.BY_CLASS: By.CLASS_NAME,
        messages_pb2.By.BY_CSS: By.CSS_SELECTOR,
        messages_pb2.By.BY_NAME: By.NAME,
    }
    try:
        element = driver.find_element(by_table[args.by], args.value)
    except NoSuchElementException:
        logger.info(
            "could not find element \"by %s\" \"%s\" on \"%s\"", by_table[args.by], args.value, driver.current_url
        )
        response.error = "no such element"
        return
    attribute = element.get_attribute(args.attribute or "outerHTML")
    if attribute:
        response.result = attribute
    else:
        logger.info(
            "could not find \"%s\" attribute for element \"by %s\" \"%s\" on \"%s\"",
            args.attribute,
            by_table[args.by],
            args.value,
            driver.current_url,
        )
        response.error = "no such attribute for given element"
