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
from akg.ops.math_gpu.equal import equal

def gen_data(shapes, dtype):
    support_list = {"float16": np.float16, "float32": np.float32}
    inputs = []
    for i in range(len(shapes)):
        shape = shapes[i]
        one_input = random_gaussian(shape, miu=1, sigma=0.1).astype(support_list[dtype])
        inputs.append(one_input)

    if len(inputs) != 2:
        raise RuntimeError("inputs num should be 2")
    expect = np.equal(inputs[0], inputs[1])
    output = np.full(expect.shape, 0, bool)
    return inputs, output, expect

def test_ms_equal(shapes, dtype, poly_sch=True, attrs=None):
    if not attrs:
        attrs = {"target": "cuda"}
    mod = utils.op_build_test(equal, shapes, [dtype, dtype], kernel_name="equal", polyhedral=poly_sch, attrs=attrs)

    inputs1, output1, expect1 = gen_data(shapes, dtype)
    output1 = utils.mod_launch(mod, (*inputs1, output1), expect=expect1)

    if shapes[0] == shapes[1]:
        inputs2 = []
        inputs2.append(inputs1[0])
        inputs2.append(inputs1[0])
        expect2 = np.equal(inputs2[0], inputs2[1])
        output2 = np.full(expect2.shape, 0, bool)
        output2 = utils.mod_launch(mod, (*inputs2, output2), expect=expect1)

        res = np.allclose(output1, expect1, rtol=5e-03, atol=1.e-8) and np.allclose(output2, expect2, rtol=5e-03, atol=1.e-8)
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
            inputs1 = to_tvm_nd_array(inputs1, akg.tvm.context(target_name, 0))
            inputs2 = to_tvm_nd_array(inputs2, akg.tvm.context(target_name, 0))
            expect1 = to_tvm_nd_array(expect1, akg.tvm.context(target_name, 0))
            expect2 = to_tvm_nd_array(expect2, akg.tvm.context(target_name, 0))
            target_profiling(mod, *inputs1, expect1, *inputs2, expect2, target=target_name, repeat_time=attrs["repeat_time"])
    else:
        res = np.allclose(output1, expect1, rtol=5e-03, atol=1.e-8)
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
            args_list = to_tvm_nd_array([inputs1, output1], akg.tvm.context(target_name, 0))
            target_profiling(mod, *args_list, target=target_name, repeat_time=attrs["repeat_time"])
