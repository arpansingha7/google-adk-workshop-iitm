"""Task 2 - SmartStudy: Multi-Agent Intelligent Study Planner (Google ADK).

Workflow
--------
SequentialAgent  smartstudy_pipeline
  1. coordinator_agent     extracts requirements        (sequential step)
  2. planning_agent        prepares requirements        (sequential step)
  3. ParallelAgent analysis_team
        topic_agent / practice_agent / schedule_agent   (parallel)
  4. LoopAgent review_loop (max_iterations=2)
        study_plan_writer -> review_agent               (loop)
"""

from google.adk.agents import Agent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext

MODEL = "gemini-flash-lite-latest"


# Review agent calls this to stop the loop early when the plan is approved.
def approve_plan(tool_context: ToolContext) -> dict:
    """Call ONLY when the study plan passes every review check; ends the loop."""
    tool_context.actions.escalate = True
    return {"status": "approved"}


# 1. Coordinator ---------------------------------------------------------
coordinator_agent = Agent(
    name="coordinator_agent",
    model=MODEL,
    description="Receives the student's request and extracts the requirements.",
    instruction=(
        "You are the Coordinator. Read the student's request and extract:\n"
        "- Subject\n- Exam date / days remaining\n- Topics (list)\n"
        "- Current level\n- Available study time per day\n"
        "Output them as a clean structured list. If something is missing, assume a "
        "sensible default and say so."
    ),
    output_key="requirements",
)

# 2. Planning agent ------------------------------------------------------
planning_agent = Agent(
    name="planning_agent",
    model=MODEL,
    description="Prepares requirements and hands them to the three analysis agents.",
    instruction=(
        "You are the Planning Agent. Using the requirements below, write a short "
        "planning brief (total study hours = days x hours/day, goals, constraints) "
        "that the Topic, Practice and Schedule agents will use.\n\n"
        "Requirements:\n{requirements}"
    ),
    output_key="planning_brief",
)

# 3-5. Parallel agents ---------------------------------------------------
topic_agent = Agent(
    name="topic_agent",
    model=MODEL,
    description="Analyzes each topic.",
    instruction=(
        "You are the Topic Agent. For EACH topic in the requirements, give:\n"
        "Priority (High/Medium/Low), Difficulty, Recommended study focus.\n"
        "Present as a table.\n\nRequirements:\n{requirements}\n\nBrief:\n{planning_brief}"
    ),
    output_key="topic_analysis",
)

practice_agent = Agent(
    name="practice_agent",
    model=MODEL,
    description="Decides practice volume and type per topic.",
    instruction=(
        "You are the Practice Agent. For EACH topic decide the number of problems "
        "(e.g. Arrays 5, Linked Lists 5, Trees 8, Graphs 8, Dynamic Programming 10) "
        "and the practice type: Concept Questions, Coding Problems, Mixed Practice or "
        "Mock Test.\n\nRequirements:\n{requirements}\n\nBrief:\n{planning_brief}"
    ),
    output_key="practice_plan",
)

schedule_agent = Agent(
    name="schedule_agent",
    model=MODEL,
    description="Builds a realistic day-wise time schedule.",
    instruction=(
        "You are the Schedule Agent. Convert the available study time into a realistic "
        "day-wise schedule for every day until the exam. Include revision and practice "
        "blocks, not only new topics, and keep each day within the daily hours. "
        "Reserve the last day for final prep.\n\n"
        "Requirements:\n{requirements}\n\nBrief:\n{planning_brief}"
    ),
    output_key="schedule",
)

analysis_team = ParallelAgent(
    name="analysis_team",
    description="Runs Topic, Practice and Schedule agents in parallel.",
    sub_agents=[topic_agent, practice_agent, schedule_agent],
)

# 6. Writer + 7. Reviewer (loop) -----------------------------------------
study_plan_writer = Agent(
    name="study_plan_writer",
    model=MODEL,
    description="Combines analysis into one complete study plan.",
    instruction=(
        "You are the Study Plan Writer. Combine the inputs into ONE complete day-wise "
        "study plan (Day 1..Day N). Each day lists: topics to study, practice to "
        "complete, revision, hours per block (total must equal the daily limit). "
        "End with mock test / final preparation on the last day.\n\n"
        "Topic analysis:\n{topic_analysis}\n\nPractice plan:\n{practice_plan}\n\n"
        "Schedule:\n{schedule}\n\n"
        "Reviewer feedback (empty on first pass; if present, fix every issue):\n"
        "{review_feedback?}\n\n"
        "Output only the full study plan."
    ),
    output_key="draft_plan",
)

review_agent = Agent(
    name="review_agent",
    model=MODEL,
    description="Reviews the draft plan and approves or requests improvements.",
    instruction=(
        "You are the Review Agent. Check the draft plan:\n"
        "1. Are all topics covered?\n2. Does it fit within the available study time each day?\n"
        "3. Is sufficient practice included?\n4. Is revision included?\n"
        "5. Is the final day suitable for exam preparation?\n\n"
        "If ALL pass: call the approve_plan tool, then output the plan exactly as the "
        "FINAL STUDY PLAN (10-day personalized plan, nicely formatted).\n"
        "If anything fails: list the specific fixes needed (do NOT call approve_plan).\n\n"
        "Draft plan:\n{draft_plan}"
    ),
    tools=[approve_plan],
    output_key="review_feedback",
)

review_loop = LoopAgent(
    name="review_loop",
    description="Writer -> Reviewer loop, maximum 2 iterations.",
    sub_agents=[study_plan_writer, review_agent],
    max_iterations=2,
)

# Sequential root --------------------------------------------------------
smartstudy_pipeline = SequentialAgent(
    name="smartstudy_pipeline",
    description="Coordinator -> Planning -> Parallel analysis -> Review loop.",
    sub_agents=[coordinator_agent, planning_agent, analysis_team, review_loop],
)

root_agent = smartstudy_pipeline
