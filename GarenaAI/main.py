from __future__ import annotations

import asyncio
import logging
import os
import signal

import grpc

try:
    from db import close_open_connections
    from generated import garena_pet_pb2_grpc as rpc
    from pet_grpc_service import GarenaPetGrpcService
except ImportError:  # Allows `python -m GarenaAI.main` from repo root.
    from GarenaAI.db import close_open_connections
    from GarenaAI.generated import garena_pet_pb2_grpc as rpc
    from GarenaAI.pet_grpc_service import GarenaPetGrpcService

logger = logging.getLogger(__name__)
DEFAULT_BIND_ADDR = "127.0.0.1:50051"


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


async def serve(bind_addr: str | None = None) -> None:
    service = GarenaPetGrpcService()
    server = await start_server(bind_addr, service)
    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()
    registered_signals: list[signal.Signals] = []

    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(shutdown_signal, shutdown_requested.set)
        except (NotImplementedError, RuntimeError):
            continue
        registered_signals.append(shutdown_signal)

    wait_task = asyncio.create_task(server.wait_for_termination())
    shutdown_task = asyncio.create_task(shutdown_requested.wait())

    try:
        done, _ = await asyncio.wait(
            {wait_task, shutdown_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            task.result()
    except asyncio.CancelledError:
        logger.info("Garena pet gRPC server shutdown requested")
        raise
    finally:
        for shutdown_signal in registered_signals:
            loop.remove_signal_handler(shutdown_signal)

        if not wait_task.done():
            logger.info("Stopping Garena pet gRPC server")
            await server.stop(grace=2)

        for task in (wait_task, shutdown_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(wait_task, shutdown_task, return_exceptions=True)
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
