/**
 * Copyright 2019 Huawei Technologies Co., Ltd
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

#ifndef POLY_SPACE_ANALYZER_H_
#define POLY_SPACE_ANALYZER_H_

#include <tvm/ir.h>

#include <vector>
#include <deque>
#include <string>
#include <unordered_map>
#include <unordered_set>

#include "poly/scop_builder.h"
#include "poly/tiling/tiling_analyzer.h"
#include "poly/tiling/custom_tiling.h"

namespace akg {
namespace ir {
namespace poly {
class SpaceAnalyzer {
 public:
  explicit SpaceAnalyzer(TilingAnalyzer *analyzer) : analyzer_(analyzer) {}
  ~SpaceAnalyzer() {}

  void AnalyzeSpecialAxes();

 private:
  TilingAnalyzer *analyzer_{nullptr};
  // Provides stmt after analysis.
  std::unordered_map<const For *, std::vector<ProvideEntry>> provides_ana_;

  // generalized cases
  void IdentifyInsnType();
  void IdentifyDmaUnderCondition();
  void IdentifySharedAxes() const;
  void IdentifyVectorizedAxes();
  void IdentifyAlignAxes();
  void IdentifyReduceAxes();
  void IdentifyCastAxes();
  void IdentifyModAxes();
  void IdentifyPostFusionReduceTensors();

  // customized cases
  void IdentifyDynamicShape();
  void IdentifyCustomTiling();

  // utils
  void MarkInnerMostAxis(std::vector<TensorEntry> tensors, const std::string &attr_key);
  void MarkGemmAxes(const ProvideEntry &pe);
  void MarkBroadcastAxes(const ProvideEntry &pe);
  std::vector<Expr> FindModConstraint(const Expr &arg, std::vector<Expr> constraints);
  const For *GetBufferInnerAxis(TensorEntry t, int offset = 1);
  void SetAttrForAxis(int tile_band, int tile_axis, const std::string &attr_key, const std::string &attr_value);
  void SetAttrForTensor(const std::string &tensor_name, int pos, const std::string &attr_key,
                        const std::string &attr_value);
  std::string ParseAllTypeExpr(const Expr constraint);
  std::string ParseArrayExpr(const Array<Expr> constraint);
};
}  // namespace poly
}  // namespace ir
}  // namespace akg

#endif  // POLY_SPACE_ANALYZER_H_
