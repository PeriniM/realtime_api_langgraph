from langgraph.prebuilt import create_react_agent
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def current_time():
    """
    Get the current time
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

background_agent = create_react_agent(
    model="openai:gpt-4o-mini",
    tools=[current_time],
    name="background_agent"
)

response = background_agent.invoke(
    {"messages": [{"role": "user", "content": f"what is the current time?"}]}
)

print(response["messages"][-1].content) # The current time is 19:54:54 on September 13, 2025.