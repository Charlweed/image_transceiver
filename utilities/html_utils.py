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


import base64
import logging
import os
import sys
import tempfile
from enum import Enum, auto

GREEN_SQUARE_SRC=r"data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAABGdBTUEAALGPC/xhBQAAAAFzUkdCAK7OHOkAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAABZJREFUGNNjZPjP8J8BD2BiIACGhwIAEVwCDkpesjsAAAAASUVORK5CYII="  # noqa
RED_DOT_SRC = r"data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="  # noqa
SRC_ATTRIBUTE_FILENAME = "src_attribute.txt"
TINY_PNG_SRC = r"data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQYV2NgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="  # noqa
__GREEN_DIAMOND_FILE_PATH  = r"custom_nodes/image_transceiver/js/green_diamond_00.png"  # noqa
__GREEN_PIXEL_FILE_PATH    = r"custom_nodes/image_transceiver/js/green_pixel_00.png"  # noqa
__GREEN_SQUARE_FILE_PATH   = r"custom_nodes/image_transceiver/js/green_square_8x8.png"  # noqa
__LAMP_FILE_PATH           = r"custom_nodes/image_transceiver/js/magic_lamp_160x86.png"  # noqa


class ImageFormat(Enum):
    APNG = auto()
    AVIF = auto()
    BMP = auto()
    GIF = auto()
    ICO = auto()
    JPEG = auto()
    PNG = auto()
    SVG = auto()
    WebP = auto()

    @property
    def attribute_prefix(self) -> str:
        lowered = self.name.lower()
        return f"data:image/{lowered};base64, "


class SrcAttributeExample(Enum):
    GREEN_DIAMOND = auto()
    GREEN_PIXEL = auto()
    GREEN_SQUARE = auto()
    MAGIC_LAMP = auto()


def image_b64_str_to_attribute(img_base64_str: str, image_format: ImageFormat = ImageFormat.PNG) -> str:
    """
    Converts the base64 encoded string of an image into the src attribute for an img tag.
    Parameters
    ----------
    img_base64_str The base64 encoded string of an image.
    image_format The format of the image as enumerated by ImageFormat
    Returns
    -------
    The src attribute for an img tag.
    """
    attribute: str = f"{image_format.attribute_prefix}{img_base64_str}"
    return attribute


def image_b64_bytes_to_attribute(image_bytes: bytes, image_format: ImageFormat = ImageFormat.PNG) -> str:
    """
    Converts the base64 encoded bytes of an image into the src attribute for an img tag.
    Parameters
    ----------
    image_bytes The base64 encoded bytes of an image.
    image_format The format of the image as enumerated by ImageFormat
    Returns
    -------
    The src attribute for an img tag.
    """
    img_base64_str = image_bytes.decode(encoding='utf-8')  # convert bytes to string
    attribute: str = image_b64_str_to_attribute(img_base64_str=img_base64_str, image_format=image_format)
    return attribute


def _load_image_bytes(png_file_path_str: str = __GREEN_SQUARE_FILE_PATH) -> bytes:
    logging.warning(f"Current Working Directory={os.getcwd()}")
    with open(png_file_path_str, "rb") as data:
        data_base64 = base64.b64encode(data.read())  # encode to base64 (bytes)
        return data_base64


def lamp_image_bytes() -> bytes:
    return _load_image_bytes(png_file_path_str=__LAMP_FILE_PATH)


def make_src_attribute(example: SrcAttributeExample = SrcAttributeExample.GREEN_SQUARE) -> str:
    image_bytes: bytes
    match example:
        case SrcAttributeExample.GREEN_DIAMOND:
            image_bytes = _load_image_bytes(png_file_path_str=__GREEN_DIAMOND_FILE_PATH)
        case SrcAttributeExample.GREEN_PIXEL:
            image_bytes = _load_image_bytes(png_file_path_str=__GREEN_PIXEL_FILE_PATH)
        case SrcAttributeExample.GREEN_SQUARE:
            image_bytes = _load_image_bytes()
        case SrcAttributeExample.MAGIC_LAMP:
            image_bytes = _load_image_bytes(png_file_path_str=__LAMP_FILE_PATH)
        case _:
            raise NotImplemented(f"No file path for {example}")
    src_attribute = image_b64_bytes_to_attribute(image_bytes=image_bytes)
    return src_attribute


def _store_image_str():
    attribute = make_src_attribute()
    attribute_fyle_name = os.path.join(tempfile.gettempdir(), SRC_ATTRIBUTE_FILENAME)
    logging.warning(f"store_image_str(): filename \"{attribute_fyle_name}\"")
    # Open the file for writing
    with open(attribute_fyle_name, 'w') as fyle:
        fyle.write(attribute)
        fyle.write("\n")


def main() -> int:
    _store_image_str()
    return 0


if __name__ == "__main__":
    sys.exit(main())
