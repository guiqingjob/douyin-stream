#!/usr/bin/env python3
"""Comprehensive test for all transcribe and pipeline modules."""

import importlib
import inspect
import sys
import traceback

RESULTS = []

def test_import(module_name):
    """Test if a module can be imported."""
    try:
        mod = importlib.import_module(module_name)
        return "PASS", mod, None
    except Exception as e:
        return "FAIL", None, str(e)

def test_function_exists(mod, func_name):
    """Test if a function exists in module and check signature."""
    if mod is None:
        return "FAIL", f"Module is None", None
    try:
        func = getattr(mod, func_name, None)
        if func is None:
            return "FAIL", f"Function '{func_name}' not found", None
        sig = inspect.signature(func)
        return "PASS", str(sig), None
    except Exception as e:
        return "FAIL", str(e), None

def test_class_exists(mod, class_name):
    """Test if a class exists in module."""
    if mod is None:
        return "FAIL", f"Module is None", None
    try:
        cls = getattr(mod, class_name, None)
        if cls is None:
            return "FAIL", f"Class '{class_name}' not found", None
        return "PASS", str(inspect.signature(cls.__init__)), None
    except Exception as e:
        return "FAIL", str(e), None

def record_result(category, module, test_name, status, detail=""):
    RESULTS.append({
        "category": category,
        "module": module,
        "test": test_name,
        "status": status,
        "detail": detail
    })

# ==================== 1. Transcribe CLI Modules ====================
print("=" * 80)
print("1. 转写 CLI 模块 (media_tools.transcribe.cli)")
print("=" * 80)

cli_modules = [
    "media_tools.transcribe.cli.main",
    "media_tools.transcribe.cli.auth",
    "media_tools.transcribe.cli.capture",
    "media_tools.transcribe.cli.run_api",
    "media_tools.transcribe.cli.run_batch",
    "media_tools.transcribe.cli.accounts_status",
    "media_tools.transcribe.cli.summarize_network",
    "media_tools.transcribe.cli.claim_equity",
    "media_tools.transcribe.cli.claim_needed",
    "media_tools.transcribe.cli.interactive_menu",
    "media_tools.transcribe.cli.init_wizard",
    "media_tools.transcribe.cli.common",
    "media_tools.transcribe.cli.flow_execution",
    "media_tools.transcribe.cli.rich_ui",
    "media_tools.transcribe.cli.cleanup_remote_records",
]

for mod_name in cli_modules:
    status, mod, err = test_import(mod_name)
    record_result("CLI", mod_name, "import", status, err)
    print(f"  [{status}] import {mod_name}" + (f" - {err}" if err else ""))

# Test main.py functions
print("\n--- main.py functions ---")
_, main_mod, _ = test_import("media_tools.transcribe.cli.main")
if main_mod:
    for func in ["main", "run", "print_overview"]:
        status, detail, _ = test_function_exists(main_mod, func)
        record_result("CLI", "main.py", func, status, detail)
        print(f"  [{status}] main.{func}() {detail}")

# Test auth.py functions
print("\n--- auth.py functions ---")
_, auth_mod, _ = test_import("media_tools.transcribe.cli.auth")
if auth_mod:
    for func in ["build_parser", "run", "main"]:
        status, detail, _ = test_function_exists(auth_mod, func)
        record_result("CLI", "auth.py", func, status, detail)
        print(f"  [{status}] auth.{func}() {detail}")

# Test capture.py
print("\n--- capture.py functions ---")
_, capture_mod, _ = test_import("media_tools.transcribe.cli.capture")
if capture_mod:
    for func in ["build_parser", "run", "main", "should_capture"]:
        status, detail, _ = test_function_exists(capture_mod, func)
        record_result("CLI", "capture.py", func, status, detail)
        print(f"  [{status}] capture.{func}() {detail}")

# Test run_api.py
print("\n--- run_api.py functions ---")
_, run_api_mod, _ = test_import("media_tools.transcribe.cli.run_api")
if run_api_mod:
    for func in ["build_parser", "run", "main"]:
        status, detail, _ = test_function_exists(run_api_mod, func)
        record_result("CLI", "run_api.py", func, status, detail)
        print(f"  [{status}] run_api.{func}() {detail}")

# Test run_batch.py
print("\n--- run_batch.py functions ---")
_, run_batch_mod, _ = test_import("media_tools.transcribe.cli.run_batch")
if run_batch_mod:
    for func in ["build_parser", "run", "main"]:
        status, detail, _ = test_function_exists(run_batch_mod, func)
        record_result("CLI", "run_batch.py", func, status, detail)
        print(f"  [{status}] run_batch.{func}() {detail}")

# Test accounts_status.py
print("\n--- accounts_status.py functions ---")
_, acc_status_mod, _ = test_import("media_tools.transcribe.cli.accounts_status")
if acc_status_mod:
    for func in ["run", "main"]:
        status, detail, _ = test_function_exists(acc_status_mod, func)
        record_result("CLI", "accounts_status.py", func, status, detail)
        print(f"  [{status}] accounts_status.{func}() {detail}")

# Test summarize_network.py
print("\n--- summarize_network.py functions ---")
_, sum_net_mod, _ = test_import("media_tools.transcribe.cli.summarize_network")
if sum_net_mod:
    for func in ["build_parser", "run", "main"]:
        status, detail, _ = test_function_exists(sum_net_mod, func)
        record_result("CLI", "summarize_network.py", func, status, detail)
        print(f"  [{status}] summarize_network.{func}() {detail}")

# Test claim_equity.py
print("\n--- claim_equity.py functions ---")
_, claim_eq_mod, _ = test_import("media_tools.transcribe.cli.claim_equity")
if claim_eq_mod:
    for func in ["build_parser", "run", "main"]:
        status, detail, _ = test_function_exists(claim_eq_mod, func)
        record_result("CLI", "claim_equity.py", func, status, detail)
        print(f"  [{status}] claim_equity.{func}() {detail}")

# Test claim_needed.py
print("\n--- claim_needed.py functions ---")
_, claim_need_mod, _ = test_import("media_tools.transcribe.cli.claim_needed")
if claim_need_mod:
    for func in ["run", "main"]:
        status, detail, _ = test_function_exists(claim_need_mod, func)
        record_result("CLI", "claim_needed.py", func, status, detail)
        print(f"  [{status}] claim_needed.{func}() {detail}")

# Test interactive_menu.py
print("\n--- interactive_menu.py functions ---")
_, menu_mod, _ = test_import("media_tools.transcribe.cli.interactive_menu")
if menu_mod:
    for func in ["build_main_menu", "build_group_menu", "show_menu_prompt", "main"]:
        status, detail, _ = test_function_exists(menu_mod, func)
        record_result("CLI", "interactive_menu.py", func, status, detail)
        print(f"  [{status}] interactive_menu.{func}() {detail}")
    for cls in ["MenuItem"]:
        status, detail, _ = test_class_exists(menu_mod, cls)
        record_result("CLI", "interactive_menu.py", cls, status, detail)
        print(f"  [{status}] interactive_menu.{cls} {detail}")

# Test init_wizard.py
print("\n--- init_wizard.py functions ---")
_, wizard_mod, _ = test_import("media_tools.transcribe.cli.init_wizard")
if wizard_mod:
    for func in ["build_parser", "run", "main", "ask_question", "ask_yes_no", "setup_env_config"]:
        status, detail, _ = test_function_exists(wizard_mod, func)
        record_result("CLI", "init_wizard.py", func, status, detail)
        print(f"  [{status}] init_wizard.{func}() {detail}")

# Test common.py
print("\n--- common.py functions ---")
_, common_mod, _ = test_import("media_tools.transcribe.cli.common")
if common_mod:
    for func in ["load_config", "command_parser", "add_flow_execution_arguments"]:
        status, detail, _ = test_function_exists(common_mod, func)
        record_result("CLI", "common.py", func, status, detail)
        print(f"  [{status}] common.{func}() {detail}")
    for cls in ["FlowCliConfig"]:
        status, detail, _ = test_class_exists(common_mod, cls)
        record_result("CLI", "common.py", cls, status, detail)
        print(f"  [{status}] common.{cls} {detail}")

# Test flow_execution.py
print("\n--- flow_execution.py functions ---")
_, flow_exec_mod, _ = test_import("media_tools.transcribe.cli.flow_execution")
if flow_exec_mod:
    for func in ["execute_flow_with_fallback", "execute_flow_once"]:
        status, detail, _ = test_function_exists(flow_exec_mod, func)
        record_result("CLI", "flow_execution.py", func, status, detail)
        print(f"  [{status}] flow_execution.{func}() {detail}")

# Test rich_ui.py
print("\n--- rich_ui.py functions ---")
_, rich_ui_mod, _ = test_import("media_tools.transcribe.cli.rich_ui")
if rich_ui_mod:
    for func in ["print_header", "print_info", "print_warning", "ask_prompt", "ask_confirm"]:
        status, detail, _ = test_function_exists(rich_ui_mod, func)
        record_result("CLI", "rich_ui.py", func, status, detail)
        print(f"  [{status}] rich_ui.{func}() {detail}")

# ==================== 2. Transcribe Core Modules ====================
print("\n" + "=" * 80)
print("2. 转写核心模块 (media_tools.transcribe)")
print("=" * 80)

core_modules = [
    "media_tools.transcribe",
    "media_tools.transcribe.flow",
    "media_tools.transcribe.config",
    "media_tools.transcribe.errors",
    "media_tools.transcribe.http",
    "media_tools.transcribe.accounts",
    "media_tools.transcribe.account_status",
    "media_tools.transcribe.quota",
    "media_tools.transcribe.runtime",
    "media_tools.transcribe.oss_upload",
    "media_tools.transcribe.result_metadata",
]

for mod_name in core_modules:
    status, mod, err = test_import(mod_name)
    record_result("CORE", mod_name, "import", status, err)
    print(f"  [{status}] import {mod_name}" + (f" - {err}" if err else ""))

# Test config.py
print("\n--- config.py ---")
_, config_mod, _ = test_import("media_tools.transcribe.config")
if config_mod:
    for cls in ["AppConfig", "AppPaths"]:
        status, detail, _ = test_class_exists(config_mod, cls)
        record_result("CORE", "config.py", cls, status, detail)
        print(f"  [{status}] config.{cls} {detail}")
    for func in ["load_config"]:
        status, detail, _ = test_function_exists(config_mod, func)
        record_result("CORE", "config.py", func, status, detail)
        print(f"  [{status}] config.{func}() {detail}")

# Test flow.py
print("\n--- flow.py ---")
_, flow_mod, _ = test_import("media_tools.transcribe.flow")
if flow_mod:
    for cls in ["FlowResult", "FlowDebugArtifacts"]:
        status, detail, _ = test_class_exists(flow_mod, cls)
        record_result("CORE", "flow.py", cls, status, detail)
        print(f"  [{status}] flow.{cls} {detail}")
    for func in ["run_real_flow", "poll_until_done", "build_upload_tag"]:
        status, detail, _ = test_function_exists(flow_mod, func)
        record_result("CORE", "flow.py", func, status, detail)
        print(f"  [{status}] flow.{func}() {detail}")

# Test errors.py
print("\n--- errors.py ---")
_, errors_mod, _ = test_import("media_tools.transcribe.errors")
if errors_mod:
    for cls in ["QwenTranscribeError", "UserFacingError", "ConfigurationError", "InputValidationError", "AuthenticationRequiredError"]:
        status, detail, _ = test_class_exists(errors_mod, cls)
        record_result("CORE", "errors.py", cls, status, detail)
        print(f"  [{status}] errors.{cls} {detail}")

# Test quota.py
print("\n--- quota.py functions ---")
_, quota_mod, _ = test_import("media_tools.transcribe.quota")
if quota_mod:
    for cls in ["QuotaSnapshot", "ClaimEquityResult"]:
        status, detail, _ = test_class_exists(quota_mod, cls)
        record_result("CORE", "quota.py", cls, status, detail)
        print(f"  [{status}] quota.{cls} {detail}")
    for func in ["claim_equity_quota", "get_quota_snapshot", "record_quota_consumption"]:
        status, detail, _ = test_function_exists(quota_mod, func)
        record_result("CORE", "quota.py", func, status, detail)
        print(f"  [{status}] quota.{func}() {detail}")

# Test runtime.py
print("\n--- runtime.py ---")
_, runtime_mod, _ = test_import("media_tools.transcribe.runtime")
if runtime_mod:
    for cls in ["ExportConfig"]:
        status, detail, _ = test_class_exists(runtime_mod, cls)
        record_result("CORE", "runtime.py", cls, status, detail)
        print(f"  [{status}] runtime.{cls} {detail}")
    for func in ["load_dotenv", "as_absolute", "ensure_dir", "now_stamp", "guess_mime_type", "get_export_config"]:
        status, detail, _ = test_function_exists(runtime_mod, func)
        record_result("CORE", "runtime.py", func, status, detail)
        print(f"  [{status}] runtime.{func}() {detail}")

# Test accounts.py
print("\n--- accounts.py ---")
_, accounts_mod, _ = test_import("media_tools.transcribe.accounts")
if accounts_mod:
    for cls in ["ExecutionAccount", "ExecutionAccounts"]:
        status, detail, _ = test_class_exists(accounts_mod, cls)
        record_result("CORE", "accounts.py", cls, status, detail)
        print(f"  [{status}] accounts.{cls} {detail}")
    for func in ["load_accounts_config", "resolve_auth_state_path"]:
        status, detail, _ = test_function_exists(accounts_mod, func)
        record_result("CORE", "accounts.py", func, status, detail)
        print(f"  [{status}] accounts.{func}() {detail}")

# Test http.py
print("\n--- http.py ---")
_, http_mod, _ = test_import("media_tools.transcribe.http")
if http_mod:
    for func in ["api_json", "download_file"]:
        status, detail, _ = test_function_exists(http_mod, func)
        record_result("CORE", "http.py", func, status, detail)
        print(f"  [{status}] http.{func}() {detail}")

# Test oss_upload.py
print("\n--- oss_upload.py ---")
_, oss_mod, _ = test_import("media_tools.transcribe.oss_upload")
if oss_mod:
    for func in ["upload_file_to_oss"]:
        status, detail, _ = test_function_exists(oss_mod, func)
        record_result("CORE", "oss_upload.py", func, status, detail)
        print(f"  [{status}] oss_upload.{func}() {detail}")

# ==================== 3. Pipeline Modules ====================
print("\n" + "=" * 80)
print("3. Pipeline 模块 (media_tools.pipeline)")
print("=" * 80)

pipeline_modules = [
    "media_tools.pipeline",
    "media_tools.pipeline.config",
    "media_tools.pipeline.orchestrator_v2",
    "media_tools.pipeline.orchestrator",
]

for mod_name in pipeline_modules:
    status, mod, err = test_import(mod_name)
    record_result("PIPELINE", mod_name, "import", status, err)
    print(f"  [{status}] import {mod_name}" + (f" - {err}" if err else ""))

# Test orchestrator_v2.py
print("\n--- orchestrator_v2.py ---")
_, orch_v2_mod, _ = test_import("media_tools.pipeline.orchestrator_v2")
if orch_v2_mod:
    for cls in ["OrchestratorV2", "ErrorType"]:
        status, detail, _ = test_class_exists(orch_v2_mod, cls)
        record_result("PIPELINE", "orchestrator_v2.py", cls, status, detail)
        print(f"  [{status}] orchestrator_v2.{cls} {detail}")
    for func in ["classify_error"]:
        status, detail, _ = test_function_exists(orch_v2_mod, func)
        record_result("PIPELINE", "orchestrator_v2.py", func, status, detail)
        print(f"  [{status}] orchestrator_v2.{func}() {detail}")

# Test pipeline config.py
print("\n--- pipeline config.py ---")
_, pconfig_mod, _ = test_import("media_tools.pipeline.config")
if pconfig_mod:
    for cls in ["PipelineConfig"]:
        status, detail, _ = test_class_exists(pconfig_mod, cls)
        record_result("PIPELINE", "config.py", cls, status, detail)
        print(f"  [{status}] pipeline_config.{cls} {detail}")
    for func in ["load_pipeline_config"]:
        status, detail, _ = test_function_exists(pconfig_mod, func)
        record_result("PIPELINE", "config.py", func, status, detail)
        print(f"  [{status}] pipeline_config.{func}() {detail}")

# ==================== Summary ====================
print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)

pass_count = sum(1 for r in RESULTS if r["status"] == "PASS")
fail_count = sum(1 for r in RESULTS if r["status"] == "FAIL")
warn_count = sum(1 for r in RESULTS if r["status"] == "WARN")

print(f"\n总计: {len(RESULTS)} 个测试")
print(f"  PASS: {pass_count}")
print(f"  FAIL: {fail_count}")
print(f"  WARN: {warn_count}")

print("\n--- FAIL 详情 ---")
for r in RESULTS:
    if r["status"] == "FAIL":
        print(f"  [{r['category']}] {r['module']}::{r['test']} - {r['detail']}")

print("\n--- WARN 详情 ---")
for r in RESULTS:
    if r["status"] == "WARN":
        print(f"  [{r['category']}] {r['module']}::{r['test']} - {r['detail']}")

# 最终结果码
if fail_count == 0:
    print("\n[SUCCESS] 所有测试通过!")
    sys.exit(0)
else:
    print(f"\n[WARNING] {fail_count} 个测试失败，请检查上述详情。")
    sys.exit(1)
