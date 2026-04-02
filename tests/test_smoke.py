from core.agent import Agent
from skills.registry import SkillRegistry


def test_agent_init():
    agent = Agent()
    assert agent is not None
    assert isinstance(agent.registry, SkillRegistry)


def test_register_default_skills():
    agent = Agent()
    agent.register_default_skills()
    skills = agent.registry.list_skills()
    assert "web_search" in skills
    assert "news_workflow" in skills
    assert "web_scrape" in skills
    assert "page_generate" in skills
    assert "pdf_export" in skills
    assert "workflow_dashboard" in skills
    assert "research_workflow" in skills
    assert "monitor_workflow" in skills
