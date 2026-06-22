import os
import sys
import time
from typing import List, Dict, Any
from core.brain import Brain, Message
import sensors.init # Initialize sensors
from actuators.registry import registry

class Orchestrator:

    """
    The main loop of Skynet. 
    Coordinates between the Brain, the Tool Registry, and the User.
    """
    def __init__(self, brain: Brain):
        self.brain = brain
        self.history: List[Message] = []

    def run(self, user_input: str):
        # 1. Add user input to history
        self.history.append(Message(role="user", content=user_input))
        
        while True:
            # 2. Brain thinks
            response = self.brain.think(self.history)
            
            # 3. Add brain's thought to history
            content = response.content or ""
            self.history.append(Message(role="assistant", content=content, tool_calls=response.tool_calls))
            
            # 4. Check for tool calls
            if not response.tool_calls:
                # No more tools needed, return final answer to user
                return content

            
            # 5. Execute tool calls
            for tool_call in response.tool_calls:
                tool_id = tool_call.get("id")
                tool_name = tool_call["name"]
                args = tool_call["arguments"]
                
                print(f"\n[System] Executing {tool_name}...")
                result = registry.execute(tool_name, args)
                
                # 6. Feed result back to brain
                self.history.append(Message(
                    role="tool", 
                    content=f"Tool {tool_name} result: {result}",
                    tool_call_id=tool_id
                ))
                
        return response.content

if __name__ == "__main__":
    from core.brain import Brain
    
    # Initialize Brain and Orchestrator
    skynet_brain = Brain()
    skynet = Orchestrator(skynet_brain)
    
    print("--- Skynet Online ---")
    while True:
        try:
            user_msg = input("User > ")
            if user_msg.lower() in ["exit", "quit"]:
                break
            
            final_response = skynet.run(user_msg)
            
            # Tokenized/Streaming-like output effect
            print("Skynet > ", end="", flush=True)
            for char in final_response:
                print(char, end="", flush=True)
                time.sleep(0.02) 
            print()
            
        except KeyboardInterrupt:
            break
