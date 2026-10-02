from eval.load_golden import read_file, GOLDEN_SET_FILE_PATH
from eval.faithfulness import score_faithfulness
from httpx import AsyncClient
from config import get_settings
import logging
import asyncio

s = get_settings()

logger = logging.getLogger(__name__)
http_client = AsyncClient(timeout=s.HTTP_TIMEOUT)


async def main(golden_path):
    async with http_client as client:
        for row in read_file(golden_path):
            score = await score_faithfulness(row, client)
            supported = sum(1 for c in row.expected_claims if c.mark == "S")
            expected = supported / len(row.expected_claims)
            logger.info(f"Question: {row.question} | Expected: {expected} | Score: {score}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(GOLDEN_SET_FILE_PATH))
