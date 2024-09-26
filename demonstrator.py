#  Copyright (c) 2024. Charles Hymes
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from websockets.sync.client import connect
from utilities.html_utils import *

DEMONSTRATOR_LOGGER: logging.Logger = logging.getLogger("ImageTransceiver")
DEMONSTRATOR_LOGGER_FORMAT: str = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter(DEMONSTRATOR_LOGGER_FORMAT)
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
DEMONSTRATOR_LOGGER.propagate = False
DEMONSTRATOR_LOGGER.addHandler(ch)


def main() -> int:
    lamp_bytes: bytes = lamp_image_bytes()
    lamp_img_str = lamp_bytes.decode(encoding='utf-8')  # convert bytes to string
    with connect("ws://localhost:8765") as websocket:
        websocket.send(lamp_img_str)
        message = websocket.recv()
        DEMONSTRATOR_LOGGER.warning(f"Received: {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
