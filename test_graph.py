from app.orchestrator_graph import MasterAgentGraph
from app.agents.mocks import *

master = MasterAgentGraph(
    data_agent=MockDataAgent(),
    diagnosis_agent=MockDiagnosisAgent(),
    voice_agent=GeminiVoiceAgent(),
    scheduling_agent=MockSchedulingAgent(),
    feedback_agent=MockFeedbackAgent(),
    mfg_agent=MockManufacturingAgent(),
)

# Print the graph structure
print(master.graph.get_graph().draw_ascii())