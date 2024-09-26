#  Copyright (c) 2023. Charles Hymes
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
#
import logging
import numbers
from typing import Any, List

ALL_NUMERIC_LIST_MSG = "List is all numeric."


def as_strings_deeply(data: Any):
    """Recursively converts dictionary keys to strings."""
    if isinstance(data, str):
        return str(data)
    if not isinstance(data, dict):
        return data
    return dict((str(k), as_strings_deeply(v))
                for k, v in data.items())


def bool_of(string: str, include_digits=False) -> bool:
    """
    Strings consisting of or containing digits will raise type errors unless include_digits is true.
    Strings of floats will raise type errors. ints other than 1 ot 0 will raise type errors.
    :param string:
    :param include_digits: If true "0" and "1" will be parsed as booleans.
    :return:
    """
    if string.lower() in ['true', 't', 'y', 'yes', 'enable', 'enabled', 'yeah', 'yup', 'certainly', 'uh-huh']:
        return True
    if string.lower() in ['false', 'f', 'n', 'no', 'disable', 'disabled', 'nope', 'nah', 'no-way', 'nuh-uh']:
        return False
    if include_digits:
        if string.lower() == '1':
            return True
        if string.lower() == '0':
            return False
    raise TypeError("Could not interpret \"%s\" as bool" % string)


def bool_safe_of(string: str) -> bool:
    try:
        if string is not None and (string.strip() != ""):
            return bool_of(string)
        return False
    except (KeyError, ValueError):
        return False


def is_numerical(thing) -> bool:
    if isinstance(thing, numbers.Number):
        return True
    if isinstance(thing, str):
        if thing.isnumeric():
            return True
        try:
            as_float: float = float(thing)  # noqa
            return True
        except:  # noqa
            pass
    try:
        as_bool: bool = bool_of(thing)  # noqa
        return True
    except:  # noqa
        pass
    return False


def is_all_numeric_list(some_list: List) -> bool:
    for item in some_list:
        if not is_numerical(item):
            return False
    return True


def is_all_nonnumerical_strings(some_list: List) -> bool:
    """
    Opens strs found as items of some_list, returns False if any of them can be parsed as numerical
    :param some_list: the list to evaluate.
    :return: True if all items are of type str, and none of the contents of each str are numerical.
    """
    for item in some_list:
        if not isinstance(item, str):
            return False
        if is_numerical(item):
            return False
    return True


def is_homogenous_list(some_list: List) -> bool:
    f_type: type = type(some_list[0])
    for item in some_list:
        if not isinstance(item, f_type):
            return False
    return True


def types_in(some_list: List) -> List[type]:
    return [type(item) for item in some_list]


def type_in(item_type: type, some_list: List) -> bool:
    return item_type in some_list


def float_of(datum) -> float:
    """This function will be enhanced to be more robust than standard float()"""
    if not is_numerical(datum):
        raise TypeError("Cannot convert \"%s\" into number." % str(datum))
    return float(datum)


def float_or_str(datum: str) -> float | str:
    subject = datum.strip()
    if not is_numerical(subject):
        return datum
    try:
        return float(subject)
    except Exception as excpt:
        logging.exception(excpt)
        raise excpt


def int_or_str(datum: str) -> int | str:
    subject = datum.strip()
    if not is_numerical(subject):
        return datum
    try:
        return int(subject)
    except Exception as excpt:
        logging.exception(excpt)
        raise excpt


def attempt_parse(datum) -> Any:
    # So far, all node JSON is dicts, lists, and strings. Numbers and bools are often, but not allways, wrapped as strs
    if isinstance(datum, dict):
        raise NotImplementedError("dict types are not currently supported.")
    if isinstance(datum, list):
        data: List = datum
        if len(data) < 2:
            raise ValueError("List is Empty or singleton.")
        if is_all_numeric_list(some_list=data):
            raise TypeError(ALL_NUMERIC_LIST_MSG)
        if is_all_nonnumerical_strings(some_list=data):
            return data
        if is_homogenous_list(some_list=data):
            return data
        else:
            raise TypeError("Heterogeneous List")

    if isinstance(datum, str):
        if is_numerical(datum):
            return float.__name__
        try:
            bool_of(datum)  # noqa
            return bool.__name__
        except:  # noqa
            pass
        return str.__name__
    if is_numerical(datum):
        return float.__name__
    datum_type = type(datum)
    datum_type_name = datum_type.__name__
    message = "Unsupported data type %s" % datum_type_name
    raise NotImplementedError(message)


def round_to_multiple(value, multiple):
    return multiple * round(float(value) / multiple)
