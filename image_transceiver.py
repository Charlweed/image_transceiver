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

import asyncio
import json
import hashlib
import logging
import numpy as np
import time
import torch
from PIL import Image, ImageOps
from io import BytesIO
from server import PromptServer  # noqa
from torch import Tensor
from typing import Dict
from websockets import serve, WebSocketServer, WebSocketServerProtocol
from image_transceiver.utilities.html_utils import *

TRANSCEIVER_NODE_LOGGER: logging.Logger = logging.getLogger("ImageTransceiver")
TRANSCEIVER_NODE_LOGGER_FORMAT: str = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter(TRANSCEIVER_NODE_LOGGER_FORMAT)
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
TRANSCEIVER_NODE_LOGGER.propagate = False
TRANSCEIVER_NODE_LOGGER.addHandler(ch)
TRANSCEIVER_MSG_KEY = "TRANSCEIVER_MSG"


def _is_json(maybe_json):
    try:
        json.loads(maybe_json)
    except ValueError as val_err:  # noqa
        return False
    return True


class ServerOperation(Enum):
    START = auto()
    STOP = auto()
    RESTART = auto()
    REPORT = auto()


class ControllerCommand(Enum):
    """
    Commands for the Transceiver_Controller. Often, will be forwarded to ComfyUI.
    Ideally, this would be in a single module used by both GIMP and ComfyUI.
    """
    # Usage: Brackets for name, parentheses for value
    ATTENTION = "command"
    CONFIG = "config"
    ENQUEUE_PROMPT = "enqueue_prompt"
    ABORT_WORKFLOW = "abort_workflow"


class PayloadType(Enum):
    """
    Keep in sync with strings in image_transceiver_controller.js
    """
    PICT_CHA = "pict_cha"
    COMFYUI_CMD = "comfyui_command"


class ImageTransceiverCore:
    # No connections can send messages exceeding the max_size parameter.
    MAX_MEMORY_USAGE = 1_073_741_824  # bytes. 1gb

    def __init__(self):
        TRANSCEIVER_NODE_LOGGER.setLevel(level=logging.DEBUG)
        TRANSCEIVER_NODE_LOGGER.warning(f"{self.__class__.__name__} Constructor")
        self._image_field: Image = Image.new("RGB", (1, 1), (255, 255, 255))
        self._transceiver_port: int = 8765
        self._server_future: asyncio.Future | None = None
        self._future_result: asyncio.Future | None = None

    @property
    def transceiver_port(self) -> int:
        return self._transceiver_port

    @transceiver_port.setter
    def transceiver_port(self, port: int):
        self._transceiver_port = port

    @property
    def image_pil(self) -> Image:
        return self._image_field

    @image_pil.setter
    def image_pil(self, image_val: Image):
        if not image_val:
            raise ValueError(f"Cannot assign \"None\" as image_pil on transceiver core.")
        self._image_field = image_val
        assignment_msg: str = f"Assigned PIL image to transceiver core."
        TRANSCEIVER_NODE_LOGGER.warning(assignment_msg)

    def handle_image_msg(self, img_base64_str: str):
        TRANSCEIVER_NODE_LOGGER.debug(f"incoming_image string={img_base64_str[:32]}... ")
        src_attribute: str = image_b64_str_to_attribute(img_base64_str=img_base64_str)
        image_sabot: Dict[str, str] = {PayloadType.PICT_CHA.value: src_attribute}

        # json_str: str = json.dumps(obj=image_sabot, indent=4, sort_keys=True)
        # TRANSCEIVER_NODE_LOGGER.warning(json_str)
        PromptServer.instance.send_sync(TRANSCEIVER_MSG_KEY, image_sabot)
        pil_image: Image = Image.open(BytesIO(base64.b64decode(img_base64_str)))
        image_description_msg: str = f"Created PIL image from incoming_image:"
        f" format={pil_image.format};"
        f" size={pil_image.size};"
        f" mode={pil_image.mode};"
        f" info={pil_image.info}"
        TRANSCEIVER_NODE_LOGGER.debug(image_description_msg)
        self.image_pil = pil_image

    def handle_json_msg(self, json_text: str):
        TRANSCEIVER_NODE_LOGGER.debug(f"incoming json_text... \n ${json_text}")
        parsed_message = json.loads(json_text)
        command_str: str = parsed_message[ControllerCommand.ATTENTION.value]
        # Brackets for name, parentheses for value
        command: ControllerCommand = ControllerCommand(command_str)
        dirty: bool = False
        match command:
            case ControllerCommand.CONFIG:
                if "port" in parsed_message:
                    dirty = True
                    self.transceiver_port = parsed_message["port"]
                if dirty:
                    self.server_control(ServerOperation.RESTART)
            case ControllerCommand.ENQUEUE_PROMPT:
                TRANSCEIVER_NODE_LOGGER.debug(f"{command}... \n ${json_text}")
                cmd_sabot: Dict[str, str] = {PayloadType.COMFYUI_CMD.value: command.value}
                sabot_text: str = json.dumps(obj=cmd_sabot, indent=4, sort_keys=True)
                TRANSCEIVER_NODE_LOGGER.warning(sabot_text)
                PromptServer.instance.send_sync(TRANSCEIVER_MSG_KEY, cmd_sabot)
            case _:
                raise NotImplemented(f"Unsupported command \"{command}\"")

    def server_control(self, operation: ServerOperation):
        TRANSCEIVER_NODE_LOGGER.warning(f"server_control; Operation {operation}")
        match operation:
            case ServerOperation.STOP:
                if self._server_future is not None:
                    self._server_future.cancel("Stopped")
                    self._server_future = None
            case ServerOperation.START:
                self._run_server_coroutine()
            case ServerOperation.RESTART:
                if self._server_future is not None:
                    self._server_future.cancel("Stopped")
                    self._server_future = None
                    time.sleep(0.25)
                    self._run_server_coroutine()
            case ServerOperation.REPORT:
                pass
            case _:
                raise NotImplemented(f"Unsupported operation {operation}")

    # noinspection PyMethodMayBeStatic
    async def _relay_to_comfy(self, client_websocket: WebSocketServerProtocol):
        TRANSCEIVER_NODE_LOGGER.info("relay_to_comfy invoked")
        incoming_message: str
        try:  # Getting and sending messages can raise exceptions
            async for incoming_message in client_websocket:
                try:  # processing the message can raise exceptions.
                    is_json = _is_json(maybe_json=incoming_message)
                    if is_json:
                        self.handle_json_msg(json_text=incoming_message)
                    else:
                        self.handle_image_msg(img_base64_str=incoming_message)
                except Exception as ex_err1:
                    TRANSCEIVER_NODE_LOGGER.exception(ex_err1)
                outgoing_message: str = f"Sent a {TRANSCEIVER_MSG_KEY} json string to ComfyServer."
                TRANSCEIVER_NODE_LOGGER.info(outgoing_message)
                await client_websocket.send(outgoing_message)
        except Exception as ex_err0:
            TRANSCEIVER_NODE_LOGGER.exception(ex_err0)

    async def _run_server(self):
        TRANSCEIVER_NODE_LOGGER.info("_run_server invoked")
        ws_server: WebSocketServer
        # No connections can send messages exceeding the max_size parameter.
        async with serve(ws_handler=self._relay_to_comfy,
                         host="localhost",
                         port=self._transceiver_port,
                         max_size=ImageTransceiverCore.MAX_MEMORY_USAGE,
                         logger=TRANSCEIVER_NODE_LOGGER) as ws_server:
            TRANSCEIVER_NODE_LOGGER.info("server obtained, waiting for close ...")
            await ws_server.wait_closed()

    def _run_server_coroutine(self):
        TRANSCEIVER_NODE_LOGGER.info("_run_server_coroutine invoked")
        if self._server_future is not None:
            TRANSCEIVER_NODE_LOGGER.warning("Transceiver server is already running.")
            return
        try:
            this_loop = asyncio.get_running_loop()
            self._server_future = asyncio.run_coroutine_threadsafe(self._run_server(), this_loop)
            time.sleep(0.25)
        except RuntimeError as r_error:
            TRANSCEIVER_NODE_LOGGER.exception(r_error)


class ImageTransceiver:
    """
    An example node

    Class methods
    -------------
    INPUT_TYPES (dict):
        Tell the main program input parameters of nodes.
    IS_CHANGED:
        optional method to control when the node is re-executed.

    Attributes
    ----------
    RETURN_TYPES (`tuple`):
        The type of each element in the output tuple.
    RETURN_NAMES (`tuple`):
        Optional. The name of each output in the output tuple.
    FUNCTION (`str`):
        The name of the entry-point method. For example, if `FUNCTION = "execute"` then it will run Example().execute()
    OUTPUT_NODE ([`bool`]):
        If this node is an output node that outputs a result/image from the graph. The SaveImage node is an example.
        The backend iterates on these output nodes and tries to execute all their parents if their parent graph is
         properly connected.
        Assumed to be False if not present.
    CATEGORY (`str`):
        The category the node should appear in the UI.
    execute(s) -> tuple || None:
        The entry point method. The name of this method must be the same as the value of property `FUNCTION`.
        For example, if `FUNCTION = "execute"` then this method's name must be `execute`, if `FUNCTION = "foo"` then it
        must be `foo`.
    """

    RETURN_TYPES = (
        "IMAGE",  # a 2nd order Tensor, aka matrix, ie "image_tensor: Tensor = torch.from_numpy(image_np_array)[None,]"
        "MASK"
        )
    #
    # RETURN_NAMES = ("image_output_name",)

    FUNCTION = "flow_image"

    # OUTPUT_NODE = False

    # Consider the categories "real-time", "live" or "client-server"
    CATEGORY = "image"  # "image" is an existing category in ComfyUI. Nodes can make their own categories too.

    TRANSCEIVER_CORE: ImageTransceiverCore = ImageTransceiverCore()

    @classmethod
    def IS_CHANGED(cls, print_to_stream, node_id):  # noqa
        """
            The node will always be re-executed if any of the inputs change but
            this method can be used to force the node to execute again even when the inputs don't change.
            You can make this node return a number or a string. This value will be compared to the one returned the last
            time the node was executed, if it is different the node will be executed again.
            This method is used in the core repo for the LoadImage node where they return the image hash as a string,
            if the image hash changes between executions the LoadImage node is executed again.
        """
        TRANSCEIVER_NODE_LOGGER.info(f"{cls.__name__} IS_CHANGED() invoked.")  # So far, I have not seen this invoked.
        hash_val: str = "A020988"  # 42. Google it.
        if ImageTransceiver.TRANSCEIVER_CORE.image_pil is not None:
            pil_image: Image = ImageTransceiver.TRANSCEIVER_CORE.image_pil
            image_bytes: bytes = pil_image.tobytes()
            image_hasher = hashlib.sha256(image_bytes)
            hash_val = image_hasher.hexdigest()
        return hash_val

    @classmethod
    def INPUT_TYPES(cls):  # noqa
        """
            Return a dictionary which contains config for all input fields.
            Some types (string): "MODEL", "VAE", "CLIP", "CONDITIONING", "LATENT", "IMAGE", "INT", "STRING", "FLOAT".
            Input types "INT", "STRING" or "FLOAT" are special values for fields on the node.
            The type can be a list for selection.

            Returns: `dict`:
                - Key input_fields_group (`string`): Can be either required, hidden or optional. A node class must have
                 property `required`
                - Value input_fields (`dict`): Contains input fields config:
                    * Key field_name (`string`): Name of an entry-point method's argument
                    * Value field_config (`tuple`):
                        + First value is a string indicate the type of field or a list for selection.
                        + Second value is a config for type "INT", "STRING" or "FLOAT".
        """
        TRANSCEIVER_NODE_LOGGER.info(f"{cls.__name__} INPUT_TYPES() invoked.")
        TRANSCEIVER_NODE_LOGGER.info("Calling server_control.")
        ImageTransceiver.TRANSCEIVER_CORE.server_control(ServerOperation.START)
        return {
            "required": {
                "print_to_stream": (["enable", "disable"],),
            },
            "hidden": {"node_id": "UNIQUE_ID"},  # Add the hidden key
        }

    def __init__(self):
        """
        There is NO INSTANCE of ImageTransceiver until the workflow is flowing, and obviously the constructor is not
        invoked either ...😔
        """
        TRANSCEIVER_NODE_LOGGER.info(f"{self.__class__.__name__} Constructor")
        self._image_tensor: Tensor | None = None
        self._mask_tensor: Tensor | None = None

    @property
    def image_tensor(self) -> Tensor:
        return self._image_tensor

    @image_tensor.setter
    def image_tensor(self, image_tensor_arg: Tensor):
        self._image_tensor = image_tensor_arg

    @property
    def mask_tensor(self) -> Tensor:
        return self._mask_tensor

    @mask_tensor.setter
    def mask_tensor(self, mask_tensor_arg: Tensor):
        self._mask_tensor = mask_tensor_arg

    # noinspection PyMethodMayBeStatic
    def flow_image(self, print_to_stream, node_id) -> tuple[Tensor, Tensor]:
        message: str = f"""Your input contains:
                node_id: {node_id}
            """
        TRANSCEIVER_NODE_LOGGER.info(message)
        if print_to_stream == "enable":
            print(message)
        # Refactored from https://www.comfydocs.org/essentials/custom_node_images_and_masks
        #  and
        #  <projects>/ComfyUI/nodes.py method load_image(self, image) lines 1513-1519
        # Less reuse of identifiers, and I added type hints.
        image_pil: Image = ImageOps.exif_transpose(ImageTransceiver.TRANSCEIVER_CORE.image_pil)  # Can be None
        if image_pil is not None:
            if image_pil.mode == 'I':
                image_pil = image_pil.point(lambda i: i * (1 / 255))
            image_pil_converted: Image = image_pil.convert("RGB")
            image_np_array = np.array(image_pil_converted).astype(np.float32) / 255.0
            image_tensor: Tensor = torch.from_numpy(image_np_array)[None,]
            self.image_tensor = image_tensor
            if 'A' in image_pil.getbands():
                mask = np.array(image_pil.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
            self.mask_tensor = mask.unsqueeze(0)
        return self.image_tensor, self.mask_tensor
