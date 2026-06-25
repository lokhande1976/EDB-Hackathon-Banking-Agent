"""Playwright E2E tests for the Lloyds Bank AI Assistant.

Covers: page load, quick chips, Mode B/C/A agent flows, typing indicator,
conversation reset, mobile viewport, and input state during streaming.

Defaults to the live Mumbai Cloud Run service. Override with:
    TEST_BASE_URL=https://agent-service-577303767450.us-central1.run.app/ui \
    pytest tests/test_playwright.py -v

Install once:
    uv run playwright install chromium
"""

import os
import allure
import pytest
from playwright.sync_api import Page, expect

_DEFAULT_URL = "https://agent-service-577303767450.asia-south1.run.app/ui"


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("TEST_BASE_URL", _DEFAULT_URL).rstrip("/")


# ── Core helper ────────────────────────────────────────────────────────────

def send_and_wait(page: Page, message: str, timeout_ms: int = 90_000) -> str:
    """Fill input, click send, wait for the bot to finish streaming, return bot text."""
    with allure.step(f"Type message: {message[:60]}"):
        page.locator(".chat-input").fill(message)
    with allure.step("Click send"):
        page.locator(".send-btn").click()
    with allure.step("Wait for agent to start thinking"):
        page.locator(".status-pill.status-busy").wait_for(timeout=10_000)
    with allure.step("Wait for agent to finish responding"):
        page.locator(".status-pill.status-on").wait_for(timeout=timeout_ms)
    reply = page.locator(".msg-bubble--bot").last.inner_text()
    allure.attach(reply, name="agent_reply", attachment_type=allure.attachment_type.TEXT)
    return reply


# ── Page load ──────────────────────────────────────────────────────────────

@allure.feature("Chat UI")
@allure.story("Page Load")
@allure.title("Welcome screen elements are visible on first load")
@allure.severity(allure.severity_level.BLOCKER)
def test_welcome_screen_elements_visible(page: Page, base_url: str):
    with allure.step("Navigate to app"):
        page.goto(base_url)
    with allure.step("Assert logo is visible"):
        expect(page.locator(".lloyds-badge").first).to_be_visible()
    with allure.step("Assert welcome title is correct"):
        expect(page.locator(".welcome-title")).to_contain_text("Lloyds Bank AI assistant")
    with allure.step("Assert welcome subtitle is present"):
        expect(page.locator(".welcome-sub")).to_be_visible()
    with allure.step("Assert chat input and send button exist"):
        expect(page.locator(".chat-input")).to_be_visible()
        expect(page.locator(".send-btn")).to_be_visible()
    with allure.step("Assert 6 quick-action chips are rendered"):
        expect(page.locator(".qa-chip")).to_have_count(6)


@allure.feature("Chat UI")
@allure.story("Page Load")
@allure.title("Status indicator shows Online on initial load")
@allure.severity(allure.severity_level.NORMAL)
def test_initial_status_is_online(page: Page, base_url: str):
    page.goto(base_url)
    expect(page.locator(".status-pill.status-on")).to_be_visible()
    expect(page.locator(".status-pill")).to_contain_text("Online")


@allure.feature("Chat UI")
@allure.story("Page Load")
@allure.title("Footer disclaimer is visible")
@allure.severity(allure.severity_level.MINOR)
def test_footer_disclaimer_visible(page: Page, base_url: str):
    page.goto(base_url)
    expect(page.locator(".input-hint")).to_contain_text("not financial advice")


# ── Quick action chips ─────────────────────────────────────────────────────

@allure.feature("Chat UI")
@allure.story("Quick Actions")
@allure.title("Savings chip sends query, hides all chips, and receives a reply")
@allure.severity(allure.severity_level.CRITICAL)
def test_savings_chip_sends_query_and_hides_chips(page: Page, base_url: str):
    page.goto(base_url)
    with allure.step("Click 'Savings accounts' chip"):
        page.locator(".qa-chip", has_text="Savings accounts").click()
    with allure.step("User message appears immediately"):
        expect(page.locator(".msg-bubble--user").first).to_be_visible(timeout=5_000)
    with allure.step("Chips are hidden after first message"):
        expect(page.locator(".qa-chip")).to_have_count(0)
    with allure.step("Wait for bot reply"):
        page.locator(".status-pill.status-busy").wait_for(timeout=10_000)
        page.locator(".status-pill.status-on").wait_for(timeout=90_000)
    reply = page.locator(".msg-bubble--bot").last.inner_text()
    allure.attach(reply, name="savings_reply", attachment_type=allure.attachment_type.TEXT)
    assert len(reply) > 20


@allure.feature("Chat UI")
@allure.story("Quick Actions")
@allure.title("Investments chip returns investment-related reply")
@allure.severity(allure.severity_level.NORMAL)
def test_investments_chip_returns_investment_info(page: Page, base_url: str):
    page.goto(base_url)
    page.locator(".qa-chip", has_text="Investments").click()
    page.locator(".status-pill.status-busy").wait_for(timeout=10_000)
    page.locator(".status-pill.status-on").wait_for(timeout=90_000)
    reply = page.locator(".msg-bubble--bot").last.inner_text().lower()
    allure.attach(reply, name="investments_reply", attachment_type=allure.attachment_type.TEXT)
    assert any(k in reply for k in ["invest", "isa", "stocks", "shares", "fund"])


@allure.feature("Chat UI")
@allure.story("Quick Actions")
@allure.title("First home chip returns mortgage-related reply")
@allure.severity(allure.severity_level.NORMAL)
def test_first_home_chip_returns_mortgage_info(page: Page, base_url: str):
    page.goto(base_url)
    page.locator(".qa-chip", has_text="First home").click()
    page.locator(".status-pill.status-busy").wait_for(timeout=10_000)
    page.locator(".status-pill.status-on").wait_for(timeout=90_000)
    reply = page.locator(".msg-bubble--bot").last.inner_text().lower()
    allure.attach(reply, name="mortgage_reply", attachment_type=allure.attachment_type.TEXT)
    assert any(k in reply for k in ["mortgage", "home", "property", "%", "buyer"])


# ── Agent mode tests ───────────────────────────────────────────────────────

@allure.feature("Chat UI")
@allure.story("Mode C — Generic Query")
@allure.title("Generic market question answered directly without customer ID prompt")
@allure.severity(allure.severity_level.CRITICAL)
def test_mode_c_generic_query_answers_without_asking_for_id(page: Page, base_url: str):
    page.goto(base_url)
    reply = send_and_wait(page, "What is the FTSE 100 index?")
    assert len(reply) > 20
    low = reply.lower()
    assert not ("customer id" in low and "to access" in low), (
        f"Agent incorrectly asked for customer ID on a generic query: {reply[:400]}"
    )


@allure.feature("Chat UI")
@allure.story("Mode C — Generic Query")
@allure.title("Generic Lloyds product question returns product names")
@allure.severity(allure.severity_level.NORMAL)
def test_mode_c_lloyds_product_info_no_id_required(page: Page, base_url: str):
    page.goto(base_url)
    reply = send_and_wait(page, "What savings accounts does Lloyds Bank offer?")
    low = reply.lower()
    assert any(k in low for k in ["saver", "isa", "savings", "account", "lloyds"])


@allure.feature("Chat UI")
@allure.story("Mode B — Personal Query Without ID")
@allure.title("Wellbeing query without customer ID triggers ID request")
@allure.severity(allure.severity_level.CRITICAL)
def test_mode_b_personal_query_without_id_prompts_for_it(page: Page, base_url: str):
    page.goto(base_url)
    reply = send_and_wait(page, "Can you check my financial wellbeing?")
    low = reply.lower()
    assert any(k in low for k in ["customer id", "customer number", "your id", "what is your"]), (
        f"Expected customer ID prompt. Got: {reply[:400]}"
    )


@allure.feature("Chat UI")
@allure.story("Mode B — Personal Query Without ID")
@allure.title("Spending query without customer ID triggers ID request")
@allure.severity(allure.severity_level.NORMAL)
def test_mode_b_spending_query_without_id_prompts_for_it(page: Page, base_url: str):
    page.goto(base_url)
    reply = send_and_wait(page, "Review my recent spending please")
    low = reply.lower()
    assert any(k in low for k in ["customer id", "customer number", "id", "who you are"])


@allure.feature("Chat UI")
@allure.story("Mode A — Authenticated Flow")
@allure.title("Customer ID C001 returns personalised account data")
@allure.severity(allure.severity_level.CRITICAL)
def test_mode_a_with_customer_id_returns_account_data(page: Page, base_url: str):
    page.goto(base_url)
    reply = send_and_wait(
        page,
        "My customer ID is C001. Please give me a summary of my accounts.",
        timeout_ms=120_000,
    )
    assert len(reply) > 50
    low = reply.lower()
    assert any(k in low for k in ["£", "account", "balance", "savings", "current"])


@allure.feature("Chat UI")
@allure.story("Mode A — Authenticated Flow")
@allure.title("Follow-up question in same session stays in Mode A")
@allure.severity(allure.severity_level.NORMAL)
def test_mode_a_followup_after_customer_id(page: Page, base_url: str):
    page.goto(base_url)
    with allure.step("Send first message with customer ID"):
        send_and_wait(page, "My customer ID is C001.", timeout_ms=60_000)
    with allure.step("Send follow-up without repeating customer ID"):
        reply = send_and_wait(page, "What are my savings account balances?", timeout_ms=90_000)
    low = reply.lower()
    assert any(k in low for k in ["£", "account", "balance", "saver"])


# ── Conversation UX ────────────────────────────────────────────────────────

@allure.feature("Chat UI")
@allure.story("Conversation UX")
@allure.title("Typing indicator appears while bot streams then disappears")
@allure.severity(allure.severity_level.NORMAL)
def test_typing_indicator_visible_then_hidden(page: Page, base_url: str):
    page.goto(base_url)
    page.locator(".chat-input").fill("What is the Bank of England base rate?")
    page.locator(".send-btn").click()
    with allure.step("Typing bubble must appear"):
        expect(page.locator(".typing-bubble")).to_be_visible(timeout=10_000)
    with allure.step("Typing bubble disappears when done"):
        expect(page.locator(".typing-bubble")).to_be_hidden(timeout=90_000)


@allure.feature("Chat UI")
@allure.story("Conversation UX")
@allure.title("User message bubble appears instantly before bot replies")
@allure.severity(allure.severity_level.NORMAL)
def test_user_message_appears_immediately_before_bot_reply(page: Page, base_url: str):
    page.goto(base_url)
    msg = "Tell me about Lloyds credit cards"
    page.locator(".chat-input").fill(msg)
    page.locator(".send-btn").click()
    expect(page.locator(".msg-bubble--user").first).to_contain_text(msg, timeout=2_000)


@allure.feature("Chat UI")
@allure.story("Conversation UX")
@allure.title("Input and send button disabled while bot is streaming")
@allure.severity(allure.severity_level.NORMAL)
def test_input_and_send_disabled_during_streaming(page: Page, base_url: str):
    page.goto(base_url)
    page.locator(".chat-input").fill("What is FTSE 100?")
    page.locator(".send-btn").click()
    with allure.step("Input is disabled during streaming"):
        expect(page.locator(".chat-input")).to_be_disabled(timeout=5_000)
    with allure.step("Send button is disabled during streaming"):
        expect(page.locator(".send-btn")).to_be_disabled(timeout=5_000)
    page.locator(".status-pill.status-on").wait_for(timeout=90_000)
    with allure.step("Input re-enables after response"):
        expect(page.locator(".chat-input")).to_be_enabled()


@allure.feature("Chat UI")
@allure.story("Conversation UX")
@allure.title("New Chat button resets conversation to welcome screen")
@allure.severity(allure.severity_level.NORMAL)
def test_new_chat_button_appears_and_resets_to_welcome(page: Page, base_url: str):
    page.goto(base_url)
    with allure.step("New Chat button is hidden before any message"):
        expect(page.locator(".btn-new-chat")).to_be_hidden()
    with allure.step("Send a message to enter chat mode"):
        send_and_wait(page, "What is a cash ISA?")
    with allure.step("New Chat button appears after first message"):
        expect(page.locator(".btn-new-chat")).to_be_visible()
    with allure.step("Click New Chat"):
        page.locator(".btn-new-chat").click()
    with allure.step("Welcome screen returns"):
        expect(page.locator(".welcome-title")).to_be_visible()
        expect(page.locator(".qa-chip")).to_have_count(6)
        expect(page.locator(".btn-new-chat")).to_be_hidden()


@allure.feature("Chat UI")
@allure.story("Conversation UX")
@allure.title("Status pill transitions Online → Thinking → Online")
@allure.severity(allure.severity_level.NORMAL)
def test_status_transitions_busy_then_online(page: Page, base_url: str):
    page.goto(base_url)
    with allure.step("Initial status is Online"):
        expect(page.locator(".status-pill")).to_contain_text("Online")
    page.locator(".chat-input").fill("What is FTSE 100?")
    page.locator(".send-btn").click()
    with allure.step("Status becomes Thinking while streaming"):
        expect(page.locator(".status-pill")).to_contain_text("Thinking", timeout=10_000)
    with allure.step("Status returns to Online when done"):
        page.locator(".status-pill.status-on").wait_for(timeout=90_000)
        expect(page.locator(".status-pill")).to_contain_text("Online")


# ── Mobile viewport ────────────────────────────────────────────────────────

@allure.feature("Chat UI")
@allure.story("Mobile")
@allure.title("iPhone 14 viewport: input is visible and in the lower half of screen")
@allure.severity(allure.severity_level.CRITICAL)
def test_mobile_input_visible_and_positioned_at_bottom(page: Page, base_url: str):
    with allure.step("Set iPhone 14 viewport (390×844)"):
        page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url)
    input_box = page.locator(".chat-input")
    with allure.step("Input is visible"):
        expect(input_box).to_be_visible()
    with allure.step("Input is positioned in the lower half of the screen"):
        box = input_box.bounding_box()
        assert box is not None
        allure.attach(
            f"Input y={box['y']:.0f}, height={box['height']:.0f}, viewport=844px",
            name="input_position",
            attachment_type=allure.attachment_type.TEXT,
        )
        assert box["y"] > 422, (
            f"Input top at y={box['y']:.0f} — expected below midpoint (422px). CSS viewport bug?"
        )


@allure.feature("Chat UI")
@allure.story("Mobile")
@allure.title("Full chat flow works on mobile viewport")
@allure.severity(allure.severity_level.CRITICAL)
def test_mobile_full_chat_flow(page: Page, base_url: str):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url)
    reply = send_and_wait(page, "What is Lloyds Club Monthly Saver?")
    assert len(reply) > 20


@allure.feature("Chat UI")
@allure.story("Mobile")
@allure.title("All 6 quick chips are present on mobile (horizontal scroll)")
@allure.severity(allure.severity_level.NORMAL)
def test_mobile_quick_chips_scrollable(page: Page, base_url: str):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url)
    expect(page.locator(".qa-chip")).to_have_count(6)
