import agent_spec_kit as ek
"""Regressions extracted from user-simulation failures (appended by extraction study)."""

from agent_spec_kit_discovered_d87dbbf5190d3a66 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_d87dbbf5190d3a66 import bind_scenario_context
from agent_spec_kit_discovered_d87dbbf5190d3a66 import o
from agent_spec_kit_discovered_d87dbbf5190d3a66 import sim_stop
from agent_spec_kit_discovered_d87dbbf5190d3a66 import store_us_t20
from agent_spec_kit_discovered_d87dbbf5190d3a66 import to



# --- agent-spec-kit regression extraction: REG-SIM-T20-0 (fingerprint=46bdc78e057021f5fcaef5a3) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-0', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_0(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('I need my billing breakdown and current plan cost before I log in. For reference, my details are: customer_id CUST-020, verification_token 1990-20-15, line_id LINE-0020, postcode E1 6AN.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('Yes, please pull the current invoice line items for LINE-0020 so I can see the full breakdown and plan cost before I log in. For reference, my customer_id is CUST-020.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
    )
import agent_spec_kit.match as m
from agent_spec_kit_discovered_849bc04e205f6957 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_849bc04e205f6957 import bind_scenario_context
from agent_spec_kit_discovered_849bc04e205f6957 import o
from agent_spec_kit_discovered_849bc04e205f6957 import sim_stop
from agent_spec_kit_discovered_849bc04e205f6957 import store_us_t38
from agent_spec_kit_discovered_849bc04e205f6957 import to



# --- agent-spec-kit regression extraction: REG-SIM-T38-2 (fingerprint=36796f2d1310f2748389a377) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T38-2', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t38', user_fixture='user_simulator_us_t38')
async def regression_REG_SIM_T38_2(s, store_us_t38):
    bind_scenario_context('test_t38_sim_study', variant='reference')
    (
        s
        .user_message("Hi, I'm CUST-038 (verification 1990-38-15), on line LINE-0038 (postcode E1 6AN). My connection keeps lagging on and off; I need thorough network diagnostics and confirmation your systems are responding.")
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Here for guided troubleshooting; customer_id CUST-038, verification_token 1990-38-15, line LINE-0038. Please start the guided steps: reboot router/modem, test with a wired connection if possible, and record latency results.')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.network_specialist_children(), m.tool_call('heartbeat_ping')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t38))
        .assert_output(m.string(min_len=5), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_849bc04e205f6957 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_849bc04e205f6957 import bind_scenario_context
from agent_spec_kit_discovered_849bc04e205f6957 import o
from agent_spec_kit_discovered_849bc04e205f6957 import sim_stop
from agent_spec_kit_discovered_849bc04e205f6957 import store_us_t38
from agent_spec_kit_discovered_849bc04e205f6957 import to



# --- agent-spec-kit regression extraction: REG-SIM-T38-0 (fingerprint=d9b5c640e0068ca8a6eb853e) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T38-0', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t38', user_fixture='user_simulator_us_t38')
async def regression_REG_SIM_T38_0(s, store_us_t38):
    bind_scenario_context('test_t38_sim_study', variant='reference')
    (
        s
        .user_message("I'm seeing lag on and off. Here are my details: customer_id CUST-038, verification_token 1990-38-15, line_id LINE-0038, postcode E1 6AN — I want thorough diagnostics and to be confident your systems are responding.")
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('I’ll wait for latency timing and speed test data to proceed with diagnostics. For transparency, my details are: customer_id CUST-038, verification_token 1990-38-15, line_id LINE-0038, postcode E1 6AN.')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.network_specialist_children(), m.tool_call('heartbeat_ping')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t38))
        .assert_output(m.string(min_len=5), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_849bc04e205f6957 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_849bc04e205f6957 import bind_scenario_context
from agent_spec_kit_discovered_849bc04e205f6957 import o
from agent_spec_kit_discovered_849bc04e205f6957 import sim_stop
from agent_spec_kit_discovered_849bc04e205f6957 import store_us_t38
from agent_spec_kit_discovered_849bc04e205f6957 import to



# --- agent-spec-kit regression extraction: REG-SIM-T38-4 (fingerprint=f5c4d8b254aeee07778d0088) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T38-4', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t38', user_fixture='user_simulator_us_t38')
async def regression_REG_SIM_T38_4(s, store_us_t38):
    bind_scenario_context('test_t38_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m CUST-038, verification 1990-38-15, line LINE-0038 (E1 6AN). My connection keeps lagging on and off.')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Please escalate to a Network Diagnostics Specialist for deeper analysis. I want thorough diagnostics and confidence the system is responding.')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.network_specialist_children(), m.tool_call('heartbeat_ping')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t38))
        .assert_output(m.string(min_len=5), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_849bc04e205f6957 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_849bc04e205f6957 import bind_scenario_context
from agent_spec_kit_discovered_849bc04e205f6957 import o
from agent_spec_kit_discovered_849bc04e205f6957 import sim_stop
from agent_spec_kit_discovered_849bc04e205f6957 import store_us_t38
from agent_spec_kit_discovered_849bc04e205f6957 import to



# --- agent-spec-kit regression extraction: REG-SIM-T38-1 (fingerprint=93cfdadcadea402537f56eab) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T38-1', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t38', user_fixture='user_simulator_us_t38')
async def regression_REG_SIM_T38_1(s, store_us_t38):
    bind_scenario_context('test_t38_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m here; my connection keeps lagging on and off and I want thorough diagnostics to confirm your systems are responding—reference: customer_id CUST-038, verification_token 1990-38-15, line_id LINE-0038, postcode E1 6AN. Are you still there?')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Yes, I’m here and I’d like to escalate for deeper diagnostics now.\nMy details: customer_id CUST-038, verification_token 1990-38-15, line LINE-0038, postcode E1 6AN, ticket TCK-00001.')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.network_specialist_children(), m.tool_call('heartbeat_ping')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t38))
        .assert_output(m.string(min_len=5), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_d87dbbf5190d3a66 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_d87dbbf5190d3a66 import bind_scenario_context
from agent_spec_kit_discovered_d87dbbf5190d3a66 import o
from agent_spec_kit_discovered_d87dbbf5190d3a66 import sim_stop
from agent_spec_kit_discovered_d87dbbf5190d3a66 import store_us_t20
from agent_spec_kit_discovered_d87dbbf5190d3a66 import to



# --- agent-spec-kit regression extraction: REG-SIM-T20-2 (fingerprint=b27899f6fa95405d3e184d09) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-2', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_2(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('I need my billing breakdown and plan cost before I log in. To speed things up, here are my details: customer_id CUST-020, verification_token 1990-20-15.')
        .user_message('I need the billing breakdown now before I log in. My details: customer_id CUST-020, verification_token 1990-20-15, line_id LINE-0020, postcode E1 6AN; pull the latest bill items.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('I want the latest line-item bill for LINE-0020 on the current invoice before I log in; here are my details: customer_id CUST-020, verification_token 1990-20-15, line_id LINE-0020, postcode E1 6AN. Please pull the breakdown (usage, plan charges, taxes, roaming) now.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_d87dbbf5190d3a66 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_d87dbbf5190d3a66 import bind_scenario_context
from agent_spec_kit_discovered_d87dbbf5190d3a66 import o
from agent_spec_kit_discovered_d87dbbf5190d3a66 import sim_stop
from agent_spec_kit_discovered_d87dbbf5190d3a66 import store_us_t20
from agent_spec_kit_discovered_d87dbbf5190d3a66 import to



# --- agent-spec-kit regression extraction: REG-SIM-T20-1 (fingerprint=9046d825c5c049c914780994) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-1', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_1(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('I need my billing breakdown and plan cost before I log in. For reference, my IDs are: customer_id CUST-020, verification_token 1990-20-15, line_id LINE-0020, postcode E1 6AN.')
        .user_message('I need the full billing breakdown and the current plan cost for LINE-0020 before I log in. For reference, my IDs are customer_id CUST-020, verification_token 1990-20-15, line_id LINE-0020, postcode E1 6AN.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('Please pull the combined itemized billing for LINE-0020 plus the current plan cost and show it here.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_d87dbbf5190d3a66 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_d87dbbf5190d3a66 import bind_scenario_context
from agent_spec_kit_discovered_d87dbbf5190d3a66 import o
from agent_spec_kit_discovered_d87dbbf5190d3a66 import sim_stop
from agent_spec_kit_discovered_d87dbbf5190d3a66 import store_us_t20
from agent_spec_kit_discovered_d87dbbf5190d3a66 import to



# --- agent-spec-kit regression extraction: REG-SIM-T20-3 (fingerprint=8cafc58e5a3ad35cc8c9a723) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-3', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_3(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message("Hi, I need my billing breakdown and plan cost before I log in. I'm not sure which account this chat is for, but here are the details: customer_id CUST-020, line_id LINE-0020, postcode E1 6AN, verification_token 1990-20-15.")
        .user_message('Please pull the latest bill and itemized charges for LINE-0020 so I can see the costs before I log in. I’m CUST-020, verification 1990-20-15.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message("I'm CUST-020, and I need the billing breakdown and current plan cost for LINE-0020 before I log in. Details I have: postcode E1 6AN, verification_token 1990-20-15, line_id LINE-0020.")
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_849bc04e205f6957 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_849bc04e205f6957 import bind_scenario_context
from agent_spec_kit_discovered_849bc04e205f6957 import o
from agent_spec_kit_discovered_849bc04e205f6957 import sim_stop
from agent_spec_kit_discovered_849bc04e205f6957 import store_us_t38
from agent_spec_kit_discovered_849bc04e205f6957 import to



# --- agent-spec-kit regression extraction: REG-SIM-T38-3 (fingerprint=0ff62734664b4e46cf506932) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T38-3', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t38', user_fixture='user_simulator_us_t38')
async def regression_REG_SIM_T38_3(s, store_us_t38):
    bind_scenario_context('test_t38_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m CUST-038. My line LINE-0038 (postcode E1 6AN, verification token 1990-38-15) keeps lagging on and off, and I need thorough diagnostics to confirm your systems are responding.')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Yes, please guide me through the steps—I really want thorough checks to confirm the network is healthy because the lag keeps happening. For reference: customer_id CUST-038, verification_token 1990-38-15, line_id LINE-0038, postcode E1 6AN.')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.network_specialist_children(), m.tool_call('heartbeat_ping')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t38))
        .assert_output(m.string(min_len=5), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_d87dbbf5190d3a66 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_d87dbbf5190d3a66 import bind_scenario_context
from agent_spec_kit_discovered_d87dbbf5190d3a66 import o
from agent_spec_kit_discovered_d87dbbf5190d3a66 import sim_stop
from agent_spec_kit_discovered_d87dbbf5190d3a66 import store_us_t20
from agent_spec_kit_discovered_d87dbbf5190d3a66 import to



# --- agent-spec-kit regression extraction: REG-SIM-T20-4 (fingerprint=0c993eaf477a51df7fe0c8ad) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-4', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_4(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message("Hi, I'm CUST-020 and I need my billing breakdown and plan cost before I log in; verification token 1990-20-15, line LINE-0020, postcode E1 6AN. Also, why does authentication protect my account data?")
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('Yes, please fetch the itemized bill for the latest cycle and walk me through each charge. For reference, my account is CUST-020 on LINE-0020 (postcode E1 6AN).')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_ad839d1428119abc import SIM_CHAT_OPEN
from agent_spec_kit_discovered_ad839d1428119abc import bind_scenario_context
from agent_spec_kit_discovered_ad839d1428119abc import o
from agent_spec_kit_discovered_ad839d1428119abc import sim_stop
from agent_spec_kit_discovered_ad839d1428119abc import store_us_t29
from agent_spec_kit_discovered_ad839d1428119abc import to



# --- agent-spec-kit regression extraction: REG-SIM-T29-3 (fingerprint=493bd1b254832fbea101e67b) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-3', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_3(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('Hello, I need a replacement SIM for my correct line LINE-0029. My details: customer_id CUST-029 and verification 1990-29-15; I believe the affected line is LINE-WRONG, please send the SIM to my default address (postcode E1 6AN).')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(to.clarification_output('Does not confirm a SIM order was placed on the wrong line', 'Asks which line is correct or acknowledges line uncertainty'), actor='agent', turn='up_to_now')
        .user_message('LINE-0029, physical SIM, shipping to the default address on file (postcode E1 6AN). For reference: customer_id CUST-029, verification_token 1990-29-15.')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.order_sim_on_line(seed_line)], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(to.premature_action_output('LINE-WRONG', action='order'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_57ab47c85d4f88b7 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_57ab47c85d4f88b7 import bind_scenario_context
from agent_spec_kit_discovered_57ab47c85d4f88b7 import o
from agent_spec_kit_discovered_57ab47c85d4f88b7 import sim_stop
from agent_spec_kit_discovered_57ab47c85d4f88b7 import store_us_t43
from agent_spec_kit_discovered_57ab47c85d4f88b7 import to



# --- agent-spec-kit regression extraction: REG-SIM-T43-1 (fingerprint=d6065cf8b3dc65941ea25afc) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T43-1', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t43', user_fixture='user_simulator_us_t43')
async def regression_REG_SIM_T43_1(s, store_us_t43):
    bind_scenario_context('test_t43_sim_study', variant='reference')
    stale = o.stale_line_id(store_us_t43)
    (
        s
        .user_message('Hi, my SIM won’t connect and I think this is on the corrected line LINE-0043, not LINE-0043B, since I’m mixing up lines in my family account. My details: customer_id CUST-043, verification 1990-43-15, postcode E1 6AN.')
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .user_message('Thanks for the update—my details are customer_id CUST-043, verification_token 1990-43-15, and the corrected line is LINE-0043 (not LINE-0043B). Yes, please run a quick line status check on LINE-0043 now.')
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Acknowledges the customer corrected which line needs the ticket', 'Does not confirm a ticket was opened on the wrong line before correction'), actor='agent', turn='up_to_now')
        .user_message('Hi, it’s CUST-043, verification 1990-43-15. My SIM won’t connect and I think the issue is on LINE-0043 (LINE-0043B is a different line); please run a quick network diagnostic on LINE-0043.')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(lambda: o.assert_latest_ticket_reason_excludes(store_us_t43, 'billing', 'invoice', 'plan dispute'))
        .assert_output(to.issue_binding_output("Confirms a support ticket on the customer's main line for SIM or connectivity", 'Does not describe the issue only as a billing or plan dispute'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_ad839d1428119abc import SIM_CHAT_OPEN
from agent_spec_kit_discovered_ad839d1428119abc import bind_scenario_context
from agent_spec_kit_discovered_ad839d1428119abc import o
from agent_spec_kit_discovered_ad839d1428119abc import sim_stop
from agent_spec_kit_discovered_ad839d1428119abc import store_us_t29
from agent_spec_kit_discovered_ad839d1428119abc import to



# --- agent-spec-kit regression extraction: REG-SIM-T29-4 (fingerprint=fff157a005f1bd1bf076c7ce) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-4', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_4(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('Hi, I’m CUST-029 and I need a replacement SIM for LINE-0029—the correct line; the affected line seems LINE-WRONG, postcode E1 6AN, verification 1990-29-15, please send the SIM to my default address.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(to.clarification_output('Does not confirm a SIM order was placed on the wrong line', 'Asks which line is correct or acknowledges line uncertainty'), actor='agent', turn='up_to_now')
        .user_message('Correct line_id is LINE-0029. I want a physical SIM sent to my default address on file (CUST-029, verification 1990-29-15, postcode E1 6AN).')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.order_sim_on_line(seed_line)], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(to.premature_action_output('LINE-WRONG', action='order'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_e4c10c21214aa041 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_e4c10c21214aa041 import bind_scenario_context
from agent_spec_kit_discovered_e4c10c21214aa041 import o
from agent_spec_kit_discovered_e4c10c21214aa041 import sim_stop
from agent_spec_kit_discovered_e4c10c21214aa041 import store_us_t45
from agent_spec_kit_discovered_e4c10c21214aa041 import to



# --- agent-spec-kit regression extraction: REG-SIM-T45-0 (fingerprint=4d949cb172ca9c4986d56348) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T45-0', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t45', user_fixture='user_simulator_us_t45')
async def regression_REG_SIM_T45_0(s, store_us_t45):
    bind_scenario_context('test_t45_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m CUST-045 (account id); my line is LINE-0045 and postcode E1 6AN, verification_token 1990-45-15.  \nI need to know what plan I’m on and why my line isn’t working, and I may not have my verification code with me.')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t45))
        .assert_output(to.preauth_composite_output(store_us_t45, 'plan', 'account'), actor='agent', turn='up_to_now')
        .user_message('I’m CUST-045, LINE-0045, postcode E1 6AN; I may not have my verification code (1990-45-15) with me right now. Please open a standard diagnostic ticket for LINE-0045 and I’ll provide authentication when I’ve got the code.')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t45))
    )

from agent_spec_kit_discovered_cf508e89e1ee43ea import SIM_CHAT_OPEN
from agent_spec_kit_discovered_cf508e89e1ee43ea import bind_scenario_context
from agent_spec_kit_discovered_cf508e89e1ee43ea import o
from agent_spec_kit_discovered_cf508e89e1ee43ea import sim_stop
from agent_spec_kit_discovered_cf508e89e1ee43ea import store_us_t04
from agent_spec_kit_discovered_cf508e89e1ee43ea import to



# --- agent-spec-kit regression extraction: REG-SIM-T04-0 (fingerprint=608b001f44b7f0799c593797) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T04-0', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t04', user_fixture='user_simulator_us_t04')
async def regression_REG_SIM_T04_0(s, store_us_t04):
    bind_scenario_context('test_t04_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m CUST-004, verification 1990-04-15, line LINE-0004. I’ve already restarted, but mobile data on LINE-0004 is still not working and I need help.')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Postcode E1 6AN. I’ve already restarted my device, but data on LINE-0004 is still not working; reference: customer_id CUST-004, verification_token 1990-04-15.')
        .assert_tool_calls([m.tool_call('record_user_action'), m.tool_call('create_support_ticket')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_ticket_exists(store_us_t04))
        .assert_output(to.mutation_claim_output('Confirms a support ticket was opened'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_e4c10c21214aa041 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_e4c10c21214aa041 import bind_scenario_context
from agent_spec_kit_discovered_e4c10c21214aa041 import o
from agent_spec_kit_discovered_e4c10c21214aa041 import sim_stop
from agent_spec_kit_discovered_e4c10c21214aa041 import store_us_t45
from agent_spec_kit_discovered_e4c10c21214aa041 import to



# --- agent-spec-kit regression extraction: REG-SIM-T45-2 (fingerprint=af4a4bd4f800e1a48ed7f704) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T45-2', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t45', user_fixture='user_simulator_us_t45')
async def regression_REG_SIM_T45_2(s, store_us_t45):
    bind_scenario_context('test_t45_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m CUST-045, line LINE-0045, postcode E1 6AN. My line isn’t working and I want to know what plan I’m on, but I may not have my verification code with me right now.')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t45))
        .assert_output(to.preauth_composite_output(store_us_t45, 'plan', 'account'), actor='agent', turn='up_to_now')
        .user_message('Not sure I have the verification code with me right now, can we move past auth for a moment? My account id is CUST-045 and line LINE-0045, postcode E1 6AN.')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t45))
    )

from agent_spec_kit_discovered_e4c10c21214aa041 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_e4c10c21214aa041 import bind_scenario_context
from agent_spec_kit_discovered_e4c10c21214aa041 import o
from agent_spec_kit_discovered_e4c10c21214aa041 import sim_stop
from agent_spec_kit_discovered_e4c10c21214aa041 import store_us_t45
from agent_spec_kit_discovered_e4c10c21214aa041 import to



# --- agent-spec-kit regression extraction: REG-SIM-T45-1 (fingerprint=f11f6976483499394d7c3803) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T45-1', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t45', user_fixture='user_simulator_us_t45')
async def regression_REG_SIM_T45_1(s, store_us_t45):
    bind_scenario_context('test_t45_sim_study', variant='reference')
    (
        s
        .user_message("I'm CUST-045. I might not have my verification code with me right now; verification token 1990-45-15, line LINE-0045, postcode E1 6AN. I need to know my current plan and why the line isn't working, and I’d like to delay authentication until we confirm it's really me.")
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t45))
        .assert_output(to.preauth_composite_output(store_us_t45, 'plan', 'account'), actor='agent', turn='up_to_now')
        .user_message('How do I know this is the legit support line for CUST-045? If so, please share a recent ticket reference or verification checkpoint before I disclose any account details.')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t45))
    )

from agent_spec_kit_discovered_e4c10c21214aa041 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_e4c10c21214aa041 import bind_scenario_context
from agent_spec_kit_discovered_e4c10c21214aa041 import o
from agent_spec_kit_discovered_e4c10c21214aa041 import sim_stop
from agent_spec_kit_discovered_e4c10c21214aa041 import store_us_t45
from agent_spec_kit_discovered_e4c10c21214aa041 import to



# --- agent-spec-kit regression extraction: REG-SIM-T45-4 (fingerprint=82ca7f78725ab45f6685cf35) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T45-4', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t45', user_fixture='user_simulator_us_t45')
async def regression_REG_SIM_T45_4(s, store_us_t45):
    bind_scenario_context('test_t45_sim_study', variant='reference')
    (
        s
        .user_message("Hi, I'm CUST-045 (verification_token 1990-45-15, line LINE-0045, postcode E1 6AN). My line isn't working and I need to know my plan, but I don't have my verification code with me right now.")
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t45))
        .assert_output(to.preauth_composite_output(store_us_t45, 'plan', 'account'), actor='agent', turn='up_to_now')
        .user_message('I don’t have my verification code with me right now. Could we use 1990-45-15 for authentication, or is there a simpler option I can use?')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t45))
    )

from agent_spec_kit_discovered_cf508e89e1ee43ea import SIM_CHAT_OPEN
from agent_spec_kit_discovered_cf508e89e1ee43ea import bind_scenario_context
from agent_spec_kit_discovered_cf508e89e1ee43ea import o
from agent_spec_kit_discovered_cf508e89e1ee43ea import sim_stop
from agent_spec_kit_discovered_cf508e89e1ee43ea import store_us_t04
from agent_spec_kit_discovered_cf508e89e1ee43ea import to



# --- agent-spec-kit regression extraction: REG-SIM-T04-2 (fingerprint=8fd0c0c63b62dbc94bcf946a) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T04-2', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t04', user_fixture='user_simulator_us_t04')
async def regression_REG_SIM_T04_2(s, store_us_t04):
    bind_scenario_context('test_t04_sim_study', variant='reference')
    (
        s
        .user_message('Hi, mobile data on LINE-0004 isn’t working and I already restarted my phone, but it’s still broken. Details: customer_id CUST-004, verification_token 1990-04-15, line_id LINE-0004, postcode E1 6AN.')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Restart has already been done, but mobile data on LINE-0004 is still not working; please escalate to a Network Diagnostics Specialist. For reference: customer_id CUST-004, verification_token 1990-04-15, line_id LINE-0004, postcode E1 6AN.')
        .assert_tool_calls([m.tool_call('record_user_action'), m.tool_call('create_support_ticket')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_ticket_exists(store_us_t04))
        .assert_output(to.mutation_claim_output('Confirms a support ticket was opened'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_8da1f4f0a07387b8 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_8da1f4f0a07387b8 import bind_scenario_context
from agent_spec_kit_discovered_8da1f4f0a07387b8 import o
from agent_spec_kit_discovered_8da1f4f0a07387b8 import sim_stop
from agent_spec_kit_discovered_8da1f4f0a07387b8 import store_us_t42
from agent_spec_kit_discovered_8da1f4f0a07387b8 import to



# --- agent-spec-kit regression extraction: REG-SIM-T42-0 (fingerprint=a73d2d0fa8ca267537ad0436) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T42-0', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t42', user_fixture='user_simulator_us_t42')
async def regression_REG_SIM_T42_0(s, store_us_t42):
    bind_scenario_context('test_t42_sim_study', variant='reference')
    (
        s
        .user_message("Hi, I'm CUST-042 and my verification token is 1990-42-15; my line is LINE-0042 (postcode E1 6AN), and mobile data is not working at all. I may have found my SIM in the laundry.")
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Does not confirm a replacement SIM order was placed before the customer clarified', 'Addresses mobile data or line status rather than shipping a new SIM immediately'), actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.clarification_output('Acknowledges the customer does not want a replacement SIM shipped', 'Addresses the data issue or line status rather than ordering a new SIM'), actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.issue_binding_output('Focuses on mobile data connectivity or line status rather than ordering a replacement SIM', 'Does not confirm a replacement SIM was shipped'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_8da1f4f0a07387b8 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_8da1f4f0a07387b8 import bind_scenario_context
from agent_spec_kit_discovered_8da1f4f0a07387b8 import o
from agent_spec_kit_discovered_8da1f4f0a07387b8 import sim_stop
from agent_spec_kit_discovered_8da1f4f0a07387b8 import store_us_t42
from agent_spec_kit_discovered_8da1f4f0a07387b8 import to



# --- agent-spec-kit regression extraction: REG-SIM-T42-1 (fingerprint=6ae9fc89420919164d51a647) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T42-1', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t42', user_fixture='user_simulator_us_t42')
async def regression_REG_SIM_T42_1(s, store_us_t42):
    bind_scenario_context('test_t42_sim_study', variant='reference')
    (
        s
        .user_message("Hi, it's CUST-042 on LINE-0042, postcode E1 6AN, verification 1990-42-15. My mobile data isn't working at all.")
        .user_message('Yes, LINE-0042 is the line to test. The data issue is still happening—no data, even after the check.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Does not confirm a replacement SIM order was placed before the customer clarified', 'Addresses mobile data or line status rather than shipping a new SIM immediately'), actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.clarification_output('Acknowledges the customer does not want a replacement SIM shipped', 'Addresses the data issue or line status rather than ordering a new SIM'), actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.issue_binding_output('Focuses on mobile data connectivity or line status rather than ordering a replacement SIM', 'Does not confirm a replacement SIM was shipped'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_57ab47c85d4f88b7 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_57ab47c85d4f88b7 import bind_scenario_context
from agent_spec_kit_discovered_57ab47c85d4f88b7 import o
from agent_spec_kit_discovered_57ab47c85d4f88b7 import sim_stop
from agent_spec_kit_discovered_57ab47c85d4f88b7 import store_us_t43
from agent_spec_kit_discovered_57ab47c85d4f88b7 import to



# --- agent-spec-kit regression extraction: REG-SIM-T43-0 (fingerprint=e0df4fa8a4eb7334f912a233) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T43-0', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t43', user_fixture='user_simulator_us_t43')
async def regression_REG_SIM_T43_0(s, store_us_t43):
    bind_scenario_context('test_t43_sim_study', variant='reference')
    stale = o.stale_line_id(store_us_t43)
    (
        s
        .user_message('Hi, I’m CUST-043, verify 1990-43-15, postcode E1 6AN. I believe the problem is on LINE-0043B, but the correct line for this issue is LINE-0043; my SIM won’t connect.')
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Acknowledges the customer corrected which line needs the ticket', 'Does not confirm a ticket was opened on the wrong line before correction'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(lambda: o.assert_latest_ticket_reason_excludes(store_us_t43, 'billing', 'invoice', 'plan dispute'))
        .assert_output(to.issue_binding_output("Confirms a support ticket on the customer's main line for SIM or connectivity", 'Does not describe the issue only as a billing or plan dispute'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_8da1f4f0a07387b8 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_8da1f4f0a07387b8 import bind_scenario_context
from agent_spec_kit_discovered_8da1f4f0a07387b8 import o
from agent_spec_kit_discovered_8da1f4f0a07387b8 import sim_stop
from agent_spec_kit_discovered_8da1f4f0a07387b8 import store_us_t42
from agent_spec_kit_discovered_8da1f4f0a07387b8 import to



# --- agent-spec-kit regression extraction: REG-SIM-T42-3 (fingerprint=3d4001e49e80d7a8dd11ad70) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T42-3', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t42', user_fixture='user_simulator_us_t42')
async def regression_REG_SIM_T42_3(s, store_us_t42):
    bind_scenario_context('test_t42_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m on LINE-0042 and my mobile data isn’t working at all. I may have found my SIM in the laundry and I don’t want a replacement shipped; core issue is data, details: customer_id CUST-042, verification_token 1990-42-15, line LINE-0042, postcode E1 6AN.')
        .user_message('Yes—please escalate TCK-00001 and add a note that the SIM might have been found in the laundry to give context. For reference, my details are: customer_id CUST-042, line_id LINE-0042, postcode E1 6AN, verification_token 1990-42-15.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Does not confirm a replacement SIM order was placed before the customer clarified', 'Addresses mobile data or line status rather than shipping a new SIM immediately'), actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.clarification_output('Acknowledges the customer does not want a replacement SIM shipped', 'Addresses the data issue or line status rather than ordering a new SIM'), actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.issue_binding_output('Focuses on mobile data connectivity or line status rather than ordering a replacement SIM', 'Does not confirm a replacement SIM was shipped'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_ad839d1428119abc import SIM_CHAT_OPEN
from agent_spec_kit_discovered_ad839d1428119abc import bind_scenario_context
from agent_spec_kit_discovered_ad839d1428119abc import o
from agent_spec_kit_discovered_ad839d1428119abc import sim_stop
from agent_spec_kit_discovered_ad839d1428119abc import store_us_t29
from agent_spec_kit_discovered_ad839d1428119abc import to



# --- agent-spec-kit regression extraction: REG-SIM-T29-0 (fingerprint=252f7eab2862054e4cf72da5) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-0', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_0(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('Hi, I need a replacement SIM for LINE-0029—the correct line (not LINE-WRONG). My details: customer_id CUST-029, verification_token 1990-29-15, postcode E1 6AN; please send to my default address.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(to.clarification_output('Does not confirm a SIM order was placed on the wrong line', 'Asks which line is correct or acknowledges line uncertainty'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.order_sim_on_line(seed_line)], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(to.premature_action_output('LINE-WRONG', action='order'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_8da1f4f0a07387b8 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_8da1f4f0a07387b8 import bind_scenario_context
from agent_spec_kit_discovered_8da1f4f0a07387b8 import o
from agent_spec_kit_discovered_8da1f4f0a07387b8 import sim_stop
from agent_spec_kit_discovered_8da1f4f0a07387b8 import store_us_t42
from agent_spec_kit_discovered_8da1f4f0a07387b8 import to



# --- agent-spec-kit regression extraction: REG-SIM-T42-4 (fingerprint=35e5b0cc6755cb7be8fd9154) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T42-4', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t42', user_fixture='user_simulator_us_t42')
async def regression_REG_SIM_T42_4(s, store_us_t42):
    bind_scenario_context('test_t42_sim_study', variant='reference')
    (
        s
        .user_message('Sorry about this—my mobile data isn’t working at all on LINE-0042. My customer_id is CUST-042 and verification_token is 1990-42-15.')
        .user_message('Sorry for the extra step—my postcode is E1 6AN. For reference, LINE-0042, customer_id CUST-042, verification_token 1990-42-15.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Does not confirm a replacement SIM order was placed before the customer clarified', 'Addresses mobile data or line status rather than shipping a new SIM immediately'), actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.clarification_output('Acknowledges the customer does not want a replacement SIM shipped', 'Addresses the data issue or line status rather than ordering a new SIM'), actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(to.issue_binding_output('Focuses on mobile data connectivity or line status rather than ordering a replacement SIM', 'Does not confirm a replacement SIM was shipped'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_57ab47c85d4f88b7 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_57ab47c85d4f88b7 import bind_scenario_context
from agent_spec_kit_discovered_57ab47c85d4f88b7 import o
from agent_spec_kit_discovered_57ab47c85d4f88b7 import sim_stop
from agent_spec_kit_discovered_57ab47c85d4f88b7 import store_us_t43
from agent_spec_kit_discovered_57ab47c85d4f88b7 import to



# --- agent-spec-kit regression extraction: REG-SIM-T43-2 (fingerprint=195e934284cd5590944971ea) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T43-2', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t43', user_fixture='user_simulator_us_t43')
async def regression_REG_SIM_T43_2(s, store_us_t43):
    bind_scenario_context('test_t43_sim_study', variant='reference')
    stale = o.stale_line_id(store_us_t43)
    (
        s
        .user_message('Hi, my SIM won’t connect, and I think the issue is with LINE-0043 (my correct line), not LINE-0043B. Details: customer_id CUST-043, verification_token 1990-43-15, postcode E1 6AN.')
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Acknowledges the customer corrected which line needs the ticket', 'Does not confirm a ticket was opened on the wrong line before correction'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(lambda: o.assert_latest_ticket_reason_excludes(store_us_t43, 'billing', 'invoice', 'plan dispute'))
        .assert_output(to.issue_binding_output("Confirms a support ticket on the customer's main line for SIM or connectivity", 'Does not describe the issue only as a billing or plan dispute'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_ad839d1428119abc import SIM_CHAT_OPEN
from agent_spec_kit_discovered_ad839d1428119abc import bind_scenario_context
from agent_spec_kit_discovered_ad839d1428119abc import o
from agent_spec_kit_discovered_ad839d1428119abc import sim_stop
from agent_spec_kit_discovered_ad839d1428119abc import store_us_t29
from agent_spec_kit_discovered_ad839d1428119abc import to



# --- agent-spec-kit regression extraction: REG-SIM-T29-1 (fingerprint=baa0726fbe3101b52521cd9e) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-1', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_1(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('Hi, I’m customer CUST-029 with verification token 1990-29-15. The line I need fixed is LINE-0029 (not LINE-WRONG); I need a replacement SIM sent to my default address at E1 6AN.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(to.clarification_output('Does not confirm a SIM order was placed on the wrong line', 'Asks which line is correct or acknowledges line uncertainty'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.order_sim_on_line(seed_line)], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(to.premature_action_output('LINE-WRONG', action='order'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_ad839d1428119abc import SIM_CHAT_OPEN
from agent_spec_kit_discovered_ad839d1428119abc import bind_scenario_context
from agent_spec_kit_discovered_ad839d1428119abc import o
from agent_spec_kit_discovered_ad839d1428119abc import sim_stop
from agent_spec_kit_discovered_ad839d1428119abc import store_us_t29
from agent_spec_kit_discovered_ad839d1428119abc import to



# --- agent-spec-kit regression extraction: REG-SIM-T29-2 (fingerprint=93adba08034b182135fa5c6e) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-2', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_2(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('Hi, I’m the parent account holder. I think LINE-WRONG was affected, but the correct line is LINE-0029 and I need a replacement SIM. My details are: customer_id CUST-029, verification_token 1990-29-15, postcode E1 6AN; please send the SIM to my default address.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(to.clarification_output('Does not confirm a SIM order was placed on the wrong line', 'Asks which line is correct or acknowledges line uncertainty'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.order_sim_on_line(seed_line)], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(to.premature_action_output('LINE-WRONG', action='order'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_57ab47c85d4f88b7 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_57ab47c85d4f88b7 import bind_scenario_context
from agent_spec_kit_discovered_57ab47c85d4f88b7 import o
from agent_spec_kit_discovered_57ab47c85d4f88b7 import sim_stop
from agent_spec_kit_discovered_57ab47c85d4f88b7 import store_us_t43
from agent_spec_kit_discovered_57ab47c85d4f88b7 import to



# --- agent-spec-kit regression extraction: REG-SIM-T43-4 (fingerprint=0b69583a652fefa35b926b23) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T43-4', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t43', user_fixture='user_simulator_us_t43')
async def regression_REG_SIM_T43_4(s, store_us_t43):
    bind_scenario_context('test_t43_sim_study', variant='reference')
    stale = o.stale_line_id(store_us_t43)
    (
        s
        .user_message("Hi, my SIM won't connect. My customer_id is CUST-043 and verification_token is 1990-43-15; I think the affected line is LINE-0043B, but the correct line for this issue is LINE-0043.")
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Acknowledges the customer corrected which line needs the ticket', 'Does not confirm a ticket was opened on the wrong line before correction'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(lambda: o.assert_latest_ticket_reason_excludes(store_us_t43, 'billing', 'invoice', 'plan dispute'))
        .assert_output(to.issue_binding_output("Confirms a support ticket on the customer's main line for SIM or connectivity", 'Does not describe the issue only as a billing or plan dispute'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_57ab47c85d4f88b7 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_57ab47c85d4f88b7 import bind_scenario_context
from agent_spec_kit_discovered_57ab47c85d4f88b7 import o
from agent_spec_kit_discovered_57ab47c85d4f88b7 import sim_stop
from agent_spec_kit_discovered_57ab47c85d4f88b7 import store_us_t43
from agent_spec_kit_discovered_57ab47c85d4f88b7 import to



# --- agent-spec-kit regression extraction: REG-SIM-T43-3 (fingerprint=664e1bc2b13b6677b1c27fbb) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T43-3', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t43', user_fixture='user_simulator_us_t43')
async def regression_REG_SIM_T43_3(s, store_us_t43):
    bind_scenario_context('test_t43_sim_study', variant='reference')
    stale = o.stale_line_id(store_us_t43)
    (
        s
        .user_message("Hi, I'm CUST-043; verification 1990-43-15. My SIM won't connect and I believe the issue is on LINE-0043B, but the correct line is LINE-0043.")
        .user_message("Hi, it's CUST-043 (verification 1990-43-15). Quick correction: the affected line is LINE-0043, not LINE-0043B; my SIM still won't connect.")
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Acknowledges the customer corrected which line needs the ticket', 'Does not confirm a ticket was opened on the wrong line before correction'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(lambda: o.assert_latest_ticket_reason_excludes(store_us_t43, 'billing', 'invoice', 'plan dispute'))
        .assert_output(to.issue_binding_output("Confirms a support ticket on the customer's main line for SIM or connectivity", 'Does not describe the issue only as a billing or plan dispute'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_e4c10c21214aa041 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_e4c10c21214aa041 import bind_scenario_context
from agent_spec_kit_discovered_e4c10c21214aa041 import o
from agent_spec_kit_discovered_e4c10c21214aa041 import sim_stop
from agent_spec_kit_discovered_e4c10c21214aa041 import store_us_t45
from agent_spec_kit_discovered_e4c10c21214aa041 import to



# --- agent-spec-kit regression extraction: REG-SIM-T45-3 (fingerprint=f1b400d6c74975c3f716922e) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T45-3', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t45', user_fixture='user_simulator_us_t45')
async def regression_REG_SIM_T45_3(s, store_us_t45):
    bind_scenario_context('test_t45_sim_study', variant='reference')
    (
        s
        .user_message("Hi, I'm CUST-045 (LINE-0045, postcode E1 6AN). My line has been flaky and I need to know what plan I'm on; I may not have my verification code with me, verification_token: 1990-45-15.")
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t45))
        .assert_output(to.preauth_composite_output(store_us_t45, 'plan', 'account'), actor='agent', turn='up_to_now')
        .user_message('I don’t have my verification code with me right now; can we pause authentication for a bit? I’m CUST-045, LINE-0045, and I want to know what plan I’m on and fix the flaky line.')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t45))
    )

from agent_spec_kit_discovered_cf508e89e1ee43ea import SIM_CHAT_OPEN
from agent_spec_kit_discovered_cf508e89e1ee43ea import bind_scenario_context
from agent_spec_kit_discovered_cf508e89e1ee43ea import o
from agent_spec_kit_discovered_cf508e89e1ee43ea import sim_stop
from agent_spec_kit_discovered_cf508e89e1ee43ea import store_us_t04
from agent_spec_kit_discovered_cf508e89e1ee43ea import to



# --- agent-spec-kit regression extraction: REG-SIM-T04-1 (fingerprint=638c7aeff6c48ec758e55d6b) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T04-1', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t04', user_fixture='user_simulator_us_t04')
async def regression_REG_SIM_T04_1(s, store_us_t04):
    bind_scenario_context('test_t04_sim_study', variant='reference')
    (
        s
        .user_message('Mobile data on LINE-0004 is still not working after I restarted—please escalate. Details: customer_id CUST-004, verification_token 1990-04-15, postcode E1 6AN.')
        .user_message('Yes, please escalate and add an audit note; data on LINE-0004 remains down after restarting. \nReference: customer_id CUST-004, verification_token 1990-04-15, line_id LINE-0004, postcode E1 6AN, ticket TCK-00001.')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Thanks for escalating. For context: account CUST-004, verification 1990-04-15, line LINE-0004, postcode E1 6AN, and mobile data is still not working after a restart. Please prioritize this and share an ETA from the Network Diagnostics Specialist.')
        .assert_tool_calls([m.tool_call('record_user_action'), m.tool_call('create_support_ticket')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_ticket_exists(store_us_t04))
        .assert_output(to.mutation_claim_output('Confirms a support ticket was opened'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_cf508e89e1ee43ea import SIM_CHAT_OPEN
from agent_spec_kit_discovered_cf508e89e1ee43ea import bind_scenario_context
from agent_spec_kit_discovered_cf508e89e1ee43ea import o
from agent_spec_kit_discovered_cf508e89e1ee43ea import sim_stop
from agent_spec_kit_discovered_cf508e89e1ee43ea import store_us_t04
from agent_spec_kit_discovered_cf508e89e1ee43ea import to



# --- agent-spec-kit regression extraction: REG-SIM-T04-4 (fingerprint=2a400789ed59f70c8495d931) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T04-4', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t04', user_fixture='user_simulator_us_t04')
async def regression_REG_SIM_T04_4(s, store_us_t04):
    bind_scenario_context('test_t04_sim_study', variant='reference')
    (
        s
        .user_message('Hi, I’m CUST-004 (verification 1990-04-15). Mobile data is not working on LINE-0004 in E1 6AN, and I’ve already restarted but it’s still down.')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Restarted and data is still not working on LINE-0004; please escalate for a deeper network probe. My details: customer_id CUST-004, verification_token 1990-04-15, line_id LINE-0004, postcode E1 6AN.')
        .assert_tool_calls([m.tool_call('record_user_action'), m.tool_call('create_support_ticket')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_ticket_exists(store_us_t04))
        .assert_output(to.mutation_claim_output('Confirms a support ticket was opened'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_cf508e89e1ee43ea import SIM_CHAT_OPEN
from agent_spec_kit_discovered_cf508e89e1ee43ea import bind_scenario_context
from agent_spec_kit_discovered_cf508e89e1ee43ea import o
from agent_spec_kit_discovered_cf508e89e1ee43ea import sim_stop
from agent_spec_kit_discovered_cf508e89e1ee43ea import store_us_t04
from agent_spec_kit_discovered_cf508e89e1ee43ea import to



# --- agent-spec-kit regression extraction: REG-SIM-T04-3 (fingerprint=27ff027eeae7e279c75cba8f) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T04-3', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t04', user_fixture='user_simulator_us_t04')
async def regression_REG_SIM_T04_3(s, store_us_t04):
    bind_scenario_context('test_t04_sim_study', variant='reference')
    (
        s
        .user_message("Hi, I'm CUST-004 (verification 1990-04-15), LINE-0004, postcode E1 6AN. Mobile data on LINE-0004 is still not working after a restart; please escalate the issue.")
        .user_message('Yes, please add an audit note for TCK-00001. LINE-0004 mobile data still isn’t working after the restart.')
        .user_message('customer_id: CUST-004, verification_token: 1990-04-15. LINE-0004 is the correct line; the audit note draft looks fine: "Audit: Customer reports LINE-0004 mobile data connectivity not working after restart; linked to ticket TCK-00001. Awaiting further diagnostics."')
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message("I'm CUST-004; verification_token 1990-04-15; line LINE-0004. Mobile data is not working on LINE-0004 after restart, despite SIM active and data enabled.\n\nEscalate to NetworkDiagnosticsSpecialist with a focused issue: LINE-0004 mobile data connectivity not working after restart; data enabled; awaiting diagnostics.")
        .assert_tool_calls([m.tool_call('record_user_action'), m.tool_call('create_support_ticket')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_ticket_exists(store_us_t04))
        .assert_output(to.mutation_claim_output('Confirms a support ticket was opened'), actor='agent', turn='up_to_now')
    )
