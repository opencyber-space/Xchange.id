import os
from typing import Any, Dict, Optional, Set

from .agents_functions import AgentFunctions


class FunctionCaller:
    def __init__(
        self,
        *,
        executor_id: str,
        unique_parameter: str,
        num_workers: int = 8,
        functions_registry_url: Optional[str] = None,
    ):
        registry_url = functions_registry_url or os.environ["FUNCTION_REGISTRY_URL"]

        self._agent_functions = AgentFunctions(
            functions_registry_url=registry_url,
            unique_parameter=unique_parameter,
            executor_id=executor_id,
            num_workers=num_workers,
        )
        self._added_functions: Set[str] = set()

    def _ensure_added(self, function_id: str) -> None:
        if function_id not in self._added_functions:
            self._agent_functions.add(function_id)
            self._added_functions.add(function_id)

    def call(self, function_id: str, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._ensure_added(function_id)
        return self._agent_functions.call(function_id=function_id, input_data=input_data, **kwargs)

    def shutdown(self, wait: bool = True) -> None:
        self._agent_functions.shutdown(wait=wait)
