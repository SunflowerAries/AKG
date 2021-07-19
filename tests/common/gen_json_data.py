# Copyright 2020-2021 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""generate numpy data for composite json"""
import os
import tempfile
import json
import logging
import inspect
import numpy as np
from tests.common.gen_random import random_gaussian
from tests.common.test_utils import precheck


def get_attr(attr_desc, attr_type):
    """get op attr by type"""
    for attr in attr_desc:
        if attr["name"] == attr_type:
            return attr["value"]
    logging.warning("attr {} not found, please check.".format(attr_type))
    return None


class CodePrinter(object):
    """print numpy file"""

    def __init__(self, out_file):
        self.fout_ = open(out_file, 'w')
        self.indent_ = 0

    def __del__(self):
        self.fout_.close()

    def out(self, data, new_line=False):
        """write data"""
        if new_line:
            self.fout_.write("\n")
            for i in range(0, self.indent_):
                self.fout_.write('    ')
        if isinstance(data, str):
            self.fout_.write(data)
        else:
            self.fout_.write(str(data))

    def null_line(self):
        """add null line"""
        self.fout_.write("\n")

    def close(self):
        """close file"""
        self.fout_.close()


def get_input(desc):
    """get input values"""
    value = desc.get('value', None)
    return value if value is not None else desc['tensor_name']


def reduce_str(inputs, output, attr, op_type):
    """gen sum string"""
    axis = []
    keepdims = False
    axis_value = get_attr(attr, "axis")
    if axis_value:
        axis = list(axis_value) if isinstance(axis_value, (list, tuple)) else [axis_value]
    keepdims_value = get_attr(attr, "keep_dims")
    keepdims = keepdims_value if keepdims_value else keepdims

    if axis == []:
        s = "%s = np.%s(%s.astype(np.float32) if %s.dtype == np.float16 else %s, keepdims=%s).astype(%s.dtype)" % (
            output[0]['tensor_name'], op_type, get_input(inputs[0][0]), get_input(inputs[0][0]),
            get_input(inputs[0][0]), keepdims, get_input(inputs[0][0]))
    else:
        s = "%s = np.%s(%s.astype(np.float32) if %s.dtype == np.float16 else %s, axis=tuple(%s), keepdims=%s).astype(%s.dtype); %s = np.reshape(%s, %s) " %\
            (output[0]['tensor_name'], op_type, get_input(inputs[0][0]), get_input(inputs[0][0]),
             get_input(inputs[0][0]), axis, keepdims, get_input(inputs[0][0]),
             output[0]['tensor_name'], output[0]['tensor_name'], output[0]['shape'])
    return s


def cast_str(inputs, output, attr):
    """gen cast string"""
    dst_type = get_attr(attr, "dst_type")
    if inputs[0][0].get('value', None) is not None:
        s = "%s = np.array(%s).astype(np.%s)" % (output[0]['tensor_name'], get_input(inputs[0][0]), dst_type)
    else:
        s = "%s = %s.astype(np.%s)" % (output[0]['tensor_name'], get_input(inputs[0][0]), dst_type)
    return s


def broadcast_str(inputs, output, attr):
    """gen broadcast string"""
    dst_shape = get_attr(attr, "shape")
    s = "%s = np.broadcast_to(%s, %s)" % (
        output[0]["tensor_name"], get_input(inputs[0][0]), dst_shape)
    return s


def transpose_str(inputs, output, attr):
    """gen transpose string"""
    axes = None
    axes_value = get_attr(attr, "perm")
    axes = axes_value if axes_value else axes
    s = "%s = np.transpose(%s, axes=%s)" % (
        output[0]['tensor_name'], get_input(inputs[0][0]), axes)
    return s


def trans_data_two2fractal(input_, src_format, dst_format):
    shape = list(input_.shape)
    dtype = input_.dtype
    if src_format == "DefaultFormat" or src_format == "NCHW":
        m, n = shape[-2], shape[-1]
        m1, n1 = m // 16, n // 16
        m0, n0 = 16, 16
        needPad = m % 16 != 0 or n % 16 != 0
        if needPad:
            pad_m, pad_n = (m + 15) // 16 * 16, (n + 15) // 16 * 16
            pad_shape = [x for x in shape]
            pad_shape[-1] = pad_n
            pad_shape[-2] = pad_m
            pad_input = np.zeros(pad_shape).astype(dtype)
            if len(shape) == 2:
                pad_input[:m, :n] = input_
            elif len(shape) == 3:
                pad_input[:, :m, :n] = input_
            elif len(shape) == 4:
                pad_input[:, :, :m, :n] = input_
            m1, n1 = pad_m // 16, pad_n // 16
            reshape_shape = shape[:-2] + [m1, m0, n1, n0]
            reshape_input = pad_input.reshape(reshape_shape)
        else:
            reshape_shape = shape[:-2] + [m1, m0, n1, n0]
            reshape_input = input_.reshape(reshape_shape)
        if dst_format == "FRACTAL_NZ":
            transpose_axis = [2, 0, 1, 3]
        else:
            raise ValueError("dst_fromat %s is not suppored when src_format is %s" % (
                dst_format, src_format))
        transpose_axis = [x + len(shape) - 2 for x in transpose_axis]
        transpose_axis = [x for x in range(len(shape) - 2)] + transpose_axis
        bench_mark = reshape_input.transpose(transpose_axis)
        return bench_mark
    raise ValueError("src_format %s is not supported!" % src_format)


def trans_data_fractal2two(input_, src_format, dst_format, shape_origin):
    shape_origin = [int(_) for _ in shape_origin]
    shape = list(input_.shape)
    n1, m1, m0, n0 = shape[-4:]
    new_shape = shape[:-4] + [m1 * m0, n1 * n0]
    tranpose_axis = [1, 2, 0, 3]
    tranpose_axis = [x + len(shape) - 4 for x in tranpose_axis]
    tranpose_axis = [i for i in range(len(shape) - 4)] + tranpose_axis
    bench_mark = input_.transpose(tranpose_axis).reshape(new_shape)
    if new_shape != shape_origin:
        if len(shape_origin) == 2:
            bench_mark = bench_mark[:shape_origin[0], :shape_origin[1]]
        elif len(shape_origin) == 3:
            bench_mark = bench_mark[:, shape_origin[0], :shape_origin[1]]
        elif len(shape_origin) == 4:
            bench_mark = bench_mark[:, :, shape_origin[0], :shape_origin[1]]
    return bench_mark

def get_trans_data_str(input_name, output_name, ori_shape, src_format, dst_format):

    support_formats = [("DefaultFormat", "FRACTAL_NZ"),
                       ("NCHW", "FRACTAL_NZ"),
                       ("FRACTAL_NZ", "DefaultFormat"),
                       ("FRACTAL_NZ", "NCHW")]

    if (src_format, dst_format) not in support_formats:
        raise ValueError("src_format %s and dst_format %s is not supported!" %
                         (src_format, dst_format))

    if (src_format == 'DefaultFormat' or src_format == "NCHW") and dst_format == 'FRACTAL_NZ':
        res = "%s \n%s = %s(%s, '%s', '%s')" % (inspect.getsource(trans_data_two2fractal),
                                                output_name, trans_data_two2fractal.__name__, input_name,
                                                src_format, dst_format)
    elif src_format == 'FRACTAL_NZ' and (dst_format == 'DefaultFormat' or dst_format == "NCHW"):
        res = "%s \n%s = %s(%s, '%s', '%s', %s)" % (inspect.getsource(trans_data_fractal2two),
                                                    output_name, trans_data_fractal2two.__name__, input_name,
                                                    src_format, dst_format, ori_shape)
    else:
        raise ValueError("src_format(%s) and dst_format(%s) is not supported!" % (src_format, dst_format))
    return res

def trans_data_dsl(inputs, output, attr):
    src_format = get_attr(attr, "src_format")
    dst_format = get_attr(attr, "dst_format")
    ori_shape = output[0]['shape']
    input_name = get_input(inputs[0][0])
    output_name = output[0]['tensor_name']
    return get_trans_data_str(input_name, output_name, ori_shape, src_format, dst_format)


def np_matmul_str(inputs, output, attr):
    trans_a = get_attr(attr, "transpose_a")
    trans_b = get_attr(attr, "transpose_b")
    input_0 = inputs[0][0]
    input_1 = inputs[1][0]
    res = ""
    if input_0['data_type'] == "float16":
        tmp = "%s = %s.astype(np.float32)" % (get_input(input_0), get_input(input_0))
        res = res + tmp + "\n"
    if input_1['data_type'] == "float16":
        tmp = "%s = %s.astype(np.float32)" % (get_input(input_1), get_input(input_1))
        res = res + tmp + "\n"

    if trans_a and trans_b:
        res += "%s = np.dot(np.swapaxes(%s, -1, -2), np.swapaxes(%s, -1, -2))" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    elif trans_a:
        res += "%s = np.dot(np.swapaxes(%s, -1, -2), %s)" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    elif trans_b:
        res += "%s = np.dot(%s, np.swapaxes(%s, -1, -2))" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    else:
        res += "%s = np.dot(%s, %s)" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    if output[0]['data_type'] == "float16":
        res += "\n" + "%s = %s.astype(np.float16)" % (output[0]['tensor_name'], output[0]['tensor_name'])
    return res


def batchmatmul_str(inputs, output, attr):
    trans_a = get_attr(attr, "transpose_a")
    trans_b = get_attr(attr, "transpose_b")
    if trans_a and trans_b:
        res = "%s = np.matmul(np.swapaxes(%s, -1, -2), np.swapaxes(%s, -1, -2))" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    elif trans_a:
        res = "%s = np.matmul(np.swapaxes(%s, -1, -2), %s)" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    elif trans_b:
        res = "%s = np.matmul(%s, np.swapaxes(%s, -1, -2))" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    else:
        res = "%s = np.matmul(%s, %s)" %\
              (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]))
    return res

def convert_fracal_shape(ori_shape, fractal):
    ori_shape = tuple(ori_shape)
    if fractal == "zN":
        return ori_shape[:-4] + (ori_shape[-2] * ori_shape[-3], ori_shape[-1] * ori_shape[-4])
    if fractal == "zZ":
        return ori_shape[:-4] + (ori_shape[-4] * ori_shape[-2], ori_shape[-3] * ori_shape[-1])

def matmul_str(inputs, output, attr):

    left_format = get_attr(attr, "left_format")
    if left_format == None:
        left_format = get_attr(attr, "pri_format")
    right_format = get_attr(attr, "right_format")
    if right_format == None:
        right_format = get_attr(attr, "pri_format")
    trans_a = get_attr(attr, "transpose_a")
    trans_b = get_attr(attr, "transpose_b")
    left_input = inputs[0][0]
    right_input = inputs[1][0]
    output_name = output[0]['tensor_name']
    output_format = output[0]['format']
    output_shape = output[0]['shape']
    right_ori_shape = convert_fracal_shape(right_input['shape'], right_format)

    left_input_name = get_input(left_input)
    right_input_name = get_input(right_input)
    res = ''
    if left_format == 'FRACTAL_NZ':
        left_ori_shape = convert_fracal_shape(left_input['shape'], "zN")
        left_trans_str = get_trans_data_str(left_input_name, left_input_name, left_ori_shape, left_format, 'DefaultFormat')
        res = res + left_trans_str + "\n"
    if right_format == 'FRACTAL_NZ':
        right_ori_shape = convert_fracal_shape(right_input['shape'], "zN")
        right_trans_str = get_trans_data_str(right_input_name, right_input_name, right_ori_shape, right_format, 'DefaultFormat')
        res = res + right_trans_str + "\n"
    has_batch = (len(left_input['shape']) > 4)
    if has_batch:
        matmul_str = batchmatmul_str(inputs, output, attr)
    else:
        matmul_str = np_matmul_str(inputs, output, attr)
    res = res + matmul_str + "\n"

    has_bias = (len(inputs) > 2)
    if has_bias:
        bias=inputs[2][0]
        bias_shape = right_ori_shape[-2] if trans_b else right_ori_shape[-1]
        if bias['shape'][0] != bias_shape:
            res += "%s = random_gaussian([%s, ], miu=1, sigma=0.1).astype(np.%s) \n" % (get_input(bias), str(bias_shape), bias['data_type'])

        res += "%s = np.add(%s, %s)\n" % (output_name, output_name, get_input(bias))
    if output_format != 'DefaultFormat':
        output_trans_str = get_trans_data_str(output_name, output_name, output_shape, 'DefaultFormat', output_format)
        res = res + output_trans_str + "\n"
    func_name = "matmul_func"
    params = [get_input(i[0]) for i in inputs]
    func = func_pack(func_name, res, params, output_name)
    return func + "%s = %s(%s)\n" %(output_name, func_name, ','.join(params))

def func_pack(func_name, func_body, params, ret):
    lines = func_body.split('\n')
    body_lines = ['\t' + line for line in lines]
    func_header = 'def ' + func_name + '(' + ','.join(params) + '):\n'
    new_body = '\n'.join(body_lines) + '\n\treturn '+ ret + '\n'
    return func_header + new_body

op_dsl = {
    "ReduceSum": lambda inputs, output, attr: reduce_str(inputs, output, attr, "sum"),
    "ReduceMax": lambda inputs, output, attr: reduce_str(inputs, output, attr, "max"),
    "ReduceMin": lambda inputs, output, attr: reduce_str(inputs, output, attr, "min"),
    "Sin": lambda inputs, output, attr: "%s = np.sin(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Cos": lambda inputs, output, attr: "%s = np.cos(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Asin": lambda inputs, output, attr: "%s = np.arcsin(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "ACos": lambda inputs, output, attr: "%s = np.arccos(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Sign": lambda inputs, output, attr: "%s = np.sign(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "IsNan": lambda inputs, output, attr: "%s = np.isnan(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "IsInf": lambda inputs, output, attr: "%s = np.isinf(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "IsFinite": lambda inputs, output, attr: "%s = np.isfinite(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Tanh": lambda inputs, output, attr: "%s = np.tanh(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Mul": lambda inputs, output, attr: "%s = np.multiply(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Pow": lambda inputs, output, attr: "%s = np.power(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Sub": lambda inputs, output, attr: "%s = np.subtract(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "TensorAdd": lambda inputs, output, attr: "%s = np.add(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Add": lambda inputs, output, attr: "%s = np.add(%s, %s)" %
    (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Rsqrt": lambda inputs, output, attr: "%s = 1.0/np.sqrt(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Neg": lambda inputs, output, attr: "%s = np.negative(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Exp": lambda inputs, output, attr: "%s = np.exp(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "RealDiv": lambda inputs, output, attr: "%s = np.divide(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Minimum": lambda inputs, output, attr: "%s = np.minimum(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Maximum": lambda inputs, output, attr: "%s = np.maximum(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Log": lambda inputs, output, attr: "%s = np.log(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Sqrt": lambda inputs, output, attr: "%s = np.sqrt(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Cast": lambda inputs, output, attr: cast_str(inputs, output, attr),
    "Reshape": lambda inputs, output, attr: "%s = np.reshape(%s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), output[0]['shape']),
    "OneHot": lambda inputs, output, attr: "%s = np.one_hot(%s, %s, %s, %s, %s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]), get_input(inputs[2][0]),
        attr[0]['value'], attr[1]['value'], inputs[0][0]['data_type']),
    "ZerosLike": lambda inputs, output, attr: "%s = np.zeros_like(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "AddN": lambda inputs, output, attr: "%s = %s" %
        (output[0]['tensor_name'], ' + '.join([get_input(inputs[0][i])
                                           for i in range(0, len(inputs[0]))])),
    "Tile": lambda inputs, output, attr: "%s = np.tile(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_attr(attr, "multiples")),
    "Reciprocal": lambda inputs, output, attr: "%s = np.divide(1.0, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Equal": lambda inputs, output, attr: "%s = np.equal(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "GreaterEqual": lambda inputs, output, attr: "%s = np.greater_equal(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "Select": lambda inputs, output, attr: "%s = np.where(%s, %s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]),
        get_input(inputs[1][0]), get_input(inputs[2][0])),
    "InplaceAssign": lambda inputs, output, attr: "%s = %s; %s = %s" %
        (get_input(inputs[0][0]), get_input(inputs[1][0]),
        output[0]['tensor_name'], get_input(inputs[2][0])),
    "Greater": lambda inputs, output, attr: "%s = np.greater(%s, %s)" %
        (output[0]['tensor_name'], get_input(
        inputs[0][0]), get_input(inputs[1][0])),
    "SelectGT": lambda inputs, output, attr: "%s = np.where(%s > %s, %s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]),
        get_input(inputs[2][0]), get_input(inputs[3][0])),
    "SelectLT": lambda inputs, output, attr: "%s = np.where(%s < %s, %s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0]),
        get_input(inputs[2][0]), get_input(inputs[3][0])),
    "Abs": lambda inputs, output, attr: "%s = np.absolute(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "LessEqual": lambda inputs, output, attr: "%s = np.less_equal(%s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0])),
    "Less": lambda inputs, output, attr: "%s = np.less(%s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0])),
    "EquivFormat": lambda inputs, output, attr: "%s = %s" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "ExpandDims": lambda inputs, output, attr: "%s = np.expand_dims(%s, %s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), get_attr(attr, "axis")),
    "Transpose": lambda inputs, output, attr: transpose_str(inputs, output, attr),
    "TransData": trans_data_dsl,
    "BroadcastTo": lambda inputs, output, attr: broadcast_str(inputs, output, attr),
    "BatchMatMul": lambda inputs, output, attr: matmul_str(inputs, output, attr),
    "Assign": lambda inputs, output, attr: "%s = %s; %s = %s" %
        (get_input(inputs[0][0]), get_input(inputs[1][0]), output[0]['tensor_name'],
        get_input(inputs[1][0])),
    "MatMul": lambda inputs, output, attr: matmul_str(inputs, output, attr),
    "Conv2D": lambda inputs, output, attr: conv_2d_str(inputs, output, attr),
    "Asinh": lambda inputs, output, attr: "%s = np.arcsinh(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Acosh": lambda inputs, output, attr: "%s = np.arccosh(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
    "Atan2": lambda inputs, output, attr: "%s = np.arctan2(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0]), get_input(inputs[1][0])),
    "Expm1": lambda inputs, output, attr: "%s = np.expm1(%s)" %
        (output[0]['tensor_name'], get_input(inputs[0][0])),
}

def conv_2d_str(inputs, output, attr):
    support_list = {"float16": 'np.float16', "float32": 'np.float32'}
    shape_data = inputs[0][0]['shape']
    shape_data_name = inputs[0][0]['tensor_name']
    shape_filter = inputs[1][0]['shape']
    shape_filter_name = inputs[1][0]['tensor_name']
    dtype = inputs[0][0]['data_type']
    padding = get_attr(attr, "pad_list")
    has_pad = np.sum(padding) > 0
    stride = get_attr(attr, "stride")[2:]
    dilation = get_attr(attr, "dilation")[2:]
    out_dtype = output[0]["data_type"]
    output_name = output[0]["tensor_name"]

    res = ""
    res += "n, h, w, c = {} \n".format(shape_data)
    res += ("out_c, kh, kw, c = {}\n").format(shape_filter)
    res += ("s_h, s_w = {}\n").format(stride)
    res += ("d_h, d_w = {}\n").format(dilation)
    res += ("p_l, p_r, p_t, p_b = {}\n").format(padding)
    res += ("out_h = (h + p_t + p_b - kh) // s_h + 1\n")
    res += ("out_w = (w + p_l + p_r - kw) // s_w + 1\n")

    res += ("out_shape = (n, out_h, out_w, out_c)\n")
    res += ("shape_data_pad = (n, h + p_t + p_b, w + p_l + p_r, c)\n")

    res += ("data_pad = np.zeros(shape_data_pad).astype({})\n").format(support_list[dtype])
    if has_pad:
        res += ("data_pad[:, p_t:p_t+h, p_l:p_l+w, :] = {}\n".format(shape_data_name))
    else:
        res += ("data_pad = {}\n".format(shape_data_name))

    res += ("whd = (kh - 1) * d_h + 1\n")
    res += ("wwd = (kw - 1) * d_w + 1\n")
    res += ("{} = np.zeros(out_shape).astype({})\n").format(output_name, support_list[out_dtype])
    res += ("for i in range(out_h):\n")
    res += ("    for j in range(out_w):\n")
    res += ("        for f in range(out_c):\n")
    res += ("            {}[:, i, j, f] = np.sum(data_pad[:, i*s_h:i*s_h+whd:d_h, j*s_w:j*s_w+wwd:d_w, :].astype('float32') *{}[f, :, :, :].astype('float32'),axis=(1, 2, 3))\n".format(output_name, shape_filter_name))
    return res

def gen_json_data(op_desc, with_compute=True):
    """Generating test data for composite json"""
    desc = json.loads(op_desc)
    input_for_mod = []
    input_dict = {}
    input_order = {}
    output_indexes = []
    expect = []

    op_name = desc.get("op")
    if len(op_name.split("_")) > 0:
        op_hash = op_name.split("_")[-1]
    else:
        import time
        op_hash = str(time.time())

    uni_file_name_suffix = ".json_data_" + op_hash + ".py"
    fd, uni_file_name = tempfile.mkstemp(suffix=uni_file_name_suffix)
    os.close(fd)
    p = CodePrinter(uni_file_name)
    idx = 0

    # Collect input which should be processed by atomic clean.
    clean_input = []
    sum_out = None
    for op in desc["op_desc"]:
        if op["name"] == "ReduceSum":
            for a in op["attr"]:
                if a["name"] == "enable_atomic_add":
                    sum_out = op["output_desc"][0]["tensor_name"]
                    break
        elif op["name"] == "InplaceAssign":
            if not sum_out:
                continue
            if op["input_desc"][1][0]["tensor_name"] == sum_out:
                clean_input.append(op["input_desc"][0][0]["tensor_name"])

    input_mean_value = precheck(desc)
    for input_desc in desc["input_desc"] if desc["input_desc"] is not None else []:
        shape = [1] if not input_desc[0]["shape"] else input_desc[0]["shape"]
        dtype = input_desc[0]["data_type"]
        tensor_name = input_desc[0]["tensor_name"]
        if tensor_name in clean_input:
            item = np.zeros(shape).astype(dtype)
        else:
            item = random_gaussian(shape, miu=input_mean_value, sigma=0.1).astype(dtype)
        input_for_mod.append(item)
        input_order[tensor_name] = idx
        input_dict[tensor_name] = item
        p.out("%s = np.array(input_dict.get('%s'))" % (tensor_name, tensor_name),
            new_line=False if idx == 0 else True)
        idx += 1

    inplace_assign_write = []
    fake_output_tensors = []
    elemwise_op_list = ["TensorAdd", "Add", "RealDiv", "Mul", "Minimum", "Maximum", "Sub"]
    for op in desc["op_desc"]:
        dsl_fun = op_dsl.get(op["name"], None)
        if op["name"] in ("InplaceAssign", "Assign"):
            if op["name"] == "InplaceAssign":
                fake_output = False
                for attr in op["attr"]:
                    if attr["name"] == "fake_output":
                        fake_output = attr["value"]
                if fake_output:
                    fake_output_tensors.append(op["output_desc"][0]["tensor_name"])
            inplace_assign_write.append(op["input_desc"][0][0]["tensor_name"])
        elif op["name"] in elemwise_op_list and "format" in op["output_desc"][0]and \
             op["output_desc"][0]["format"] =="FRACTAL_NZ":
            need_reshape = False
            if op["input_desc"][0][0]["format"] == "DefaultFormat" and \
               op["input_desc"][1][0]["format"] == "FRACTAL_NZ":
                fractal_tensor = op["input_desc"][1][0]
                default_tensor = op["input_desc"][0][0]
                need_reshape = True
            elif op["input_desc"][0][0]["format"] == "FRACTAL_NZ" and \
                 op["input_desc"][1][0]["format"] == "DefaultFormat":
                fractal_tensor = op["input_desc"][0][0]
                default_tensor = op["input_desc"][1][0]
                need_reshape = True
            if need_reshape:
                shape_fractal = fractal_tensor["shape"]
                shape_default = default_tensor["shape"]
                orig_shape = shape_fractal[:-4] + [shape_fractal[-3] * shape_fractal[-2]] + [shape_fractal[-4] * shape_fractal[-1]]
                shape_tmp = []
                shape_new = []
                for i in range(len(shape_default) - 2):
                    shape_new.append(shape_default[i])
                for i in range(len(shape_default), 2):
                    shape_tmp.append(1)
                for i in range(len(shape_default)):
                    shape_tmp.append(shape_default[i])
                if shape_tmp[-2] == 1 and shape_tmp[-1] == 1:
                    shape_new.extend([1, 1, 1, 1])
                elif shape_tmp[-2] == 1 and shape_tmp[-1] == shape_default[-1]:
                    shape_new.extend([shape_fractal[-4], 1, 1, shape_fractal[-1]])
                elif shape_tmp[-2] == shape_default[-2] and shape_tmp[-1] == 1:
                    shape_new.extend([1, shape_fractal[-3], shape_fractal[-2], 1])
                if "value" in default_tensor:
                    sent_reshape_tensor = "%s = np.full(%s, %s, np.%s)" \
                        % (default_tensor["tensor_name"], shape_new, default_tensor["value"],
                           default_tensor["data_type"])
                else:
                    if np.zeros(shape_default).size != np.zeros(shape_new).size:
                        raise ValueError("It is error to reshape %s to %s!" % (shape_default, shape_new))
                    sent_reshape_tensor = "%s = np.reshape(%s, %s)" \
                        % (default_tensor["tensor_name"], default_tensor["tensor_name"], tuple(shape_new))
                p.out(sent_reshape_tensor, True)
        if dsl_fun is None:
            logging.info("[%s] is not support for %s", op["name"], op)
            continue
        sent = dsl_fun(op['input_desc'], op['output_desc'], op['attr'])
        logging.debug(sent)
        p.out(sent, True)

    idx = 0
    out_nums = len(desc["output_desc"])
    for output_desc in desc["output_desc"]:
        shape = [1] if not output_desc["shape"] else output_desc["shape"]
        dtype = output_desc["data_type"]
        item = np.full(shape, np.nan, dtype)
        input_for_mod.append(item)
        tensor_name = output_desc["tensor_name"]
        if tensor_name not in fake_output_tensors:
            real_idx = idx - out_nums
            output_indexes.append(real_idx)
            p.out("expect.append(%s)" % (tensor_name), True)
        idx += 1

    # Add inplace tensors to expect, and add their index to output_indexes.
    if inplace_assign_write:
        inplace_tensors = "["
        inplace_tensors_index = []

        for tensor_name in inplace_assign_write:
            inplace_tensors_index.append(input_order[tensor_name])
            inplace_tensors += "{}, ".format(tensor_name)
        inplace_tensors += "]"

        p.out("inplace_tensors = {}".format(inplace_tensors), True)
        p.out("expect.extend(inplace_tensors)", True)
        output_indexes.extend(inplace_tensors_index)

    p.close()
    # compute the expect data
    if with_compute:
        with open(uni_file_name, 'r') as f:
            sent = f.read()
        exec(sent)
        os.remove(uni_file_name)
        return input_for_mod, expect, output_indexes
    else:
        return input_for_mod, None, output_indexes

