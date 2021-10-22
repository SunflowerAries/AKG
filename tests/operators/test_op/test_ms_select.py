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
# limitations under the License
import numpy as np
import akg
from tests.common.gen_random import random_gaussian
from akg.utils import kernel_exec as utils
from akg.utils.result_analysis import target_profiling
from akg.utils.format_transform import to_tvm_nd_array
from tests.common.tensorio import compare_tensor
from akg.ops.math_gpu.select import select

def gen_data(shape_cond, shape_x, dtype_cond, dtype_x):
    support_list = {"float16": np.float16, "float32": np.float32, "int32": np.int32, "int8": np.int8}
    cond = np.random.randint(0, 2, shape_cond).astype(support_list[dtype_cond])
    x1 = random_gaussian(shape_x, miu=1, sigma=0.1).astype(support_list[dtype_x])
    x2 = random_gaussian(shape_x, miu=1, sigma=0.1).astype(support_list[dtype_x])
    expect = np.where(cond, x1, x2)
    output = np.full(shape_x, np.nan, dtype_x)
    return expect, cond, x1, x2, output


def test_ms_select(shape_cond, shape_x, dtype_cond, dtype_x, poly_sch=True, attrs=None):
    if not attrs:
        attrs = {"target": "cuda"}
    mod = utils.op_build_test(select, [shape_cond, shape_x, shape_x], [dtype_cond, dtype_x, dtype_x],
                        kernel_name="select", polyhedral=poly_sch, attrs=attrs)

    expect, cond, x1, x2, output = gen_data(shape_cond, shape_x, dtype_cond, dtype_x)
    output = utils.mod_launch(mod, (cond, x1, x2, output), expect=expect)
    res = compare_tensor(output, expect, rtol=5e-03, atol=1.e-8)
    print("Test {}".format("Pass" if res else "Fail"))
    target_name = attrs["target"].split()[0]
    if not res:
        mod_source = mod
        if target_name != "llvm":
            mod_source = mod.imported_modules[0]
        print("Error {}:========================".format(target_name))
        print(mod_source.get_source())
        raise AssertionError("Test fail")

    if attrs["profiling"]:
        cond, x1, x2, output = to_tvm_nd_array([cond, x1, x2, output], akg.tvm.context(target_name, 0))
        target_profiling(mod, cond, x1, x2, output, target=target_name, repeat_time=attrs["repeat_time"])