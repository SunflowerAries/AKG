/**
 * Copyright 2020-2021 Huawei Technologies Co., Ltd
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

#include "poly/schedule_pass/reschedule.h"
#include "poly/schedule_tree_util.h"
#include "poly/schedule_pass.h"
#include "reduce_manager.h"

namespace akg {
namespace ir {
namespace poly {

isl::schedule ReduceManager::DetectAndMarkReduce(const isl::schedule &sch) {
  auto final_schedule = sch;

  auto all_reduce_map = scop_info_.analysis_result_.GetReduceTensorInfoMap();
  bool done_separate = false;
  auto GetInnerMostBand = [&done_separate, &all_reduce_map, this](isl::schedule_node node) -> isl::schedule_node {
    if (done_separate) {
      return node;
    }
    auto band_node = node.as<isl::schedule_node_band>();
    if (!band_node || !band_node.permutable()) {
      return node;
    }

    isl::union_set reduce_statements = GetCurrentNodeReduceStatements(node, all_reduce_map);
    if (reduce_statements.n_set() < 1) {
      return node;
    }

    isl::union_map dependences = pass_info_.dependences_;
    if (!pass_info_.force_dependences_.is_null()) {
      dependences = dependences.subtract(pass_info_.force_dependences_);
    }

    auto node_bak = node;
    if (!SplitReduceStatements(node, reduce_statements, dependences)) {
      return node_bak;
    }
    done_separate = all_reduce_map.empty();
    return node;
  };
  final_schedule = sch.get_root().map_descendant_bottom_up(GetInnerMostBand).get_schedule();
  if (done_separate) {
    final_schedule = InsertReduceMarker(final_schedule);
    final_schedule = RescheduleForReduce(final_schedule);
  }
  return final_schedule;
}

isl::schedule ReduceManager::InsertReduceMarker(const isl::schedule &sch) {
  isl::schedule final_schedule = sch;
  auto all_reduce_map = scop_info_.analysis_result_.GetReduceTensorInfoMap();
  auto InsertMarker = [&all_reduce_map, this](isl::schedule_node node) -> isl::schedule_node {
    auto band_node = node.as<isl::schedule_node_band>();
    if (!band_node) {
      return node;
    }

    for (auto it = all_reduce_map.begin(); it != all_reduce_map.end();) {
      isl::union_map reduce_statement_map = it->second.stmt_map;
      isl::id reduce_id = it->first;
      auto band_node_domain = band_node.get_partial_schedule().domain();
      auto op_type = scop_info_.analysis_result_.GetReduceOpType(reduce_id) + "_";

      StatementMap all_statements = scop_info_.analysis_result_.GetStatementMap();
      isl::union_set reduce_statements = GetReduceStatements(band_node_domain, reduce_statement_map, all_statements);
      if (reduce_statements.n_set() != 1) {
        ++it;
        continue;
      }

      all_reduce_map.erase(it++);
      std::string reduce_marker_name =
        REDUCE_MARKER + op_type + reduce_id.get_name() + "_" + std::to_string(GetReduceId());
      auto reduce_node = band_node.insert_mark(reduce_marker_name);
      return reduce_node;
    }
    return band_node;
  };
  final_schedule = final_schedule.get_root().map_descendant_bottom_up(InsertMarker).get_schedule();
  return final_schedule;
}

isl::schedule ReduceManager::RescheduleForReduce(const isl::schedule &sch) {
  auto IsContainCoincidentZero = [](const isl::schedule_node node) -> bool {
    if (!node.isa<isl::schedule_node_band>()) {
      return true;
    }

    auto band_node = node.as<isl::schedule_node_band>();
    for (int i = 0; i < static_cast<int>(band_node.n_member()); ++i) {
      if (band_node.member_get_coincident(i) == 0) {
        return true;
      }
    }
    return false;
  };

  auto SetAllCoincident = [](const isl::schedule_node node) -> isl::schedule_node {
    if (!node.isa<isl::schedule_node_band>()) {
      return node;
    }

    auto band_node = node.as<isl::schedule_node_band>();
    for (int i = 0; i < static_cast<int>(band_node.n_member()); ++i) {
      if (band_node.member_get_coincident(i) == 0) {
        band_node = band_node.member_set_coincident(i, 1);
      }
    }
    return band_node;
  };

  auto root = sch.get_root();
  auto node = root;
  root.foreach_descendant_top_down([&node](const isl::schedule_node &orig_node) -> bool {
    if (!GetMarkerName(orig_node, REDUCE_MARKER).empty() && orig_node.tree_depth() >= 2 &&
        orig_node.ancestor(2).isa<isl::schedule_node_sequence>()) {
      node = orig_node.ancestor(2);
      return false;
    }
    return true;
  });
  if (node.is_equal(root)) {
    return sch;
  }

  int child_number = static_cast<int>(node.n_children());
  Reschedule reschedule(scop_info_, pass_info_);
  for (int i = 0; i < child_number; ++i) {
    auto child_node = node.child(i);
    if (!child_node.isa<isl::schedule_node_filter>() || !child_node.has_children()) {
      continue;
    }

    // Ignore the related statements of the reduce operator.
    if (!GetMarkerName(child_node.child(0), REDUCE_MARKER).empty()) {
      continue;
    }

    // Ignore all related statements that coincide with 1.
    if (!IsContainCoincidentZero(child_node.child(0))) {
      continue;
    }

    auto active_domain = child_node.as<isl::schedule_node_filter>().get_filter();
    auto after_reschedule_node = reschedule.RescheduleSerializeSccs(active_domain, false).get_root();
    after_reschedule_node =
      after_reschedule_node.has_children() ? after_reschedule_node.child(0) : after_reschedule_node;

    // Adjust the coincident of the original schedule tree according to the result of the reschedule.
    bool is_seq =
      after_reschedule_node.isa<isl::schedule_node_sequence>() || after_reschedule_node.isa<isl::schedule_node_set>();
    if (!is_seq) {
      bool is_contain_coincient_zero = IsContainCoincidentZero(after_reschedule_node);
      node = is_contain_coincient_zero ? node : SetAllCoincident(child_node.child(0)).ancestor(2);
    } else {
      int j = 0;
      int reschedule_child_number = static_cast<int>(after_reschedule_node.n_children());
      for (; j < reschedule_child_number; ++j) {
        auto reschedule_child_node = after_reschedule_node.child(j);
        if (!reschedule_child_node.has_children() || IsContainCoincidentZero(reschedule_child_node.child(0))) {
          break;
        }
      }
      node = (j != reschedule_child_number) ? node : SetAllCoincident(child_node.child(0)).ancestor(2);
    }
  }
  return node.get_schedule();
}

size_t ReduceManager::GetReduceId() const {
  static size_t reduce_count = 0;
  return reduce_count++;
}

isl::union_set ReduceManager::GetCurrentNodeReduceStatements(const isl::schedule_node node,
                                                             ReduceTensorInfoMap &all_reduce_map,
                                                             const bool need_delete_reduce) {
  isl::union_set reduce_statements = isl::union_set::empty(node.ctx());
  if (!node.isa<isl::schedule_node_band>()) {
    return reduce_statements;
  }
  auto band_node_domain = node.as<isl::schedule_node_band>().get_partial_schedule().domain();
  StatementMap all_statements = scop_info_.analysis_result_.GetStatementMap();
  isl::union_map reduce_statement_map = isl::union_map::empty(node.ctx());

  for (auto it = all_reduce_map.begin(); it != all_reduce_map.end();) {
    reduce_statement_map = reduce_statement_map.unite(it->second.stmt_map);
    auto this_reduce = GetReduceStatements(band_node_domain, reduce_statement_map, all_statements);
    if (!this_reduce.is_empty()) {
      reduce_statements = reduce_statements.unite(this_reduce);
      it = need_delete_reduce ? all_reduce_map.erase(it) : ++it;
    } else {
      ++it;
    }
  }
  return reduce_statements;
}

isl::union_set ReduceManager::GetReduceStatements(isl::union_set domain, isl::union_map reduce_statement_map,
                                                  StatementMap all_statements) {
  isl::union_set reduce_domain = reduce_statement_map.intersect_domain(domain).domain();
  isl::union_set reduce_statements = isl::union_set::empty(reduce_domain.get_space());
  reduce_domain.foreach_set([&reduce_statements, all_statements](isl::set set) {
    isl::id id = set.get_tuple_id();

    CHECK_EQ(all_statements.count(id), 1u) << "setId is not a statement in scop" << id;
    const Node *stmt_node = all_statements.at(id);

    if (stmt_node != nullptr && stmt_node->IsInstance<Provide>()) {
      const auto provide = static_cast<const Provide *>(stmt_node);
      if (provide->value.defined()) {
        reduce_statements = reduce_statements.unite(set);
      }
    }
  });
  return reduce_statements;
}

// Determine whether the first statement can be ranked before the second statement
bool ReduceManager::AreSequentialStatements(isl::union_set first_statements, isl::union_set second_statements,
                                            isl::union_map dependences) {
  if (first_statements.is_empty() || second_statements.is_empty()) {
    return true;
  }
  isl::ctx ctx = dependences.ctx();
  isl::space space = isl::space(ctx, 0).add_unnamed_tuple_ui(1);
  isl::multi_val zero_first = isl::multi_val::zero(space);
  isl::multi_val one_second = zero_first.set_val(0, isl::val::one(ctx));
  auto order_statements = isl::multi_union_pw_aff(first_statements, zero_first);
  order_statements = order_statements.union_add(isl::multi_union_pw_aff(second_statements, one_second));

  auto order_dependences = dependences.lex_lt_at(order_statements).unite(dependences.eq_at(order_statements));
  return dependences.is_subset(order_dependences);
}

isl::schedule_node ReduceManager::ReorderStatements(const isl::schedule_node &node, isl::union_set before,
                                                    isl::union_set after) {
  isl::union_set middle = CollectDomain(node);
  isl::schedule_node order_node = node;
  isl::union_set_list filter_list;
  size_t depth = (before.is_empty() && !after.is_empty()) ? 0 : 1;
  auto AddMiddleToFilterList = [this, &filter_list, &middle]() -> void {
    if (need_split_reduce_) {
      middle.foreach_set([this, &filter_list](const isl::set &s) -> void {
        isl::union_set_list first_uset = isl::union_set_list(isl::union_set(s));
        filter_list = filter_list.is_null() ? first_uset : filter_list.add(isl::union_set(s));
      });
    } else {
      filter_list = filter_list.add(middle);
    }
  };

  if (!before.is_empty() && after.is_empty()) {
    middle = middle.subtract(before);
    filter_list = isl::union_set_list(before);
    AddMiddleToFilterList();
  } else if (before.is_empty() && !after.is_empty()) {
    middle = middle.subtract(after);
    AddMiddleToFilterList();
    filter_list = filter_list.add(after);
  } else if (!before.is_empty() && !after.is_empty()) {
    middle = middle.subtract(before).subtract(after);
    filter_list = isl::union_set_list(before);
    AddMiddleToFilterList();
    filter_list = filter_list.add(after);
  } else {
    AddMiddleToFilterList();
  }

  if (filter_list.size() == 1) {
    order_node = order_node.insert_filter(filter_list.at(0));
    return order_node;
  }
  order_node = order_node.insert_sequence(filter_list);
  order_node = order_node.insert_mark(INSERT_SYNC);
  order_node = order_node.child(0).child(depth);

  return order_node;
}

// Separate the reduce statement from other statements
bool ReduceManager::SplitReduceStatements(isl::schedule_node &node, isl::union_set reduce_statements,
                                          isl::union_map dependences) {
  auto domain = CollectDomain(node);
  auto injective_statements = domain.subtract(reduce_statements);
  if (injective_statements.is_empty()) {
    return true;
  }

  auto prefix = ShortScheduleMupaImpl(node.root(), node.root(), node.parent());
  isl::union_map active_dependences = dependences.intersect_domain(domain).intersect_range(domain).eq_at(prefix);

  isl::union_set reduction_dependent_stmt =
    active_dependences.intersect_domain(reduce_statements).intersect_range(injective_statements).range();
  auto transitive_dependent_stmt =
    active_dependences.intersect_domain(reduction_dependent_stmt).intersect_range(injective_statements).range();
  while (!transitive_dependent_stmt.is_empty() &&
         !transitive_dependent_stmt.subtract(reduction_dependent_stmt).is_empty()) {
    reduction_dependent_stmt = reduction_dependent_stmt.unite(transitive_dependent_stmt);
    transitive_dependent_stmt =
      active_dependences.intersect_domain(reduction_dependent_stmt).intersect_range(injective_statements).range();
  }

  isl::union_set reduction_indenpendent_stmt = injective_statements.subtract(reduction_dependent_stmt);

  if (reduction_indenpendent_stmt.is_empty() && reduction_dependent_stmt.is_empty()) {
    return false;
  }

  // Check the rest statements are sequential after splitting reduction dependent and independent statements from
  // reduction statements
  if (!AreSequentialStatements(reduction_indenpendent_stmt, domain.subtract(reduction_indenpendent_stmt),
                               dependences) ||
      !AreSequentialStatements(domain.subtract(reduction_dependent_stmt), reduction_dependent_stmt, dependences)) {
    return false;
  }

  if (scop_info_.user_config_.GetTarget() == TARGET_CPU) {
    SplitInitStatements(reduction_indenpendent_stmt);
    need_split_reduce_ = false;
  }

  // Reorder statements in "reduction-independent-stmt -> reduction-stmt -> reduction-dependent-stmt" order
  node = ReorderStatements(node, reduction_indenpendent_stmt, reduction_dependent_stmt);

  return true;
}

// Separate the init statement from other statements
void ReduceManager::SplitInitStatements(isl::union_set &reduction_indenpendent_stmt) {
  auto init_statements = isl::union_set::empty(reduction_indenpendent_stmt.ctx());
  for (auto init_stmt : scop_info_.analysis_result_.GetReduceInitIds()) {
    reduction_indenpendent_stmt.foreach_set([init_stmt, &init_statements](const isl::set &set) {
      isl::id id = set.get_tuple_id();
      if (id.to_str() == init_stmt.to_str()) {
        init_statements = init_statements.unite(set);
        return;
      }
    });
  }

  reduction_indenpendent_stmt = init_statements;
}

}  // namespace poly
}  // namespace ir
}  // namespace akg
