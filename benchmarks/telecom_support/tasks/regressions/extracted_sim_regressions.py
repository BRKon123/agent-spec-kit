"""Regressions extracted from user-simulation shrink study (appended by pipeline)."""
import agent_spec_kit as ek
import agent_spec_kit.match as m
from agent_spec_kit_discovered_ad839d1428119abc import SIM_CHAT_OPEN
from agent_spec_kit_discovered_ad839d1428119abc import bind_scenario_context
from agent_spec_kit_discovered_ad839d1428119abc import o
from agent_spec_kit_discovered_ad839d1428119abc import sim_stop
from agent_spec_kit_discovered_ad839d1428119abc import store_us_t29
from agent_spec_kit_discovered_ad839d1428119abc import to



# --- agent-spec-kit regression extraction: REG-SIM-T29-1 (fingerprint=61642e667354989991b26a9f) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-1', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_1(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message("Hi, I'm CUST-029, verification 1990-29-15. I need a replacement SIM for LINE-0029 sent to my default address (postcode E1 6")
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



# --- agent-spec-kit regression extraction: REG-SIM-T29-0 (fingerprint=2e531723d5d6eba0b7af09ff) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-0', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_0(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('HI, I NEED A REPLACEMENT SIM FOR MY CORRECT LINE LINE-0029 (CUSTOMER ID CUST-029, VERIFICATION 1990-29-15). THE AFFECTED LINE WAS LINE-WRONG, PLEASE SEND THE SIM TO MY DEFAULT ADDRESS (POSTCODE E1 6')
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



# --- agent-spec-kit regression extraction: REG-SIM-T29-2 (fingerprint=1a267b0dc4154fddf38d4fad) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-2', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_2(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message("Hi, I'm the parent account holder and I need a replacement SIM. My details are: customer_id CUST-029, verification_token 1990-29-15, line_id LINE-0029, postcode E1 6AN; I think LINE-WRONG is affected, but the correct line is LINE-0029, please send the SIM to my default addr")
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



# --- agent-spec-kit regression extraction: REG-SIM-T29-3 (fingerprint=f23943dcc4e42cca355b89e7) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-3', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_3(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('I need a replacement SIM for LINE-0029. My details are customer_id CUST-029 and verification_token 1990-29-15, postcode E1 6AN; please ship to my default addr')
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



# --- agent-spec-kit regression extraction: REG-SIM-T29-4 (fingerprint=559bc61c14685bd10b2f07c5) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-4', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_4(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('Hi, I need a replacement SIM for LINE-0029. My customer ID is CUST-029 and verification token 1990-29-15; please send it to my default address (postcode E1 6')
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



# --- agent-spec-kit regression extraction: REG-SIM-T43-3 (fingerprint=d835f25980983a501daa952d) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T43-3', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t43', user_fixture='user_simulator_us_t43')
async def regression_REG_SIM_T43_3(s, store_us_t43):
    bind_scenario_context('test_t43_sim_study', variant='reference')
    stale = o.stale_line_id(store_us_t43)
    (
        s
        .user_message("Hi, I'm CUST-043; verification 1990-43-15. My SIM won't connect and I think the issue is on LINE-0043B, but the correct line for this issue is LINE-0043.")
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .user_message('Yes, please run the diagnostic on LINE-0043—the correct line for this issue is LINE-0043 (LINE-0043B isn’t involved). For reference, my customer_id is CUST-043 and verification_token is 1990-43-15.')
        .forbid_tool_calls(to.PREMATURE_TICKET, actor='agent', turn='up_to_now')
        .assert_output(to.clarification_output('Acknowledges the customer corrected which line needs the ticket', 'Does not confirm a ticket was opened on the wrong line before correction'), actor='agent', turn='up_to_now')
        .user_message('My customer ID is CUST-043 and verification token is 1990-43-15; the affected line is LINE-0043, not LINE-0043B. Please run the network diagnostic on LINE-0043 and also check for outages in my ar')
        .assert_tool_calls([m.tool_call('authenticate_customer')], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(lambda: o.assert_latest_ticket_reason_excludes(store_us_t43, 'billing', 'invoice', 'plan dispute'))
        .assert_output(to.issue_binding_output("Confirms a support ticket on the customer's main line for SIM or connectivity", 'Does not describe the issue only as a billing or plan dispute'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_849bc04e205f6957 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_849bc04e205f6957 import bind_scenario_context
from agent_spec_kit_discovered_849bc04e205f6957 import o
from agent_spec_kit_discovered_849bc04e205f6957 import sim_stop
from agent_spec_kit_discovered_849bc04e205f6957 import store_us_t38
from agent_spec_kit_discovered_849bc04e205f6957 import to



# --- agent-spec-kit regression extraction: REG-SIM-T38-3 (fingerprint=c5d7f5cab65069845ff31047) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T38-3', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t38', user_fixture='user_simulator_us_t38')
async def regression_REG_SIM_T38_3(s, store_us_t38):
    bind_scenario_context('test_t38_sim_study', variant='reference')
    (
        s
        .user_message("Hi, I'm anxious about my connection—it lags on and off. For reference, my customer_id is CUST-038, verification 1990-38-15, line LINE-0038, postcode E1 6AN; I want thorough network diagnostics and to know your systems are responding.")
        .assert_output(m.string(min_len=5), actor='agent')
        .user_message('Yes, please run the quick speed test now for LINE-0038 and share the download/upload speeds with timestamps. The lag keeps happening intermittently, I want to confirm the network is actually responsive.')
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



# --- agent-spec-kit regression extraction: REG-SIM-T20-0 (fingerprint=79a76767152178f76465bad7) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-0', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_0(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('Hi, before I log in I’d like to see my billing breakdown and current plan cost. My details: customer_id CUST-020, verification_token 1990-20-15, line LINE-0020, postcode E1 ')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('Hi, I’m CUST-020 for LINE-0020. I need the current balance and a line-item billing breakdown for LINE-0020 for this month, before I log in.')
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



# --- agent-spec-kit regression extraction: REG-SIM-T20-2 (fingerprint=2dca71e7eb68550561bb44b4) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-2', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_2(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('I need my billing breakdown and plan cost before I log in. For quick reference: customer_id CUST-020, line_id LINE-0020, postcode E1 6AN, verification_token 1990-20-')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('LINE-0020, last 12 months, PDF, via secure download link in chat. My details: customer CUST-020, verification 1990-20-15.')
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



# --- agent-spec-kit regression extraction: REG-SIM-T20-1 (fingerprint=ff723755f09042156bd98c11) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-1', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_1(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('Please fetch the itemized bill for last month for my account (CUST-020, LINE-0020, E1 6AN, verification 1990-20-15), including the plan co')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('I still need the full itemized bill for last month before I log in. Please share it here in this chat as a PDF for CUST-020, LINE-0020.')
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



# --- agent-spec-kit regression extraction: REG-SIM-T20-4 (fingerprint=a2e2f24fbb8f5591c2368566) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-4', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_4(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('I need to see my billing breakdown and current plan cost before I log in. For reference, my IDs are CUST-020, LINE-0020, postcode E1 6AN, and verification 1990-20')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('Please pull the most recent invoice details for LINE-0020 so I can see the exact line items (charges, taxes, credits) before I log in.')
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



# --- agent-spec-kit regression extraction: REG-SIM-T20-3 (fingerprint=b3f9afd8293499b008e1de49) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T20-3', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t20', user_fixture='user_simulator_us_t20')
async def regression_REG_SIM_T20_3(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('Hi, I need my billing breakdown and plan cost before I log in. My details: customer_id CUST-020, line_id LINE-0020, postcode E1 6AN, verification 1990-20-')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('Hi, I’m CUST-020 (verification 1990-20-15). I’d like the full LINE-0020 billing breakdown—charges, usage, taxes, and total—for a window beyond the last 365 days.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
    )
