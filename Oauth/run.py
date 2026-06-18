"""Development server entry point."""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="OAuth 2.0 Authorization Server")
    sub = parser.add_subparsers(dest="command")

    # runserver
    run_parser = sub.add_parser("run", help="Start the development server")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8000)
    run_parser.add_argument("--reload", action="store_true", default=True)

    # createtestclient
    client_parser = sub.add_parser("create-client", help="Create a test OAuth client")
    client_parser.add_argument("--name", default="Test Client")
    client_parser.add_argument("--redirect-uris", default="http://localhost:9000/callback")
    client_parser.add_argument("--scope", default="profile")

    args = parser.parse_args()

    if args.command == "run":
        uvicorn.run(
            "oauth_server.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    elif args.command == "create-client":
        from oauth_server.database import sync_engine
        from sqlmodel import SQLModel
        import oauth_server.models  # noqa: F401 — ensure models are registered

        # Ensure tables exist (sync)
        SQLModel.metadata.create_all(sync_engine)

        from oauth_server.main import create_test_client
        create_test_client(
            client_name=args.name,
            redirect_uris=args.redirect_uris,
            scope=args.scope,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
