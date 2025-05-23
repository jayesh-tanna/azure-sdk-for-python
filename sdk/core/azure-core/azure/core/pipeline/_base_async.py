# --------------------------------------------------------------------------
#
# Copyright (c) Microsoft Corporation. All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the ""Software""), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
# --------------------------------------------------------------------------
from __future__ import annotations
from types import TracebackType
from typing import (
    Any,
    Union,
    Generic,
    TypeVar,
    List,
    Dict,
    Optional,
    Iterable,
    Type,
    AsyncContextManager,
)

from azure.core.pipeline import PipelineRequest, PipelineResponse, PipelineContext
from azure.core.pipeline.policies import AsyncHTTPPolicy, SansIOHTTPPolicy
from ._tools_async import await_result as _await_result
from ._base import cleanup_kwargs_for_transport
from .transport import AsyncHttpTransport

AsyncHTTPResponseType = TypeVar("AsyncHTTPResponseType")
HTTPRequestType = TypeVar("HTTPRequestType")


class _SansIOAsyncHTTPPolicyRunner(AsyncHTTPPolicy[HTTPRequestType, AsyncHTTPResponseType]):
    """Async implementation of the SansIO policy.

    Modifies the request and sends to the next policy in the chain.

    :param policy: A SansIO policy.
    :type policy: ~azure.core.pipeline.policies.SansIOHTTPPolicy
    """

    def __init__(self, policy: SansIOHTTPPolicy[HTTPRequestType, AsyncHTTPResponseType]) -> None:
        super(_SansIOAsyncHTTPPolicyRunner, self).__init__()
        self._policy = policy

    async def send(
        self, request: PipelineRequest[HTTPRequestType]
    ) -> PipelineResponse[HTTPRequestType, AsyncHTTPResponseType]:
        """Modifies the request and sends to the next policy in the chain.

        :param request: The PipelineRequest object.
        :type request: ~azure.core.pipeline.PipelineRequest
        :return: The PipelineResponse object.
        :rtype: ~azure.core.pipeline.PipelineResponse
        """
        await _await_result(self._policy.on_request, request)
        response: PipelineResponse[HTTPRequestType, AsyncHTTPResponseType]
        try:
            response = await self.next.send(request)
        except Exception:
            await _await_result(self._policy.on_exception, request)
            raise
        await _await_result(self._policy.on_response, request, response)
        return response


class _AsyncTransportRunner(AsyncHTTPPolicy[HTTPRequestType, AsyncHTTPResponseType]):
    """Async Transport runner.

    Uses specified HTTP transport type to send request and returns response.

    :param sender: The async Http Transport instance.
    :type sender: ~azure.core.pipeline.transport.AsyncHttpTransport
    """

    def __init__(self, sender: AsyncHttpTransport[HTTPRequestType, AsyncHTTPResponseType]) -> None:
        super(_AsyncTransportRunner, self).__init__()
        self._sender = sender

    async def send(
        self, request: PipelineRequest[HTTPRequestType]
    ) -> PipelineResponse[HTTPRequestType, AsyncHTTPResponseType]:
        """Async HTTP transport send method.

        :param request: The PipelineRequest object.
        :type request: ~azure.core.pipeline.PipelineRequest
        :return: The PipelineResponse object.
        :rtype: ~azure.core.pipeline.PipelineResponse
        """
        cleanup_kwargs_for_transport(request.context.options)
        return PipelineResponse(
            request.http_request,
            await self._sender.send(request.http_request, **request.context.options),
            request.context,
        )


class AsyncPipeline(
    AsyncContextManager["AsyncPipeline"],
    Generic[HTTPRequestType, AsyncHTTPResponseType],
):
    """Async pipeline implementation.

    This is implemented as a context manager, that will activate the context
    of the HTTP sender.

    :param transport: The async Http Transport instance.
    :type transport: ~azure.core.pipeline.transport.AsyncHttpTransport
    :param list policies: List of configured policies.

    .. admonition:: Example:

        .. literalinclude:: ../samples/test_example_async.py
            :start-after: [START build_async_pipeline]
            :end-before: [END build_async_pipeline]
            :language: python
            :dedent: 4
            :caption: Builds the async pipeline for asynchronous transport.
    """

    def __init__(
        self,
        transport: AsyncHttpTransport[HTTPRequestType, AsyncHTTPResponseType],
        policies: Optional[
            Iterable[
                Union[
                    AsyncHTTPPolicy[HTTPRequestType, AsyncHTTPResponseType],
                    SansIOHTTPPolicy[HTTPRequestType, AsyncHTTPResponseType],
                ]
            ]
        ] = None,
    ) -> None:
        self._impl_policies: List[AsyncHTTPPolicy[HTTPRequestType, AsyncHTTPResponseType]] = []
        self._transport = transport

        for policy in policies or []:
            if isinstance(policy, SansIOHTTPPolicy):
                self._impl_policies.append(_SansIOAsyncHTTPPolicyRunner(policy))
            elif policy:
                self._impl_policies.append(policy)
        for index in range(len(self._impl_policies) - 1):
            self._impl_policies[index].next = self._impl_policies[index + 1]
        if self._impl_policies:
            self._impl_policies[-1].next = _AsyncTransportRunner(self._transport)

    async def __aenter__(self) -> AsyncPipeline[HTTPRequestType, AsyncHTTPResponseType]:
        await self._transport.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> None:
        await self._transport.__aexit__(exc_type, exc_value, traceback)

    async def _prepare_multipart_mixed_request(self, request: HTTPRequestType) -> None:
        """Will execute the multipart policies.

        Does nothing if "set_multipart_mixed" was never called.

        :param request: The HTTP request object.
        :type request: ~azure.core.rest.HttpRequest
        """
        multipart_mixed_info = request.multipart_mixed_info  # type: ignore
        if not multipart_mixed_info:
            return

        requests: List[HTTPRequestType] = multipart_mixed_info[0]
        policies: List[SansIOHTTPPolicy] = multipart_mixed_info[1]
        pipeline_options: Dict[str, Any] = multipart_mixed_info[3]

        async def prepare_requests(req):
            if req.multipart_mixed_info:
                # Recursively update changeset "sub requests"
                await self._prepare_multipart_mixed_request(req)
            context = PipelineContext(None, **pipeline_options)
            pipeline_request = PipelineRequest(req, context)
            for policy in policies:
                await _await_result(policy.on_request, pipeline_request)

        # Not happy to make this code asyncio specific, but that's multipart only for now
        # If we need trio and multipart, let's reinvesitgate that later
        import asyncio  # pylint: disable=do-not-import-asyncio

        await asyncio.gather(*[prepare_requests(req) for req in requests])

    async def _prepare_multipart(self, request: HTTPRequestType) -> None:
        # This code is fine as long as HTTPRequestType is actually
        # azure.core.pipeline.transport.HTTPRequest, bu we don't check it in here
        # since we didn't see (yet) pipeline usage where it's not this actual instance
        # class used
        await self._prepare_multipart_mixed_request(request)
        request.prepare_multipart_body()  # type: ignore

    async def run(
        self, request: HTTPRequestType, **kwargs: Any
    ) -> PipelineResponse[HTTPRequestType, AsyncHTTPResponseType]:
        """Runs the HTTP Request through the chained policies.

        :param request: The HTTP request object.
        :type request: ~azure.core.pipeline.transport.HttpRequest
        :return: The PipelineResponse object.
        :rtype: ~azure.core.pipeline.PipelineResponse
        """
        await self._prepare_multipart(request)
        context = PipelineContext(self._transport, **kwargs)
        pipeline_request = PipelineRequest(request, context)
        first_node = self._impl_policies[0] if self._impl_policies else _AsyncTransportRunner(self._transport)
        return await first_node.send(pipeline_request)
