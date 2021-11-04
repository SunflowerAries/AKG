/**
 * Copyright 2021 Huawei Technologies Co., Ltd
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#ifndef COMPOSITE_OPTIMIZE_COMPLEX_EXPANDER_H_
#define COMPOSITE_OPTIMIZE_COMPLEX_EXPANDER_H_
#include "composite/optimize/optimize.h"

namespace akg {
class ComplexExpander : public CompositeOptPass {
 public:
  ComplexExpander() { pass_name_ = __FUNCTION__; }
  ~ComplexExpander() = default;
  Stmt Run(const Stmt &s) override;
};
}  // namespace akg
#endif  // COMPOSITE_OPTIMIZE_COMPLEX_EXPANDER_H__
