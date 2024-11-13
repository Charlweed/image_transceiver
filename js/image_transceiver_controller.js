/**
 * @licence MIT
 * Copyright (c) 2024. Charles Hymes
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the “Software”), to deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
 * and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of
 * the Software.
 *
 * THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
 * THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

/**
 * ComfyUI is based on LiteGraph https://github.com/jagenjo/litegraph.js/blob/master/guides/README.md
 * Guides are available at https://github.com/jagenjo/litegraph.js/blob/master/guides/README.md
 * Clone the repo to read the docs i.e. file:///L:/projects/3rd_party/litegraph.js/doc/index.html
 * There is an empty wiki https://github.com/jagenjo/litegraph.js/wiki
 */
/* BTW: Firefox show console keyboard shortcut is ctrl+shift+k */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

/**
 * Controller for browser view and python model. Holds state so callbacks like renderTransceiverViewNode() can draw
 * the node with its canvasRenderingContext2D.
 */
class ImageTransceiverController {

  /********  Payload Types  ************/
  /** @type {string} Keep in sync with PayloadType enum in image_transceiver.py */
  static PICT_CHA_KEY = "pict_cha";
  /** @type {string} Keep in sync with PayloadType enum in image_transceiver.py */
  static COMFYUI_CMD = "comfyui_command";

  /********  Controller Commands  ************/
  /** @type {string} Keep in sync with ControllerCommand enum in image_transceiver.py */
  static ATTENTION = "command";
  /** @type {string} Keep in sync with ControllerCommand enum in image_transceiver.py */
  /** @type {string} Keep in sync with ControllerCommand enum in image_transceiver.py */
  static CONFIG = "config";
  /** @type {string} Keep in sync with ControllerCommand enum in image_transceiver.py */
  static ENQUEUE_PROMPT = "enqueue_prompt";
  /** @type {string} Keep in sync with ControllerCommand enum in image_transceiver.py */
  static ABORT_WORKFLOW = "abort_workflow";


  /********  Base64 Encoded PNGs ************/
  /** @type {string} */
  static SRC_DIAMOND_GREEN = "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAIAAAC0Ujn1AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAEDSURBVEhLtZJBEoMwDAP7lr6nn+0LqUGChsVOwoGdvTSSNRz6Wh7jxvT7+wn9Y4LZae0e+rXLeBqjh45rBtOYgy4V9KYxlOpqRjmNiY4+uJBP41gOI5BM40w620AknTVwGgfSWQMK0tnOaRpV6ewCatLZxn8aJemsAGXp7JhGLBX1wYlUtE4jkIpnwKGM9xeepG7mwblMpl2/CUbCJ7+6CnQzAw5lvD/8DxGIpbMClKWzdjpASTq7gJp0tnGaDlCVzhpQkM52OB3gQDrbQCSdNSTTAc7kMAL5dIDjjj64UE4HmEh1NaM3HWAIulQwmA4wd+i4ZjwdYDR00GVqWsyPrizLD76QCPOHqP2cAAAAAElFTkSuQmCC";
  /** @type {string} */
  static SRC_DOT_RED = "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";



  /** @type {string} */
  static TRANSCEIVER_MSG_KEY = "TRANSCEIVER_MSG";
 /** @type {string} The version of this class. Synchronize with value in __init__.py and in gimp_comfyui.py */
  static VERSION = "0.7.10"

  /**
   * The content to draw in the node. Should be a base64 encoded data url.
   * @type {string} the src attribute of the HTMLImageElement transceiverImage
   */
  PNG_Data = ImageTransceiverController.SRC_DIAMOND_GREEN;

  /**
   * @typedef {Object} ComfyNode
   */
  #transceiverViewNode_f = null;

  /*
  * It is a sensible limitation that there can only be ONE ImageTransceiver node in a workflow,
  * and only ONE pict_cha_widget in that node. Anything else gets very complicated.
  */
  /**
   * @returns {ComfyNode}
   */
  get transceiverViewNode() {
    return this.#transceiverViewNode_f;
  }

  /**
   * @param {ComfyNode} tvn
   */
  set transceiverViewNode(tvn) {
    if (tvn == null) {
      throw new TypeError("Cannot set transceiverViewNode to null");
    }
    if (this.#transceiverViewNode_f != null) {
      throw new Error("Attempt to re-assign value to write-once property transceiverViewNode");
    }
    if (!Object.hasOwn(tvn, 'flags')) {
      console.debug("Supplied argument does not (yet?) have \"flags\" property.");
    }
    this.#transceiverViewNode_f = tvn;
  }


  /**
   * The visible HTMLImageElement that appears within the node.
   *  so transceiverImage_offScreen can be assigned.
   * @type {HTMLImageElement}
   * */
  transceiverImage = new Image();

  /**
   * An HTMLImageElement that can have its src changed, before being assigned to
   * @type {HTMLImageElement}
   */
  transceiverImage_offScreen = new Image();

  /**
   * When true, the image in the transceiver node needs to be re-rendered.
   * @type {boolean}
   */
  transceiverImage_isDirty = false;

  /**
   * @type {CanvasRenderingContext2D | null} Is supposed to be for the node.
   * fillRect works as expected, and the rectangles are drawn on the node area.
   * However, drawImage draws as if the coordinate system is the entire canvas.
   * That is why we must do all the rescaling and repositioning here, ourselves.
   */
  canvasRenderingContext2D = null;

  /**
   * @function onDrawForeground_orig
   */
  onDrawForeground_orig = null;

  /**
   * @function getCanvasMenuOptions_orig
   */
  getCanvasMenuOptions_orig = null;


  /**
   * Extracts the keys from an Object. Logs each key to the console as a side effect.
   * @param {Object|Array} obj
   * @returns An array of keys in the object
   */
  static getValues(obj) {
    let keys = [];
    for (let key in obj) {
      let value = obj[key];
      /**
       * Skip functions.
       */
      if (ImageTransceiverController.izf0(value)) {
        continue;
      }
      console.log(`key ${key}="${value}"`);
      console.log(value);
      keys.push(key);
    }
    return keys;
  };

  /**
   * Returns true if the value is a function.
   * @param {*} subject The value to examine
   * @returns True if the value is a function
   */
  static izf0(subject) {
    if (subject instanceof Function) {
      return true;
    }
    return false;
  };

  /**
   *
   * @param {string} text
   * @returns boolean
   */
  static izJSON(text) {
    if (typeof text !== "string") {
      return false;
    }
    try {
      JSON.parse(text);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   *
   * @param {number} container_width The width of the bounding container/frame/box or whatever.
   * @param {number} container_height The height of the bounding container/frame/box or whatever.
   * @param {number} image_width The width of the image to draw within the container.
   * @param {number} image_height height of the image to draw within the container.
   * @returns Two item array of the x_scale and the y_scale
   */
  static scaleForContainer(
    container_width,
    container_height,
    image_width,
    image_height
  ) {
    const square = Boolean(container_width == container_height);
    if (square) {
      return new Array(1, 1);
    }
    const portrait = Boolean(container_width < container_height);
    let x_scale = 1;
    let y_scale = 1;
    if (portrait) {
      x_scale = Math.min(container_width, container_height) / image_width;
      y_scale = x_scale;
    } else {
      y_scale = Math.min(container_width, container_height) / image_height;
      x_scale = y_scale;
    }
    return new Array(x_scale, y_scale);
  };

  /**
   * Prints the contents of a menu, recursively.
   * FIXME: Does not work, because the submenu property is always undefined, even when has_submenu is true.
   * @param {*} subject A CanvasMenuOption
   * @param {number} depth How far the function has already recursed.
   */
  static #walkMenu(subject, depth) {
    function stepper(value) {
      console.log(ImageTransceiverController.getValues(value).toString());
      //  FIXME: value.submenu is always undefined, even when has_submenu is true.
      if (value.submenu !== undefined) {
        let da_submenu = value.submenu;
        ImageTransceiverController.#walkMenu(da_submenu, deeper);
      }
      else {
        console.log(`value ${value} has no submenu: ${value.submenu}`);
      }
    };
    let deeper = depth + 1;
    console.log(`typeof subject=${typeof subject}`);
    console.log(`subject=${subject.toString()}`);
    let constructor_name = subject.constructor.name;
    console.log(`subject constructor=${constructor_name}`);
    let is_array = constructor_name == "Array";
    console.log(`is_array=${is_array};isArray()=${Array.isArray(subject)}`);
    if (is_array) {
      for (let value of subject) {
        stepper(value);
      }
    }
    else {
      if (typeof subject === "object") {
        for (let key in subject) {
          let value = subject[key];
          stepper(value);
        }
      }
      else {
        if (!ImageTransceiverController.izf0(subject)) {
          console.log(`${" ".repeat(depth * 2) + subject.toString()}`);
        }
      }
    }
  };

  /**
   * Send json back to the python mini-server socket, skipping the ComfyUI main server.
   *  Untested, and might never be used.
   * @param {object} json_data
   */
  static #send_to_py_transceiver(json_data) {
    // const dataToSend = JSON.stringify({ "email": "hey@mail.com", "password": "101010" });
    const dataToSend = JSON.stringify(json_data);
    let dataReceived = "";
    // see https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch
    fetch("http://localhost:8765", {
      credentials: "same-origin",
      mode: "same-origin",
      method: "post",
      headers: { "Content-Type": "application/json" },
      body: dataToSend,
    })
      .then((resp) => {
        if (resp.status === 200) {
          return resp.json();
        } else {
          console.log("Status: " + resp.status);
          return Promise.reject("server");
        }
      })
      .then((dataJson) => {
        dataReceived = JSON.parse(dataJson);
      })
      .catch((err) => {
        if (err === "server") return;
        console.log(err);
      });
    console.log(`Received: ${dataReceived}`);
  }

  initNodeImage() {
    // console.debug("initNodeImage()")
    /* This  section will run once, loading the "No Image" image ... */
    this.PNG_Data = ImageTransceiverController.SRC_DIAMOND_GREEN;
    const soiler = function () {
      // console.debug("initNodeImage(): Setting transceiverImage_isDirty")
      this.transceiverImage_isDirty = true;
    };
    this.transceiverImage.onload = soiler.bind(this);
    this.transceiverImage_isDirty = false; // Will be set true when loading is finished.
    this.transceiverImage.alt = "No Image image.";
    this.transceiverImage.src = ImageTransceiverController.SRC_DIAMOND_GREEN;
  }

  /**
   * Draws an image in the specified node.
   */
  drawInNode() {
    if (this.transceiverViewNode == null) {
      console.error("No transceiverViewNode instance. Returning.");
      return;
    }
    if (this.canvasRenderingContext2D == null) {
      console.error("No this.canvasRenderingContext2D instance. Returning.");
      return;
    }
    const SHRINKER = 0.93;
    const NODE_X_INSET = 10 * SHRINKER;
    const NODE_Y_INSET = 55 * SHRINKER;

    if (!Object.hasOwn(this.transceiverViewNode, "pos")) {
      throw new TypeError("transceiverViewNode has no pos property.");
      return;
    }
    const node_width = this.transceiverViewNode.size[0] - NODE_X_INSET;
    const node_height = this.transceiverViewNode.size[1] - NODE_Y_INSET;
    const miniframe_top_left_x = NODE_X_INSET;
    const miniframe_top_left_y = NODE_Y_INSET;

    this.canvasRenderingContext2D.save();
    const cft = ImageTransceiverController.scaleForContainer(
      node_height,
      node_width,
      this.transceiverImage.naturalWidth,
      this.transceiverImage.naturalHeight
    );
    const scaled_width = cft[0] * SHRINKER * this.transceiverImage.naturalWidth;
    const scaled_height = cft[1] * SHRINKER * this.transceiverImage.naturalHeight;
    this.canvasRenderingContext2D.drawImage(
      this.transceiverImage,
      miniframe_top_left_x,
      miniframe_top_left_y,
      scaled_width,
      scaled_height
    );
    this.canvasRenderingContext2D.restore();
  }

  /**
   * Draws an image in the canvas of the specified node, compensating for the LiteCanvas zoom and offsets.
   * @param {DOMHighResTimeStamp} _timestamp is a double and is used to store a time value in milliseconds.
   * We ignore the timestamp here.
   * See https://stackoverflow.com/questions/46197034/canvas-flickers-when-trying-to-draw-image-with-updated-src
   */
  renderTransceiverViewNode(_timestamp) {
    if (this.transceiverImage_isDirty) {  // only draw if needed
      this.transceiverImage_isDirty = false;
      this.drawInNode();
    }
    /*
     * Ugh, The method renderTransceiverViewNode becomes "unbound" from the ImageTransceiverController instance.
     * We use the "bind" method to force "this" within renderTransceiverViewNode's body to refer to the
     * IMAGE_TRANSCEIVER_CONTROLLER instance.
     */
    const reboundMethod = this.renderTransceiverViewNode.bind(this);
    requestAnimationFrame(reboundMethod);
  }

  /**
   * Called with a CanvasRenderingContext2D object to draw the node.
   * @param {CanvasRenderingContext2D} ctx
   * @returns the original callback
   */
  drawForeground(ctx) {
    // console.debug("drawForeground()")
    if (this.transceiverViewNode == null) {
      console.debug("this.transceiverViewNode == null");
      return;
    }
    this.canvasRenderingContext2D = ctx;
    /**
     * Use apply() first, then we can paint over it.
     */
    // @ts-ignore
    const r = this.onDrawForeground_orig?.apply(this.transceiverViewNode, arguments);
    if (Object.hasOwn(this.transceiverViewNode, 'flags')) {
      if (this.transceiverViewNode.flags.collapsed) {
        return r;
      }
    }
    else {
      console.warn("drawForeground(): No flags.");
    }
    this.drawInNode();
    return r;
  }

  /**
   * Either:
   * Creates a new HTMLImageElement with the img src attribute contained in the event details.
   * The new imageElement is then painted onto the imageTransceiver node canvas.
   * Or:
   * Processes a COMFYUI_CMD
   * @param {object} event
   */
  handleTransceiverMessage(event) {
    // console.warn("handleTransceiverMessage() ...");
    let message;
    const data_dict = event.detail;
    if (data_dict == null) {
      throw new Error("Missing data in event.detail");
    }
    for (const [payload_type, payload] of Object.entries(data_dict)) {
      switch (payload_type) {
        case ImageTransceiverController.PICT_CHA_KEY:
          this.PNG_Data = payload;
          const soiler = function () {
            // console.debug("handleTransceiverMessage: Setting transceiverImage_isDirty");
            this.transceiverImage_isDirty = true;
          };
          this.transceiverImage.onload = soiler.bind(this);
          this.transceiverImage_isDirty = false; // Will be set true when loading is finished.
          this.transceiverImage.alt = "From 3rd client";
          this.transceiverImage.src = this.PNG_Data;
          // message = `handleTransceiverMessage(): Assigned PNG_Data`;
          // console.debug(message);
          app.graph.setDirtyCanvas(true, true);
          break;
        case ImageTransceiverController.COMFYUI_CMD:
          this.handleControllerCommand(payload);
          break;
        default:
          message = `handleTransceiverMessage():Unsupported payload \"${payload_type}\" in event data.`;
          console.error(message);
      }
    }
  }

  /**
   * Process Controller commands.
   * @param {string} commandPayload
   */
  handleControllerCommand(commandPayload) {
    let message = `handleTransceiverMessage():Controller command \"${commandPayload}\"`;
    console.debug(message);
    /* TODO: Support command + args json */
    //  const itsJson = ImageTransceiverController.izJSON(commandPayload)
    const command_name = commandPayload;
    switch (command_name) {
      case ImageTransceiverController.ENQUEUE_PROMPT:
        try {
          /**
           * Its unclear what the 1st parameter is. 0 Is from the ComfyUI ui itself. 2nd parameter is
           * how many times current prompt should run. Note that some prompt values
           *  (seed, etc.) can auto-change. */
          app.queuePrompt(0, 1);
        }
        catch (errorArg) {
          console.error(errorArg);
        }
        break;
        case ImageTransceiverController.ABORT_WORKFLOW:
          /* TODO: Implement this. */
          Function.prototype();  // NO-OP
          break;
      default:
        console.error(`Unsupported Command ${command_name}`);
    }
  }
}

/**
 * Controller for browser view and python model.
 * @type {ImageTransceiverController}
 */
const IMAGE_TRANSCEIVER_CONTROLLER = new ImageTransceiverController();

/**
 * The basic structure of an extension follows is to import the main Comfy app object, and call
 * app.registerExtension, passing a dictionary that contains a unique name, and one or more functions to be called
 * by hooks in the Comfy code.
 */
app.registerExtension(
  {
    name: "image_transceiver_controller.extension",
    /**
     * Called once for each node type (the list of nodes available in the AddNode menu), and is used to modify the
     *  behaviour of the node.
     * @param {*} nodeType A template for all nodes that will be created of this type, so modifications
     *  made to nodeType.prototype will apply to all nodes of this type.
     * @param {*} nodeData  An encapsulation of aspects of the node defined in the Python code, such as its name,
     * category, inputs, and outputs.
     * @param {*} app A reference to the main Comfy app object
     */
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
      /*
       * Within each hijacker, the object "arguments" is magical. It is an array of all the values of
       *  the arguments originally passed to this function.
       */
      /*
       * Use the idiom of comparing nodeData.name to the class name of the custom node. Then the
       * frontend behavior for the node can be customized.
       */
      if (nodeData.name == "ImageTransceiver") {
        // console.debug("Configuring ImageTransceiver prototype.");
        IMAGE_TRANSCEIVER_CONTROLLER.onDrawForeground_orig = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (/** @type {CanvasRenderingContext2D} */ ctx) {
          /* Note: In this scope, "this" is now a ImageTransceiverNode instance. Go figure. */
          IMAGE_TRANSCEIVER_CONTROLLER.drawForeground(ctx);
        };
      }
    },
    /*
     * Called for EVERY instance of node the graph creates (right at the end of the ComfyNode() function on nodeType
     * which serves as a constructor). In this hook we can make modifications to individual instances of our node.
     * @param {ComfyNode} node
     */
    async nodeCreated(node) {
      if (node.comfyClass == "ImageTransceiver") {
        // console.debug("Configuring ImageTransceiver instance.");
        if (IMAGE_TRANSCEIVER_CONTROLLER.transceiverViewNode == null) {
          IMAGE_TRANSCEIVER_CONTROLLER.transceiverViewNode = node;
          IMAGE_TRANSCEIVER_CONTROLLER.initNodeImage();
        }
        else {
          console.error("IMAGE_TRANSCEIVER_CONTROLLER.transceiverViewNode previously set.");
        }
      }
    },
    /**
     * Called at the end of the startup process. A good place to add event listeners (either for Comfy events,
     *  or DOM events), or adding to the global menus, both of which are discussed elsewhere.
     */
    async setup() {
      /**
       * In the scope of setup(), "this" is a dict. It's only content is whatever is assigned in
       * app.registerExtension()
       */
      /* This  section will run once, loading the "No Image" image ... */
      // console.debug(`Adding handleTransceiverMessage to listen for \"${ImageTransceiverController.TRANSCEIVER_MSG_KEY}\" messages...`);
      api.addEventListener(
        ImageTransceiverController.TRANSCEIVER_MSG_KEY,
        IMAGE_TRANSCEIVER_CONTROLLER.handleTransceiverMessage.bind(IMAGE_TRANSCEIVER_CONTROLLER)
      );

      /**
       * This call "registers" renderTransceiverViewNode as the animation frame provider for this page. In this case,
       * the ComfyUI display. After requestAnimationFrame is invoked here, renderTransceiverViewNode will be frequently invoked,
       * presumably by another thread.
       * IMPORTANT: The method renderTransceiverViewNode becomes "unbound" from the IMAGE_TRANSCEIVER_CONTROLLER instance.
       * We use the "bind" method to force "this" within renderTransceiverViewNode's body to refer to the
       * IMAGE_TRANSCEIVER_CONTROLLER instance.
       *
       */
      requestAnimationFrame(IMAGE_TRANSCEIVER_CONTROLLER.renderTransceiverViewNode.bind(IMAGE_TRANSCEIVER_CONTROLLER));
    },
  }
);
