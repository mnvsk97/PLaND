"""Fixed, isolated DeepAgent execution of the supplied English SOP request."""
from __future__ import annotations

import json
from functools import lru_cache
from threading import Lock

_PROFILE_LOCK = Lock()


@lru_cache(maxsize=8)
def build_agent(model: str, system: str, labels: tuple[str, ...], hosted_config):
    from deepagents import (GeneralPurposeSubagentProfile, HarnessProfile,
                            create_deep_agent, register_harness_profile)

    # The complete SOP and single input are supplied directly by the fixed
    # harness. No filesystem, planning, shell, network, or delegation tool is
    # needed to execute this task. This profile is identical for both arms.
    profile = HarnessProfile(
        base_system_prompt='Follow the supplied workflow SOP on the supplied input.',
        excluded_tools=frozenset({'write_todos', 'read_file', 'ls', 'glob', 'grep',
                                  'write_file', 'edit_file', 'delete', 'execute', 'task'}),
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    )
    from hosted_execution import MODEL, build_model
    if model != MODEL:
        raise ValueError('model configuration does not match the requested model')
    llm = build_model(hosted_config, labels)
    from deepagents._models import get_model_provider
    profile_key = f'{get_model_provider(llm)}:{model}'
    with _PROFILE_LOCK:
        register_harness_profile(profile_key, profile)
    return create_deep_agent(model=llm, system_prompt=system, tools=[],
                             checkpointer=False, name='pland-fixed-english-sop')


def invoke(model, system, prompt, labels, hosted_config):
    agent = build_agent(model, system, tuple(labels), hosted_config)
    result = agent.invoke({'messages': [{'role': 'user', 'content': prompt}]},
                          config={'recursion_limit': 8})
    messages = [m for m in result['messages'] if m.type == 'ai']
    if not messages:
        raise ValueError('DeepAgent returned no model message')
    content = messages[-1].content
    usage = [m.usage_metadata or {} for m in messages]
    trace = [{'type': m.type, 'content': m.content,
              'tool_calls': getattr(m, 'tool_calls', []),
              'usage_metadata': getattr(m, 'usage_metadata', None),
              'response_metadata': getattr(m, 'response_metadata', None)}
             for m in result['messages'] if m.type != 'human']
    for entry, message in zip(trace, [m for m in result['messages'] if m.type != 'human'], strict=True):
        entry['reasoning_details'] = message.additional_kwargs.get('reasoning_details')
    raw = {'message': {'content': content},
           'prompt_eval_count': sum(u.get('input_tokens', 0) for u in usage),
           'eval_count': sum(u.get('output_tokens', 0) for u in usage),
           'model_calls': len(messages), 'deepagent_trace': trace,
           'done_reason': messages[-1].response_metadata.get('done_reason')}
    from hosted_execution import normalize_messages
    raw.update(normalize_messages(messages))
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        value = {}
    if not isinstance(value, dict) or set(value) != {'label'} or raw.get('refusal'):
        value = {}
    return value if isinstance(value, dict) else {}, raw
