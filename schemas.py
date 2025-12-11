PLANNER_JSON_SCHEMA_HINT = """{
  "clarification": {
    "needed": false,
    "question": ""
  },
  "user_prompt_summary": "",
  "plan": [],
  "plan_position": 0,
  "prompts_for_executor": [""],
  "project_infos": [],
  "summaries": {
    "chat_summary": "",
    "project_summary": "",
    "project_keywords": []
  },
  "user_message": ""
}"""


EXECUTOR_JSON_SCHEMA_HINT = """{
  "picked_prompt": "",
  "fast_infos": false,
  "fast_tool": "",
  "fast_args": {},
  "actions": [
    {
      "tool_name": "",
      "args": {}
    }
  ],
  "new_tools": [
    {
      "nameTool": "",
      "beschreib": "",
      "args": "",
      "ergebniss": "",
      "python_code": ""
    }
  ],
  "tests": [
    {
      "tool_name": "",
      "test_code": ""
    }
  ],
  "execution_notes": "",
  "next_prompt": ""
}"""


VALIDATOR_JSON_SCHEMA_HINT = """{
  "approved": false,
  "reason": "",
  "fix_prompt": ""
}"""
