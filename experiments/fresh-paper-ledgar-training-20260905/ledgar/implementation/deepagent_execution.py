"""Fixed, isolated DeepAgent execution of the supplied English SOP request."""
from __future__ import annotations

import json
from functools import lru_cache


@lru_cache(maxsize=8)
def build_agent(model: str, system: str, seed: int, labels: tuple[str, ...],
                num_ctx: int, num_predict: int, keep_alive: int):
    from deepagents import (GeneralPurposeSubagentProfile, HarnessProfile,
                            create_deep_agent, register_harness_profile)
    from langchain_ollama import ChatOllama

    # The complete SOP and single input are supplied directly by the fixed
    # harness. No filesystem, planning, shell, network, or delegation tool is
    # needed to execute this task. This profile is identical for both arms.
    register_harness_profile('ollama', HarnessProfile(
        base_system_prompt='Follow the supplied workflow SOP on the supplied input.',
        excluded_tools=frozenset({'write_todos', 'read_file', 'ls', 'glob', 'grep',
                                  'write_file', 'edit_file', 'delete', 'execute', 'task'}),
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ))
    schema = {'type': 'object', 'properties': {'label': {'type': 'string', 'enum': list(labels)}},
              'required': ['label'], 'additionalProperties': False}
    llm = ChatOllama(model=model, base_url='http://127.0.0.1:11434',
                     temperature=0, reasoning=False, seed=seed, num_ctx=num_ctx,
                     num_predict=num_predict, keep_alive=keep_alive, format=schema,
                     disable_streaming=True, client_kwargs={'timeout': 300})
    return create_deep_agent(model=llm, system_prompt=system, tools=[],
                             checkpointer=False, name='pland-fixed-english-sop')


def invoke(model, system, prompt, seed, labels, num_ctx, num_predict, keep_alive):
    agent = build_agent(model, system, seed, tuple(labels), num_ctx, num_predict, keep_alive)
    result = agent.invoke({'messages': [{'role': 'user', 'content': prompt}]},
                          config={'recursion_limit': 8})
    messages = [m for m in result['messages'] if m.type == 'ai']
    content = messages[-1].content
    usage = [m.usage_metadata or {} for m in messages]
    trace = [{'type': m.type, 'content': m.content,
              'tool_calls': getattr(m, 'tool_calls', []),
              'usage_metadata': getattr(m, 'usage_metadata', None),
              'response_metadata': getattr(m, 'response_metadata', None)}
             for m in result['messages'] if m.type != 'human']
    raw = {'message': {'content': content},
           'prompt_eval_count': sum(u.get('input_tokens', 0) for u in usage),
           'eval_count': sum(u.get('output_tokens', 0) for u in usage),
           'model_calls': len(messages), 'deepagent_trace': trace,
           'done_reason': messages[-1].response_metadata.get('done_reason')}
    for key in ('load_duration', 'prompt_eval_duration', 'eval_duration'):
        raw[key] = sum(m.response_metadata.get(key, 0) for m in messages)
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        value = {}
    return value if isinstance(value, dict) else {}, raw
