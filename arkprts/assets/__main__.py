"""Entry-point."""

import argparse
import asyncio
import logging

import arkprts

parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Download arknights assets.")
parser.add_argument("output", type=str, nargs="?", default=None, help="Output directory.")
parser.add_argument("--allow", type=str, default="gamedata/excel/*", help="Files allowed to be downloaded.")
parser.add_argument("--force", action="store_true", default=False, help="Force new files to be downloaded")
parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
parser.add_argument("--server", type=str, default="en", help="Server to use, can be 'all'")
parser.add_argument("--normalize", action="store_true", help="Reformat files into a normalized expanded format")


async def main() -> None:
    """Entry-point."""
    args = parser.parse_args()

    logging.basicConfig()
    logging.getLogger("arkprts").setLevel(args.log_level.upper())

    assets = arkprts.BundleAssets(args.output, default_server=args.server)
    await assets.update_assets(args.allow, server=args.server, force=args.force, normalize=args.normalize)

    await assets.network.close()


if __name__ == "__main__":
    asyncio.run(main())
