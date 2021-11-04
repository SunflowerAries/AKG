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

#ifndef AKG_SRC_COMPOSITE_LOWER_TREE_TUNE_NODE_H_
#define AKG_SRC_COMPOSITE_LOWER_TREE_TUNE_NODE_H_
#include <sstream>
#include <vector>
#include <pass/utils.h>
#include "build_module.h"
#include "codegen/lower.h"
#include "codegen/pass_mgr.h"
#include "codegen/stage_lower.h"
#include "composite/utils/dump.h"
#include "composite/utils/util.h"
#include "pass/recover_tot.h"
#include "pass/replace_tot.h"
#include "composite/lower_tree/base_node.h"

namespace akg {
namespace lower {
constexpr auto kTune = "Tune";
constexpr auto kGetStmt = "get_stmt";
class TuneLowerNode : public BaseLowerNode {
 public:
  TuneLowerNode(const std::string &target, bool get_stmt) : BaseLowerNode(target) {
    if (target == "cuda" || target == "llvm") {
      entrance_stage_ = get_stmt ? StageType::BeforeLowerFunc : StageType::End;
    } else if (target == "cce") {
      entrance_stage_ = get_stmt ? StageType::MultiCore : StageType::End;
    } else {
      entrance_stage_ = StageType::End;
    }

    name_ = __FUNCTION__;
  }
  ~TuneLowerNode() override = default;

  void ExcuteImpl(StageType stage) override;

 private:
  bool get_stmt_{false};
};
}  // namespace lower
}  // namespace akg
#endif  // AKG_SRC_COMPOSITE_LOWER_TREE_TUNE_NODE_H_
