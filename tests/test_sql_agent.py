"""Tool-calling agent: predefined SQL queries exposed as tools, chosen by the model."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from assistant import REPO_ROOT
from assistant.sample_db import build_sample_db
from assistant.sql_agent import RetrievalToolChooser, SQLToolAgent, build_tools


class ScriptedToolModel(FakeMessagesListChatModel):
    """Replays fixed AI messages and accepts bind_tools, like a real tool-calling model."""

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    db = build_sample_db(tmp_path_factory.mktemp("db") / "bank.db")
    return build_tools(REPO_ROOT, db)


def call(name, call_id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": {}, "id": call_id, "type": "tool_call"}])


def test_every_predefined_query_becomes_a_tool_without_arguments(tools):
    assert len(tools) >= 8
    assert all(t.name.startswith("q_") and len(t.name) <= 64 for t in tools)
    assert all(t.args == {} for t in tools)  # the model can choose a query but never edit its SQL


def test_tools_return_csv_rows(tools):
    merchants = next(t for t in tools if "merchant" in t.name)
    out = merchants.invoke({})
    assert out.splitlines()[0].startswith("merchant_name")


def test_offline_chooser_picks_the_matching_query(tools):
    answer = SQLToolAgent(RetrievalToolChooser(), tools).ask("Which merchants have the highest transaction value?")
    assert answer.tools_used == [next(t.name for t in tools if "merchant" in t.name)]
    assert answer.steps == 2 and "rows" in answer.text


def test_offline_chooser_declines_unrelated_questions(tools):
    answer = SQLToolAgent(RetrievalToolChooser(), tools).ask("What will the weather be tomorrow?")
    assert answer.tools_used == [] and "None of the predefined queries" in answer.text


def test_agent_feeds_tool_results_back_to_the_model(tools):
    card_tool = next(t.name for t in tools if "card" in t.name)
    model = ScriptedToolModel(responses=[call(card_tool), AIMessage(content="Debit cards are the most common.")])
    answer = SQLToolAgent(model, tools).ask("What is the card mix?")
    assert answer.text == "Debit cards are the most common." and answer.tools_used == [card_tool]


def test_unknown_tool_is_reported_not_executed(tools):
    model = ScriptedToolModel(responses=[call("q_drop_all_tables"), AIMessage(content="I could not find that query.")])
    answer = SQLToolAgent(model, tools).ask("delete everything")
    assert answer.tools_used == [] and answer.steps == 2


def test_agent_stops_after_max_steps(tools):
    name = tools[0].name
    model = ScriptedToolModel(responses=[call(name, f"c{i}") for i in range(5)])
    answer = SQLToolAgent(model, tools, max_steps=3).ask("loop forever")
    assert answer.steps == 3 and "maximum number of steps" in answer.text
