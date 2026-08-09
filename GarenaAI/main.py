from __future__ import annotations

import asyncio
import logging
import os
import signal

import grpc
import uvicorn

try:
    from db import close_open_connections
    from generated import garena_pet_pb2_grpc as rpc
    from http_api import app as http_app
    from pet_grpc_service import GarenaPetGrpcService
except ImportError:  # Allows `python -m GarenaAI.main` from repo root.
    from GarenaAI.db import close_open_connections
    from GarenaAI.generated import garena_pet_pb2_grpc as rpc
    from GarenaAI.http_api import app as http_app
    from GarenaAI.pet_grpc_service import GarenaPetGrpcService

logger = logging.getLogger(__name__)
DEFAULT_BIND_ADDR = "127.0.0.1:50051"
DEFAULT_HTTP_BIND = "127.0.0.1:8001"


async def start_server(
    bind_addr: str | None = None,
    service: GarenaPetGrpcService | None = None,
) -> grpc.aio.Server:
    target = bind_addr or os.getenv("GARENA_PET_GRPC_BIND", DEFAULT_BIND_ADDR)
    server = grpc.aio.server()
    rpc.add_GarenaPetServiceServicer_to_server(service or GarenaPetGrpcService(), server)
    port = server.add_insecure_port(target)
    if port == 0:
        raise RuntimeError(f"could not bind Garena pet gRPC server to {target}")

    await server.start()
    logger.info("Garena pet gRPC server listening on %s", target)
    return server


def _split_host_port(bind_addr: str) -> tuple[str, int]:
    host, _, port = bind_addr.rpartition(":")
    return host or "127.0.0.1", int(port)


async def serve(bind_addr: str | None = None, http_bind_addr: str | None = None) -> None:
    service = GarenaPetGrpcService()
    server = await start_server(bind_addr, service)

    http_host, http_port = _split_host_port(
        http_bind_addr or os.getenv("GARENA_AI_HTTP_BIND", DEFAULT_HTTP_BIND)
    )
    http_server = uvicorn.Server(
        uvicorn.Config(http_app, host=http_host, port=http_port, log_level="info")
    )

    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()
    registered_signals: list[signal.Signals] = []

    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(shutdown_signal, shutdown_requested.set)
        except (NotImplementedError, RuntimeError):
            continue
        registered_signals.append(shutdown_signal)

    grpc_wait_task = asyncio.create_task(server.wait_for_termination())
    http_wait_task = asyncio.create_task(http_server.serve())
    shutdown_task = asyncio.create_task(shutdown_requested.wait())

    try:
        done, _ = await asyncio.wait(
            {grpc_wait_task, http_wait_task, shutdown_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            task.result()
    except asyncio.CancelledError:
        logger.info("Garena AI shutdown requested")
        raise
    finally:
        for shutdown_signal in registered_signals:
            loop.remove_signal_handler(shutdown_signal)

        if not grpc_wait_task.done():
            logger.info("Stopping Garena pet gRPC server")
            await server.stop(grace=2)

        if not http_wait_task.done():
            logger.info("Stopping Garena AI HTTP server")
            http_server.should_exit = True

        for task in (grpc_wait_task, http_wait_task, shutdown_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(grpc_wait_task, http_wait_task, shutdown_task, return_exceptions=True)
        try:
            service.close()
        finally:
            close_open_connections()


def main() -> None:
    logging.basicConfig(level=os.getenv("GARENA_AI_LOG_LEVEL", "INFO"))
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Garena pet gRPC server stopped")
    finally:
        close_open_connections()


if __name__ == "__main__":
    main()
