# Copyright 2019 Huawei Technologies Co., Ltd
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

"""
tf_transpose
"""
import os
import pytest
from tests.common.base import TestBase
from tests.common.test_run.gather_run import gather_run


class TestCase(TestBase):

    def setup(self):
        case_name = "test_akg_gather_001"
        case_path = os.getcwd()
        self.params_init(case_name, case_path)
        self.caseresult = True
        self._log.info("============= {0} Setup case============".format(self.casename))
        self.testarg = [
            #caseflag,opfuncname,testRunArgs, dimArgs
            ("gather_001", gather_run, ((30522, 1024), (8192,), "float16", "int32", 0)),
            ("gather_002", gather_run, ((8192, 1024), (1280,), "float16", "int32", 0)),
        ]
        self.testarg_level1 = [
            #caseflag,opfuncname,testRunArgs, dimArgs
            ("gather_101", gather_run, ((30522, 1024), (32768,), "float16", "int32", 0)),
            ("gather_102", gather_run, ((32768, 1024), (4928,), "float16", "int32", 0)),
        ]
        return

    @pytest.mark.level0
    @pytest.mark.platform_arm_ascend_training
    @pytest.mark.platform_x86_ascend_training
    @pytest.mark.env_onecard
    def test_run(self):
        self.common_run(self.testarg)

    @pytest.mark.level1
    @pytest.mark.platform_arm_ascend_training
    @pytest.mark.platform_x86_ascend_training
    @pytest.mark.env_onecard
    def test_run_level1(self):
        self.common_run(self.testarg_level1)

    def teardown(self):
        """
        clean environment
        :return:
        """
        self._log.info("============= {0} Teardown============".format(self.casename))
        return